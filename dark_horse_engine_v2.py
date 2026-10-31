"""
Dark Horse Engine — نسخه نهایی (D_last_final.py)
- انتخاب رشته دانشگاهی: Total = 0.55×M + 0.30×V + 0.15×S
- هدایت تحصیلی پایه نهم: Total = 0.60×M + 0.20×S + 0.20×V
- M-Score شاخه‌ها با مخرج ثابت ۳۰ محاسبه می‌شود
- ✅ فقط از فیلدهای archetype و fulfillment_source دیتابیس استفاده می‌کند
- ✅ هیچ تولید داخلی برای کهن‌الگو و منبع رضایت وجود ندارد
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from math import sqrt, isfinite

logger = logging.getLogger("darkhorse_engine_final")


class DarkHorseEngineV2:
    def __init__(
        self,
        motives_path: str = "micro_motives.json",
        majors_path: str = "majors_database_v2.json",
        trait_map_path: str = "trait_map_v3.json",
        value_poles_path: str = "value_poles_v2.json",
        school_branches_path: str = "school_branches_v2.json"
    ):
        self.motives_map: Dict[str, str] = {}
        self.majors_db: Dict[str, Dict] = {}
        self.trait_map: Dict[str, Dict[int, List[str]]] = {}
        self.value_poles: Dict[str, str] = {}
        self.school_branches: Dict[str, Dict] = {}
        self._alt_paths_cache: Dict[str, list] = {}
        self._branch_alt_paths_cache: Dict[str, list] = {}
        self._load_data(motives_path, majors_path, trait_map_path, value_poles_path, school_branches_path)
        self._validate_schema_consistency()
        self._precompute_alternative_paths()

    def _load_data(self, motives_path, majors_path, trait_map_path, value_poles_path, school_branches_path):
        # Reference maps are mandatory for scoring. Fail construction instead of
        # logging an error and allowing an empty/partial engine to serve requests.
        self.motives_map = self._load_json(
            motives_path, key_field="code", value_field="description_fa"
        )
        logger.info("✅ %s میکروموتیو بارگذاری شد.", len(self.motives_map))

        self.majors_db = self._load_json(majors_path, key_field="id")
        active_majors = [
            major for major in self.majors_db.values()
            if major.get("motive_driven") is True
        ]
        if not active_majors:
            raise ValueError("Required majors reference contains no motive_driven=true majors.")
        logger.info("✅ %s رشته/شاخه بارگذاری شد.", len(self.majors_db))

        expected_trait_keys = {f"S{i:02d}" for i in range(1, 26)}
        with open(trait_map_path, "r", encoding="utf-8") as fh:
            raw_trait_map = json.load(fh)
        if not isinstance(raw_trait_map, dict) or set(raw_trait_map) != expected_trait_keys:
            raise ValueError(
                "Required trait_map_v3 reference must contain exactly S01..S25."
            )

        self.trait_map = {}
        for question_key, raw_options in raw_trait_map.items():
            if not isinstance(raw_options, dict):
                raise ValueError(f"Invalid trait_map_v3 options for {question_key}.")
            options = {}
            for raw_index, traits in raw_options.items():
                try:
                    option_index = int(raw_index)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid option index {raw_index!r} in trait_map_v3[{question_key}]."
                    ) from exc
                if option_index in options:
                    raise ValueError(
                        f"Duplicate option index {option_index} in trait_map_v3[{question_key}]."
                    )
                if (
                    not isinstance(traits, list)
                    or not traits
                    or any(not isinstance(trait, str) or not trait.strip() for trait in traits)
                ):
                    raise ValueError(
                        f"Invalid trait list in trait_map_v3[{question_key}][{option_index}]."
                    )
                options[option_index] = traits
            if set(options) != set(range(5)):
                raise ValueError(
                    f"Required trait_map_v3[{question_key}] must contain options 0..4."
                )
            self.trait_map[question_key] = options
        logger.info("✅ trait_map_v3 برای %s سوال بارگذاری شد.", len(self.trait_map))

        expected_value_keys = {
            f"Q{i}{side}" for i in range(1, 16) for side in ("A", "B")
        }
        with open(value_poles_path, "r", encoding="utf-8") as fh:
            value_poles = json.load(fh)
        if (
            not isinstance(value_poles, dict)
            or set(value_poles) != expected_value_keys
            or any(not isinstance(value, str) or not value.strip() for value in value_poles.values())
        ):
            raise ValueError(
                "Required value_poles_v2 reference must contain all 30 non-empty Q1A..Q15B labels."
            )
        self.value_poles = value_poles
        logger.info("✅ value_poles با %s قطب بارگذاری شد.", len(self.value_poles))

        branches = self._load_json(school_branches_path)
        branch_names = [
            branch.get("name") for branch in branches
        ]
        if any(not isinstance(name, str) or not name.strip() for name in branch_names):
            raise ValueError("Required school_branches_v2 reference contains a branch without a name.")
        if len(branch_names) != len(set(branch_names)):
            raise ValueError("Required school_branches_v2 reference contains duplicate branch names.")
        self.school_branches = {branch["name"]: branch for branch in branches}
        logger.info("✅ شاخه‌های دبیرستانی بارگذاری شد (%s شاخه).", len(self.school_branches))

    def _load_json(self, path: str, key_field: Optional[str] = None,
                   value_field: Optional[str] = None) -> Dict:
        reference_path = Path(path)
        if not reference_path.is_file():
            raise FileNotFoundError(f"Required reference file not found: {reference_path}")

        def reject_non_finite(raw):
            raise ValueError(f"Required reference {reference_path} contains non-finite number {raw}.")

        def parse_finite_float(raw):
            value = float(raw)
            if not isfinite(value):
                reject_non_finite(raw)
            return value

        with reference_path.open("r", encoding="utf-8") as fh:
            # The default decoder accepts NaN/Infinity, even in unused metadata.
            # Check exponent overflow too (e.g. 1e999), not only JSON constants.
            data = json.load(
                fh, parse_constant=reject_non_finite, parse_float=parse_finite_float
            )

        if not isinstance(data, list) or not data:
            raise ValueError(f"Required reference {reference_path} must be a non-empty JSON array.")
        if any(not isinstance(item, dict) for item in data):
            raise ValueError(f"Required reference {reference_path} contains a non-object row.")

        if key_field is None:
            return data

        loaded = {}
        for index, item in enumerate(data):
            if key_field not in item or item[key_field] is None or item[key_field] == "":
                raise ValueError(
                    f"Required reference {reference_path} row {index} is missing {key_field!r}."
                )
            key = item[key_field]
            if key in loaded:
                raise ValueError(
                    f"Required reference {reference_path} contains duplicate {key_field}={key!r}."
                )
            if value_field is not None:
                value = item.get(value_field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"Required reference {reference_path} row {index} has no valid {value_field!r}."
                    )
                loaded[key] = value
            else:
                loaded[key] = item

        if not loaded:
            raise ValueError(f"Required reference {reference_path} produced an empty map.")
        return loaded

    def _validate_schema_consistency(self) -> None:
        """
        اعتبارسنجی هم‌ترازی موقعیتی بین strategy_weights (majors_database) و trait_map_v3.
        این دو فایل با فرض ترتیب یکسان S01..S25 به‌هم متصل می‌شوند، بدون شناسهٔ صریح مشترک.
        رشته‌های با motive_driven=False صراحتاً ظرفیت‌محورند و وارد امتیازدهی فردیت نمی‌شوند.
        """
        # Branch M is calibrated against one fixed 30-spark reference budget.
        # Reject any incomplete or non-canonical branch configuration at startup.
        branch_denominators = [
            branch.get("m_score_denom_limit")
            for branch in self.school_branches.values()
        ]
        if (
            len(self.school_branches) != 4
            or len(branch_denominators) != 4
            or any(type(value) is not int or value != 30 for value in branch_denominators)
        ):
            raise ValueError(
                "Required school_branches_v2 reference must contain exactly four branches "
                "with m_score_denom_limit=30."
            )

        expected_keys = {f"S{i:02d}" for i in range(1, 26)}
        trait_keys = set(self.trait_map.keys())
        if trait_keys != expected_keys:
            missing = expected_keys - trait_keys
            extra = trait_keys - expected_keys
            logger.warning(
                f"⚠️ trait_map_v3 با سؤالات مورد انتظار (S01..S25) هم‌تراز نیست. "
                f"موارد گم‌شده: {sorted(missing) or '—'} | موارد اضافه: {sorted(extra) or '—'}"
            )

        def finite_number(value):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
            try:
                return isfinite(value)
            except OverflowError:
                return False

        expected_value_keys = {
            f"Q{i}{side}" for i in range(1, 16) for side in ("A", "B")
        }
        stub_count = 0
        for major_id, major_data in self.majors_db.items():
            if major_data.get("motive_driven") is not True:
                stub_count += 1
                continue
            sw = major_data.get("strategy_weights")
            if (
                not isinstance(sw, list)
                or len(sw) != 25
                or any(
                    not isinstance(row, list)
                    or len(row) != 5
                    or any(not finite_number(value) or not 0 <= value <= 1 for value in row)
                    for row in sw
                )
            ):
                raise ValueError(
                    f"Active major {major_id!r}: strategy_weights must be exactly "
                    "25x5 finite numbers in [0,1]."
                )
            vw = major_data.get("value_weights")
            if (
                not isinstance(vw, dict)
                or set(vw) != expected_value_keys
                or any(not finite_number(value) for value in vw.values())
            ):
                raise ValueError(
                    f"Active major {major_id!r}: value_weights must contain exactly "
                    "30 finite numeric poles Q1A..Q15B."
                )

        active_count = len(self.majors_db) - stub_count
        logger.info(
            "✅ اعتبارسنجی کاتالوگ رشته‌ها: %s رشته فعال فردیت‌محور، %s رشته صرفاً ظرفیت‌محور (motive_driven=False).",
            active_count,
            stub_count,
        )

    def _get_branch_denom_limit(self, branch_name: str) -> Optional[int]:
        if branch_name in self.school_branches:
            return self.school_branches[branch_name].get("m_score_denom_limit")
        return None

    # ──────────────────────────────────────────────────────────────
    # محاسبه M-Score برای رشته‌ها (مخرج واقعی = تعداد کدهای رشته)
    # ──────────────────────────────────────────────────────────────
    def _compute_m_score(self, user_motives: List[str], major_data: Dict) -> Tuple[float, List[Dict]]:
        if not user_motives:
            return 0.0, []

        raw_codes = major_data.get("micro_motive_codes", [])
        if isinstance(raw_codes, dict):
            major_set = {str(c).strip().lower() for c in raw_codes.keys()}
        elif isinstance(raw_codes, list):
            major_set = {str(c).strip().lower() for c in raw_codes}
        else:
            return 0.0, []

        if not major_set:
            return 0.0, []

        user_set = {str(m).strip().lower() for m in user_motives if m and str(m).strip()}
        matched = user_set & major_set
        if not matched:
            return 0.0, []

        denom = len(major_set)
        score = len(matched) / denom

        matched_details = []
        for code in user_motives:
            code_lower = str(code).strip().lower()
            if code_lower in matched:
                desc = self.motives_map.get(code, "") or self.motives_map.get(code.upper(), "")
                matched_details.append({"code": code, "description": desc})

        return min(1.0, score), matched_details

    def _active_branch_code_set(self, raw_codes: List[str]) -> set:
        codes = {str(c).strip().lower() for c in (raw_codes or []) if c and str(c).strip()}
        if self.motives_map:
            catalog = {str(k).strip().lower() for k in self.motives_map.keys()}
            filtered = codes & catalog
            if filtered:
                return filtered
        return codes

    # ──────────────────────────────────────────────────────────────
    # محاسبه M-Score برای شاخه‌ها (مخرج ثابت ۳۰)
    # ──────────────────────────────────────────────────────────────
    def _compute_branch_m_score(self, user_motives: List[str], branch_data: Dict) -> Tuple[float, List[Dict]]:
        if not user_motives:
            return 0.0, []

        raw_codes = branch_data.get("micro_motive_codes", [])
        if not raw_codes:
            return 0.0, []

        user_set = {str(m).strip().lower() for m in user_motives if m and str(m).strip()}
        branch_set = self._active_branch_code_set(raw_codes)
        matched = user_set & branch_set

        if not matched:
            return 0.0, []

        # The denominator is fixed and does not depend on user profile length
        # or the size of the branch's motive-code pool.
        score = len(matched) / 30.0

        matched_details = []
        for code in user_motives:
            code_lower = str(code).strip().lower()
            if code_lower in matched:
                desc = self.motives_map.get(code, "") or self.motives_map.get(code.upper(), "")
                matched_details.append({"code": code, "description": desc})

        return min(1.0, score), matched_details

    # ── S-Score input contract ──
    @staticmethod
    def _parse_s_strategy_answers(sjt_answers) -> Tuple[List[int], Dict]:
        """Accept S only when all 25 protocol keys contain one valid A-E answer."""
        expected_keys = {f"sjt_{i}" for i in range(1, 26)}
        input_is_dict = isinstance(sjt_answers, dict)
        payload = sjt_answers if input_is_dict else {}

        answers = []
        valid_questions = []
        missing_questions = []
        invalid_questions = []
        for i in range(1, 26):
            key = f"sjt_{i}"
            if key not in payload:
                missing_questions.append(key)
                answers.append(-1)
                continue

            raw_answer = payload.get(key)
            if not isinstance(raw_answer, str):
                invalid_questions.append(key)
                answers.append(-1)
                continue

            answer = raw_answer.strip().upper()
            if answer not in {"A", "B", "C", "D", "E"}:
                invalid_questions.append(key)
                answers.append(-1)
                continue

            valid_questions.append(key)
            answers.append(ord(answer) - ord("A"))

        unknown_keys = sorted(str(key) for key in payload if key not in expected_keys)
        length_matches = input_is_dict and len(payload) == 25
        complete = (
            input_is_dict
            and length_matches
            and len(valid_questions) == 25
            and not unknown_keys
        )
        assessment = {
            "status": "complete" if complete else "incomplete_s_responses",
            "valid_answers": len(valid_questions),
            "expected_answers": 25,
            "input_length": len(payload) if input_is_dict else None,
            "length_matches": bool(length_matches),
            "missing_questions": missing_questions,
            "invalid_questions": invalid_questions,
            "unknown_keys": unknown_keys,
            "reason": None if complete else "incomplete_s_responses",
        }
        if not complete:
            assessment["score"] = None
            # Invalidate the scorer input too: an extra unknown key makes the
            # whole protocol payload incomplete even if the 25 expected keys exist.
            return [-1] * 25, assessment
        return answers, assessment

    # ── S-Score ──
    def _compute_s_score(self, strategy_answers: List[int], strategy_weights: List[List[float]]) -> Tuple[float, List[str]]:
        if not strategy_weights or not strategy_answers:
            return 0.0, []

        total_score = 0.0
        highlights = []

        # Keep the denominator fixed to the full S-question protocol.
        # Unanswered/invalid items contribute zero instead of shrinking the denominator.
        question_count = len(strategy_weights)

        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers):
                continue
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue

            max_w = max(row) if row else 1.0
            chosen_w = row[idx] if 0 <= idx < len(row) else 0.0
            normalized = chosen_w / max_w if max_w > 0 else 0.0

            total_score += normalized

            if normalized >= 0.7:
                q_num = i + 1
                question_key = f"S{str(q_num).zfill(2)}"
                traits = self.trait_map.get(question_key, {}).get(idx, [])
                if traits:
                    trait_names = "، ".join(traits)
                    highlights.append(f"سبک «{trait_names}» با این رشته هم‌خوانی بالایی دارد ({int(normalized*100)}%)")
                else:
                    highlights.append(f"گزینه {idx+1} با این رشته هم‌خوانی بالایی دارد ({int(normalized*100)}%)")

        final_score = (total_score / question_count) if question_count > 0 else 0.0
        return final_score, highlights

    def _compute_s_score_for_complete_profile(self, strategy_answers: List[int], strategy_weights: List[List[float]]) -> Tuple[Optional[float], List[str]]:
        """Reject incomplete S input before calling the baseline scorer."""
        if (
            not isinstance(strategy_answers, list)
            or len(strategy_answers) != 25
            or any(type(idx) is not int or idx < 0 or idx > 4 for idx in strategy_answers)
            or not isinstance(strategy_weights, list)
            or len(strategy_weights) != 25
            or any(not isinstance(row, list) or len(row) != 5 for row in strategy_weights)
        ):
            return None, []
        return self._compute_s_score(strategy_answers, strategy_weights)

    # V range normalization: aggregate evidence, never average pair ratios.
    V_EPSILON = 0.02

    @staticmethod
    def _valid_value_code(value):
        if not isinstance(value, str):
            return None
        code = value.strip().upper()
        return code if code in {f"Q{i}{side}" for i in range(1, 16) for side in "AB"} else None

    @classmethod
    def _pairwise_value_score(cls, choice, value_weights):
        code = cls._valid_value_code(choice)
        if not code:
            return 0.0, 0.0
        try:
            a, b = (float(value_weights[code[:-1] + side]) for side in "AB")
        except (KeyError, TypeError, ValueError):
            return 0.0, 0.0
        if not all(isfinite(x) and 0 <= x <= 1 for x in (a, b)):
            return 0.0, 0.0
        span = round(abs(a - b), 12)
        chosen = a if code[-1] == "A" else b
        if span < cls.V_EPSILON:
            return 0.0, chosen
        return (chosen - min(a, b)) / span, chosen

    def _compute_v_result(self, value_choices, value_weights):
        # Repeated identical answers count once; conflicting answers invalidate
        # the question rather than making the result depend on input order.
        answers = {}
        for value in value_choices or []:
            code = self._valid_value_code(value)
            if code:
                answers.setdefault(code[:-1], set()).add(code)
        answered = sum(len(codes) == 1 for codes in answers.values())
        numerator = denominator = 0.0
        informative = 0
        highlights = []
        for base, codes in answers.items():
            if len(codes) != 1:
                continue
            code = next(iter(codes))
            try:
                a, b = (float(value_weights[base + side]) for side in "AB")
            except (KeyError, TypeError, ValueError):
                continue
            if not all(isfinite(x) and 0 <= x <= 1 for x in (a, b)):
                continue
            span = round(abs(a - b), 12)
            if span < self.V_EPSILON:
                continue
            chosen = a if code[-1] == "A" else b
            numerator += chosen - min(a, b)
            denominator += span
            informative += 1
            if chosen > min(a, b):
                pole = self.value_poles.get(code, code)
                highlights.append(f"ارزش «{pole}»: هم‌راستایی قوی")
        score = min(1.0, max(0.0, numerator / denominator)) if denominator else None
        return {
            "score": score,
            "status": ("complete" if answered == 15 else "partial") if score is not None
                      else ("no_discriminative_evidence" if answered else "incomplete"),
            "coverage": {"answered": answered, "total": 15,
                         "discriminative_answered": informative},
            "highlights": highlights,
        }

    def _compute_v_score(self, value_choices, value_weights):
        result = self._compute_v_result(value_choices, value_weights)
        return result["score"], result["highlights"]

    @classmethod
    def _v_method(cls):
        return {"version": "3.1-v-range-norm",
                "v_formula": "sum(w_chosen-min(wA,wB))/sum(max(wA,wB)-min(wA,wB)); answered pairs only; range < 0.02 excluded; zero denominator => null",
                "v_epsilon": cls.V_EPSILON,
                "v_previous_formula": "mean(w_chosen/max(wA,wB)) at deploy 45e61bc5ed0f83a69ec36aff9de7a24a1ce45b90",
                "score_label": "امتیاز هم‌خوانی مدل"}

    # ──────────────────────────────────────────────────────────────
    # ابزارهای فاصله برای مسیرهای جایگزین
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _strategy_profile_vector(strategy_weights: List[List[float]], question_count: int = 25,
                                 option_count: int = 5) -> List[float]:
        """کل ماتریس Strategy را حفظ می‌کند: 25 سؤال × 5 گزینه = 125 بُعد ثابت."""
        vector: List[float] = []
        for q_idx in range(question_count):
            row = strategy_weights[q_idx] if q_idx < len(strategy_weights) else []
            for opt_idx in range(option_count):
                try:
                    vector.append(float(row[opt_idx]) if opt_idx < len(row) else 0.0)
                except (TypeError, ValueError):
                    vector.append(0.0)
        return vector

    @staticmethod
    def _rms_distance(a: List[float], b: List[float]) -> float:
        """فاصله RMS-Euclidean؛ برای بردارهای با طول ثابت، مقیاس را کنترل می‌کند."""
        n = max(len(a), len(b))
        if n == 0:
            return 0.0
        total_sq = 0.0
        for i in range(n):
            av = a[i] if i < len(a) else 0.0
            bv = b[i] if i < len(b) else 0.0
            total_sq += (av - bv) ** 2
        return sqrt(total_sq / n)

    @staticmethod
    def _hybrid_profile_distance(value_a: List[float], value_b: List[float],
                                 strategy_a: List[float], strategy_b: List[float],
                                 value_weight: float = 0.60,
                                 strategy_weight: float = 0.40) -> Tuple[float, float, float]:
        """فاصله ترکیبی غیرخطی: ریشه مجموع مربعات وزنیِ میانگین فاصله‌ها."""
        v_dist = DarkHorseEngineV2._rms_distance(value_a, value_b)
        s_dist = DarkHorseEngineV2._rms_distance(strategy_a, strategy_b)
        total_dist = sqrt(
            value_weight * (v_dist ** 2) +
            strategy_weight * (s_dist ** 2)
        )
        return total_dist, v_dist, s_dist

    # ── مسیرهای جایگزین برای رشته‌های دانشگاهی ──
    def _precompute_alternative_paths(self) -> None:
        """Phase 1: precompute alternative paths once at startup (safe if fails)."""
        try:
            for major_id in list(self.majors_db.keys()):
                self._alt_paths_cache[major_id] = self._compute_alternative_paths(major_id, top_n=3)
            for branch_name in list(self.school_branches.keys()):
                self._branch_alt_paths_cache[branch_name] = self._compute_branch_alternative_paths(
                    branch_name, top_n=3
                )
            logger.info(
                "✅ Alternative paths precomputed: %s majors, %s branches",
                len(self._alt_paths_cache),
                len(self._branch_alt_paths_cache),
            )
        except Exception as e:
            logger.error("Alternative paths precompute failed: %s", e)
            self._alt_paths_cache = {}
            self._branch_alt_paths_cache = {}

    def _find_alternative_paths(self, major_id: str, top_n: int = 3):
        cached = self._alt_paths_cache.get(major_id)
        if cached is not None:
            return list(cached)[:top_n]
        return self._compute_alternative_paths(major_id, top_n=top_n)

    def _find_branch_alternative_paths(self, branch_name: str, top_n: int = 3):
        cached = self._branch_alt_paths_cache.get(branch_name)
        if cached is not None:
            return list(cached)[:top_n]
        return self._compute_branch_alternative_paths(branch_name, top_n=top_n)

    def _compute_alternative_paths(self, major_id: str, top_n: int = 3) -> List[Dict]:
        target = self.majors_db.get(major_id)
        if not target or target.get("motive_driven") is False:
            return []

        target_vw = target.get("value_weights", {})
        target_sw = target.get("strategy_weights", [])
        target_v_vec = [target_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
        target_s_vec = self._strategy_profile_vector(target_sw)

        distances = []
        for other_id, other_data in self.majors_db.items():
            if other_id == major_id or other_data.get("motive_driven") is False:
                continue

            other_vw = other_data.get("value_weights", {})
            other_sw = other_data.get("strategy_weights", [])
            other_v_vec = [other_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
            other_s_vec = self._strategy_profile_vector(other_sw)

            total_dist, v_dist, s_dist = self._hybrid_profile_distance(
                target_v_vec, other_v_vec,
                target_s_vec, other_s_vec,
                value_weight=0.60,
                strategy_weight=0.40
            )

            distances.append({
                "major_id": other_id,
                "major_name": other_data.get("name", ""),
                "distance": round(total_dist, 3),
                "value_distance": round(v_dist, 3),
                "strategy_distance": round(s_dist, 3),
                "group": other_data.get("group", ""),
                "matching_method": "hybrid_rms_euclidean_125d_strategy"
            })

        distances.sort(key=lambda x: x["distance"])
        return distances[:top_n]

    # ── مسیرهای جایگزین برای شاخه‌های دبیرستانی ──
    def _compute_branch_alternative_paths(self, branch_name: str, top_n: int = 3) -> List[Dict]:
        if branch_name not in self.school_branches:
            return []

        target = self.school_branches[branch_name]
        target_vw = target.get("value_weights", {})
        target_sw = target.get("strategy_weights", [])
        target_v_vec = [target_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
        target_s_vec = self._strategy_profile_vector(target_sw)

        distances = []
        for other_name, other_data in self.school_branches.items():
            if other_name == branch_name:
                continue

            other_vw = other_data.get("value_weights", {})
            other_sw = other_data.get("strategy_weights", [])
            other_v_vec = [other_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
            other_s_vec = self._strategy_profile_vector(other_sw)

            total_dist, v_dist, s_dist = self._hybrid_profile_distance(
                target_v_vec, other_v_vec,
                target_s_vec, other_s_vec,
                value_weight=0.60,
                strategy_weight=0.40
            )

            distances.append({
                "branch_name": other_name,
                "distance": round(total_dist, 3),
                "value_distance": round(v_dist, 3),
                "strategy_distance": round(s_dist, 3),
                "matching_method": "hybrid_rms_euclidean_125d_strategy"
            })

        distances.sort(key=lambda x: x["distance"])
        return distances[:top_n]

    # ── پروفایل میانگین‌نرمال صفات راهبردی (تضمین عدم تناقض بین غالب و ناهمسو) ──
    def _compute_trait_alignment_profile(
        self, strategy_answers: List[int], strategy_weights: List[List[float]]
    ) -> Dict[str, float]:
        trait_scores: Dict[str, List[float]] = {}
        for i, row in enumerate(strategy_weights or []):
            if i >= len(strategy_answers):
                continue
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue
            max_w = max(row) if row else 1.0
            chosen_w = row[idx]
            normalized = (chosen_w / max_w) if max_w > 0 else 0.0
            q_num = i + 1
            question_key = f"S{str(q_num).zfill(2)}"
            trait_list = self.trait_map.get(question_key, {}).get(idx, [])
            if trait_list:
                for t in trait_list:
                    trait_scores.setdefault(t, []).append(normalized)
            else:
                trait_scores.setdefault(f"گزینه {idx+1}", []).append(normalized)
        return {
            trait: (sum(vals) / len(vals))
            for trait, vals in trait_scores.items()
            if vals
        }

    # ── استخراج ویژگی‌های ناهمسو ──
    def _extract_s_misaligned_traits(self, strategy_answers, strategy_weights):
        profile = self._compute_trait_alignment_profile(strategy_answers, strategy_weights)
        misaligned = [
            (trait, mean_score)
            for trait, mean_score in profile.items()
            if mean_score < 0.40
        ]
        misaligned.sort(key=lambda x: x[1])
        return [trait for trait, _ in misaligned[:3]]

    def _extract_v_misaligned_poles(self, value_choices, value_weights):
        poles = []
        for v in value_choices:
            if not v or not v.strip() or not v.startswith('Q'):
                continue
            letter = v[-1]
            q_part = v[:-1]
            opposite_letter = "B" if letter == "A" else "A"
            opposite = q_part + opposite_letter
            user_weight = value_weights.get(v, 0.0)
            opp_weight = value_weights.get(opposite, 0.0)
            if user_weight < 0.4 and opp_weight >= 0.7:
                pole = self.value_poles.get(v, v)
                poles.append(pole)
        return list(dict.fromkeys(poles))[:3]

    # ── سناریوهای ۸ گانه ──
    def _generate_scenario_description(self, major_name, m_evidence, m_score, s_score, v_score,
                                       strategy_answers, strategy_weights, value_choices, value_weights):
        m_aligned = m_score >= 0.5
        m_partial = 0.15 <= m_score < 0.5
        s_aligned = s_score >= 0.5
        v_aligned = v_score >= 0.5
        desc = f"📌 {major_name}: "

        if m_aligned and s_aligned and v_aligned:
            desc += "هر سه لایهٔ فردیت شما با این رشته همخوانی بالایی دارند. شما می‌توانید در این مسیر یک اسب سیاه باشید."
        elif m_aligned and (not s_aligned or not v_aligned):
            if not s_aligned and not v_aligned:
                desc += "خرده‌انگیزه‌های شما با این رشته همسو هستند، اما راهبردهای شخصی و ارزش‌های بنیادین شما با این رشته همخوانی کمتری دارند. پیشنهاد می‌شود با آگاهی از این تفاوت‌ها، در انتخاب این مسیر باریک دقت بیشتری کنید."
            elif not s_aligned:
                desc += "خرده‌انگیزه‌های شما با این رشته همسو هستند، اما راهبردهای شخصی شما با این رشته همخوانی کمتری دارد. اگر مایلید در این مسیر قدم بگذارید، توصیه می‌شود با چشمان باز این ناهماهنگی را در نظر بگیرید."
            elif not v_aligned:
                desc += "خرده‌انگیزه‌های شما با این رشته همسو هستند، اما ارزش‌های بنیادین شما با این رشته همخوانی کمتری دارد. این ممکن است به مرور باعث کاهش انگیزه شود. با دقت انتخاب کنید."
        elif not m_aligned and (s_aligned or v_aligned):
            spark_clause = (
                "اگرچه همپوشانی خرده‌انگیزه‌های شما با این رشته نسبی است"
                if m_partial
                else "اگرچه خرده‌انگیزه‌های شما همخوانی مستقیمی با این رشته ندارد"
            )
            if s_aligned and v_aligned:
                desc += f"{spark_clause}، اما راهبردهای شخصی و ارزش‌های بنیادین شما با روحیهٔ این حرفه هماهنگی خوبی نشان می‌دهد. این رشته می‌تواند یک گزینهٔ آلترناتیو غیرمنتظره اما بالقوه موفق برای شما باشد."
            elif s_aligned:
                desc += f"{spark_clause}، اما راهبردهای شخصی شما همخوانی خوبی با این حرفه دارد. اگر به این مسیر علاقه دارید، می‌توانید آن را به‌عنوان یک انتخاب نامتعارف در نظر بگیرید."
            elif v_aligned:
                desc += f"{spark_clause}، اما ارزش‌های بنیادین شما همخوانی خوبی با این حرفه دارد. این رشته می‌تواند از منظر معنا و رضایت درونی برایتان جذاب باشد، هرچند تنها بخشی از جرقه‌های روزمرهٔ آن را انتخاب کرده‌اید."
        else:
            desc += "همپوشانی هر سه لایهٔ فردیت شما — خرده‌انگیزه‌ها، راهبردهای شخصی و ارزش‌های بنیادین — با این رشته زیر آستانهٔ قوت است؛ بهتر است ابتدا گزینه‌هایی را بررسی کنید که هم‌ترازی قوی‌تری با فردیت شما دارند."

        if not s_aligned:
            mis_traits = self._extract_s_misaligned_traits(strategy_answers, strategy_weights)
            if mis_traits:
                desc += f" برای مثال، در ابعاد «{', '.join(mis_traits)}» ناهم‌راستایی دیده می‌شود."
        if not v_aligned:
            mis_poles = self._extract_v_misaligned_poles(value_choices, value_weights)
            if mis_poles:
                desc += f" همچنین ارزش‌های «{', '.join(mis_poles)}» با اولویت‌های این رشته فاصله دارند."

        if m_evidence:
            sample = "، ".join(m.get("description", m["code"]) for m in m_evidence[:2])
            if len(m_evidence) > 2:
                desc += f" (جرقه‌ها: {sample} و {len(m_evidence)-2} جرقهٔ دیگر)"
            else:
                desc += f" (جرقه‌ها: {sample})"

        return desc

    # ── استخراج ویژگی‌ها و ارزش‌های غالب (برای archetype_info) ──
    def _extract_dominant_traits(self, strategy_answers: List[int], strategy_weights: List[List[float]],
                                  threshold: float = 0.7, top_n: int = 2) -> List[str]:
        profile = self._compute_trait_alignment_profile(strategy_answers, strategy_weights)
        dominant = [
            (trait, mean_score)
            for trait, mean_score in profile.items()
            if mean_score >= threshold
        ]
        dominant.sort(key=lambda x: -x[1])
        return [t for t, _ in dominant[:top_n]]

    def _extract_dominant_values(self, value_choices: List[str], value_weights: Dict[str, float],
                                  threshold: float = 0.7, top_n: int = 2) -> List[str]:
        value_strength: Dict[str, float] = {}
        for v in value_choices:
            if not v or not v.strip():
                continue
            code = v.strip().upper()
            normalized, raw_weight = self._pairwise_value_score(code, value_weights)
            if raw_weight > threshold or (normalized >= 0.85 and raw_weight >= 0.55):
                pole = self.value_poles.get(code, v.strip())
                value_strength[pole] = max(value_strength.get(pole, 0.0), normalized)

        ranked = sorted(value_strength.items(), key=lambda x: -x[1])
        return [v for v, _ in ranked[:top_n]]

    @staticmethod
    def _get_fit_level(score: float) -> str:
        if score >= 80:
            return "همخوانی بسیار بالا"
        elif score >= 60:
            return "همخوانی بالا"
        elif score >= 40:
            return "همخوانی متوسط"
        else:
            return "همخوانی پایین"

    # ──────────────────────────────────────────────────────────────
    #  متد ۱: انتخاب رشته دانشگاهی (کنکور)
    #  فرمول: Total = 0.55×M + 0.30×V + 0.15×S
    # ──────────────────────────────────────────────────────────────
    def discover_individuality(self, user_motives, sjt_answers, conjoint_choices):
        strategy_answers, s_assessment = self._parse_s_strategy_answers(sjt_answers)

        value_choices = []
        for i in range(1, 16):
            key = f"conj_{i}"
            val = (conjoint_choices or {}).get(key, "").strip().upper()
            if val in (f'Q{i}A', f'Q{i}B'):
                value_choices.append(val)
            else:
                value_choices.append("")

        discovered = []
        incomplete = []
        for major_id, major_data in self.majors_db.items():
            try:
                # ایمنی داده: رشته‌هایی که هنوز motive واقعی و وزن‌دهی معتبر ندارند
                # نباید وارد discovery فردی شوند، حتی اگر کد P2-* آن‌ها دستی به ورودی تزریق شود.
                if major_data.get("motive_driven") is False:
                    continue

                m_score, m_ev = self._compute_m_score(user_motives or [], major_data)
                # فیلتر سخت خرده‌انگیزه: بدون همپوشانی واقعی جرقه، رشته نباید فقط با S/V بیاید.
                # (حذف قبلی این شرط باعث ظاهر شدن رشته‌ها تا ~۳۰–۴۵٪ فقط از روی راهبرد/ارزش شد.)
                if m_score < 0.15:
                    continue

                s_score, s_high = self._compute_s_score_for_complete_profile(strategy_answers, major_data.get("strategy_weights", []))
                v_result = self._compute_v_result(value_choices, major_data.get("value_weights", {}))
                v_score, v_high = v_result["score"], v_result["highlights"]
                if s_score is None or v_score is None or not major_data.get("strategy_weights"):
                    s_incomplete = s_assessment.get("status") != "complete"
                    incomplete.append({
                        "major_id": major_id,
                        "score": None,
                        "status": "incomplete_s_responses" if s_incomplete else "incomplete",
                        "reason": s_assessment.get("reason") if s_incomplete else None,
                        "s_assessment": s_assessment if s_incomplete else None,
                        "v_result": v_result,
                    })
                    continue

                total = (0.55 * m_score) + (0.30 * v_score) + (0.15 * s_score)
                final_score = round(total * 100, 1)

                if final_score < 30.0:
                    continue

                evidence = {"micro_motives_matched": m_ev}
                if s_high:
                    evidence["strategy_highlights"] = s_high
                if v_high:
                    evidence["value_alignment"] = v_high

                warnings = []
                if 0.15 <= m_score < 0.35:
                    warnings.append("همپوشانی خرده‌انگیزه با این رشته نسبتاً کم است؛ با احتیاط بررسی کن و به راهبرد/ارزش هم نگاه کن.")
                if s_score < 0.4:
                    warnings.append("راهبردهای شخصی شما با الگوی رایج این رشته تفاوت‌هایی دارد.")
                if v_score < 0.4:
                    warnings.append("برخی ارزش‌های بنیادین شما با اولویت‌های این رشته فاصله دارد.")
                if warnings:
                    evidence["warnings"] = warnings

                personalized = self._generate_scenario_description(
                    major_data.get("name", ""), m_ev, m_score, s_score, v_score,
                    strategy_answers, major_data.get("strategy_weights", []),
                    value_choices, major_data.get("value_weights", {})
                )

                archetype = major_data.get("archetype")
                fulfillment_source = major_data.get("fulfillment_source")

                archetype_info = {
                    "archetype": archetype,
                    "fulfillment_source": fulfillment_source,
                    "dominant_traits": self._extract_dominant_traits(
                        strategy_answers, major_data.get("strategy_weights", [])
                    ),
                    "dominant_values": self._extract_dominant_values(
                        value_choices, major_data.get("value_weights", {})
                    )
                }

                alt_paths = self._find_alternative_paths(major_id, top_n=3)

                discovered.append({
                    "major_id": major_id,
                    "major_name_fa": major_data.get("name", ""),
                    "realm_fa": major_data.get("group", ""),
                    "individuality_fit": {
                        "score": final_score,
                        "status": v_result["status"],
                        "value_assessment": v_result,
                        "level": self._get_fit_level(final_score),
                        # توجه: فیلد prestige_level در majors_database_v2.json فعلاً وجود ندارد.
                        # قبلاً اینجا مقدار ثابت ۲ برای همهٔ ۱۶۰ رشته برمی‌گشت (داده جعلی).
                        # تا زمانی که این فیلد به دیتابیس اضافه شود، None برمی‌گردد.
                        "market_demand_level": major_data.get("prestige_level"),
                        "raw_components": {
                            "m_score": round(m_score * 100, 1),
                            "s_score": round(s_score * 100, 1),
                            "v_score": round(v_score * 100, 1)
                        },
                        "evidence": evidence,
                        "personalized_description": personalized,
                        "archetype": archetype_info,
                        "alternative_paths": alt_paths,
                        "fulfillment_source": fulfillment_source,
                    },
                })
            except Exception as e:
                logger.error(f"خطا در تحلیل رشته/شاخه {major_id}: {e}")

        discovered.sort(key=lambda x: x["individuality_fit"]["score"], reverse=True)

        high = sum(1 for m in discovered if m["individuality_fit"]["score"] >= 80)
        med = sum(1 for m in discovered if 60 <= m["individuality_fit"]["score"] < 80)
        low = sum(1 for m in discovered if m["individuality_fit"]["score"] < 60)

        active_majors_count = sum(
            1 for m in self.majors_db.values() if m.get("motive_driven") is not False
        )

        return {
            "discovered_majors": discovered,
            "incomplete_assessments": incomplete,
            "s_assessment": s_assessment,
            "status": "incomplete" if incomplete or s_assessment.get("status") != "complete" else "complete",
            "summary": {
                "total_majors_analyzed": len(self.majors_db),
                "active_majors_analyzed": active_majors_count,
                "total_matches": len(discovered),
                "high_compatibility": high,
                "medium_compatibility": med,
                "low_compatibility": low
            },
            "method": {
                "principle": "کشف فردیت — انتخاب رشته دانشگاهی",
                "scoring": "Total = 0.55×M + 0.30×V + 0.15×S",
                "s_score_formula": "S = (1/25) * Σ(chosen_w / max_w)",
                "alternative_path_formula": "D = √(0.60×RMS(V)^2 + 0.40×RMS(S)^2), S = 125D",
                "filter": "نمایش رشته‌ها با Total ≥ 30% و M ≥ 15% (سخت)",
                **self._v_method(),
                "trait_map_version": "v3 (چند ویژگی در هر گزینه)",
                "features": ["کهن‌الگو و منبع رضایت از دیتابیس", "مسیرهای جایگزین با پروفایل کامل ۱۲۵بعدی Strategy", "سناریوهای ۸ گانه"]
            },
            "next_step": "برای مشاهده شانس قبولی دانشگاه‌ها، اطلاعات سنجش خود را وارد کنید",
        }

    # ──────────────────────────────────────────────────────────────
    #  متد ۲: هدایت تحصیلی پایه نهم (توصیه شاخه)
    #  فرمول: Total = 0.60×M + 0.20×S + 0.20×V
    #  M-Score denominator = min(30, max(15, |U|))
    # ──────────────────────────────────────────────────────────────
    def recommend_school_branch(self, user_motives, sjt_answers, conjoint_choices) -> Dict:
        strategy_answers, s_assessment = self._parse_s_strategy_answers(sjt_answers)

        value_choices = []
        for i in range(1, 16):
            key = f"conj_{i}"
            val = (conjoint_choices or {}).get(key, "").strip().upper()
            if val in (f'Q{i}A', f'Q{i}B'):
                value_choices.append(val)
            else:
                value_choices.append("")

        branch_scores = []
        incomplete = []

        for branch_name, branch_data in self.school_branches.items():
            m_score, m_ev = self._compute_branch_m_score(user_motives, branch_data)
            s_score, s_high = self._compute_s_score_for_complete_profile(strategy_answers, branch_data.get("strategy_weights", []))
            v_result = self._compute_v_result(value_choices, branch_data.get("value_weights", {}))
            v_score, v_high = v_result["score"], v_result["highlights"]
            if s_score is None or v_score is None or not branch_data.get("strategy_weights"):
                s_incomplete = s_assessment.get("status") != "complete"
                incomplete.append({
                    "branch_name": branch_name,
                    "score": None,
                    "status": "incomplete_s_responses" if s_incomplete else "incomplete",
                    "reason": s_assessment.get("reason") if s_incomplete else None,
                    "s_assessment": s_assessment if s_incomplete else None,
                    "v_result": v_result,
                })
                continue
            total = (0.60 * m_score) + (0.20 * v_score) + (0.20 * s_score)

            branch_info = {
                "branch_name": branch_name,
                "status": v_result["status"],
                "value_assessment": v_result,
                "average_score": round(total * 100, 1),
                "count": len(branch_data.get("micro_motive_codes", [])),
                "max_score": round(total * 100, 1),
                "min_score": round(total * 100, 1),
                "avg_components": {
                    "m_score": round(m_score * 100, 1),
                    "s_score": round(s_score * 100, 1),
                    "v_score": round(v_score * 100, 1)
                },
                "evidence": {
                    "micro_motives_matched": m_ev,
                    "strategy_highlights": s_high[:3] if s_high else [],
                    "value_alignment": v_high[:3] if v_high else []
                }
            }

            alternative_paths = self._find_branch_alternative_paths(branch_name, top_n=3)
            if alternative_paths:
                branch_info["alternative_paths"] = alternative_paths

            if m_score < 0.15:
                branch_info["warning"] = "همخوانی انگیزه در این شاخه پایین است. ممکن است این شاخه برای شما جذابیت روزمره‌ی کمتری داشته باشد."

            branch_scores.append(branch_info)

        branch_scores.sort(key=lambda x: x["average_score"], reverse=True)

        best_branch = None
        for branch in branch_scores:
            if branch["avg_components"]["m_score"] >= 15:
                best_branch = branch["branch_name"]
                break

        return {
            "recommended_branches": branch_scores,
            "incomplete_assessments": incomplete,
            "s_assessment": s_assessment,
            "status": "incomplete" if incomplete or s_assessment.get("status") != "complete" else "complete",
            "best_branch": best_branch,
            "summary": {
                "total_majors_analyzed": len(self.majors_db),
                "branches_analyzed": len(self.school_branches)
            },
            "method": {
                "principle": "هدایت تحصیلی — توصیه شاخه دبیرستانی",
                "scoring": "Total = 0.60×M + 0.20×S + 0.20×V",
                "m_denom_limit": "min(30, max(15, |unique_user_motives|))",
                "alternative_path_formula": "D = √(0.60×RMS(V)^2 + 0.40×RMS(S)^2), S = 125D",
                "filter": "بهترین شاخه فقط از بین شاخه‌های با M ≥ 15% انتخاب می‌شود",
                "features": ["M-Score مستقیم از شاخه", "S و V از شاخه", "مسیرهای جایگزین با پروفایل کامل ۱۲۵بعدی Strategy"],
                **self._v_method()
            },
            "next_step": "بر اساس این نتایج، شاخه‌ای که بیشترین امتیاز را دارد و همخوانی انگیزه‌ی بالایی دارد، مناسب‌ترین گزینه برای شماست."
        }
