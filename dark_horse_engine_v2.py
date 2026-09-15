"""
Dark Horse Engine — نسخه نهایی (D_last_final.py)
- انتخاب رشته دانشگاهی: Total = 0.55×M + 0.30×V + 0.15×S
- هدایت تحصیلی پایه نهم: Total = 0.60×M + 0.20×S + 0.20×V
- M-Score شاخه‌ها با مخرج ۳۰ محاسبه می‌شود
- ✅ فقط از فیلدهای archetype و fulfillment_source دیتابیس استفاده می‌کند
- ✅ هیچ تولید داخلی برای کهن‌الگو و منبع رضایت وجود ندارد
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from math import sqrt

logger = logging.getLogger("darkhorse_engine_final")


class DarkHorseEngineV2:
    def __init__(
        self,
        motives_path: str = "docs/data/micro_motives.json",
        majors_path: str = "majors_database_v2.json",
        trait_map_path: str = "docs/data/trait_map_v3.json",
        value_poles_path: str = "value_poles_v2.json",
        school_branches_path: str = "school_branches_v2.json"
    ):
        self.motives_map: Dict[str, str] = {}
        self.majors_db: Dict[str, Dict] = {}
        self.trait_map: Dict[str, Dict[int, List[str]]] = {}
        self.value_poles: Dict[str, str] = {}
        self.school_branches: Dict[str, Dict] = {}
        self._load_data(motives_path, majors_path, trait_map_path, value_poles_path, school_branches_path)
        self._validate_schema_consistency()

    def _load_data(self, motives_path, majors_path, trait_map_path, value_poles_path, school_branches_path):
        try:
            self.motives_map = self._load_json(motives_path, key_field="code", value_field="description_fa")
            logger.info(f"✅ {len(self.motives_map)} میکروموتیو بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری میکروموتیوها: {e}")
            self.motives_map = {}

        try:
            self.majors_db = self._load_json(majors_path, key_field="id")
            logger.info(f"✅ {len(self.majors_db)} رشته/شاخه بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری رشته‌ها/شاخه‌ها: {e}")
            self.majors_db = {}

        try:
            with open(trait_map_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                self.trait_map = {
                    q_key: {int(k): v for k, v in options.items()}
                    for q_key, options in raw.items()
                }
            logger.info(f"✅ trait_map_v3 برای {len(self.trait_map)} سوال بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری trait_map_v3: {e}")
            self.trait_map = {}

        try:
            with open(value_poles_path, "r", encoding="utf-8") as f:
                self.value_poles = json.load(f)
            logger.info(f"✅ value_poles با {len(self.value_poles)} قطب بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری value_poles: {e}")
            self.value_poles = {}

        try:
            branches = self._load_json(school_branches_path)
            self.school_branches = {b.get("name"): b for b in branches}
            logger.info(f"✅ شاخه‌های دبیرستانی بارگذاری شد ({len(self.school_branches)} شاخه).")
        except Exception as e:
            logger.error(f"خطا در بارگذاری شاخه‌ها: {e}")
            self.school_branches = {}

    def _load_json(self, path: str, key_field: Optional[str] = None,
                   value_field: Optional[str] = None) -> Dict:
        if not Path(path).exists():
            raise FileNotFoundError(f"فایل {path} یافت نشد.")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if key_field and isinstance(data, list):
            if value_field:
                return {item[key_field]: item.get(value_field, "") for item in data if key_field in item}
            return {item[key_field]: item for item in data if key_field in item}
        return data

    def _validate_schema_consistency(self) -> None:
        """
        اعتبارسنجی هم‌ترازی موقعیتی بین strategy_weights (majors_database) و trait_map_v3.
        این دو فایل با فرض ترتیب یکسان S01..S25 به‌هم متصل می‌شوند، بدون شناسهٔ صریح مشترک.
        هرگونه ناهماهنگی اینجا لاگ می‌شود تا به‌جای خطای خاموش در runtime، در بارگذاری دیده شود.
        """
        expected_keys = {f"S{i:02d}" for i in range(1, 26)}
        trait_keys = set(self.trait_map.keys())
        if trait_keys != expected_keys:
            missing = expected_keys - trait_keys
            extra = trait_keys - expected_keys
            logger.warning(
                f"⚠️ trait_map_v3 با سؤالات مورد انتظار (S01..S25) هم‌تراز نیست. "
                f"موارد گم‌شده: {sorted(missing) or '—'} | موارد اضافه: {sorted(extra) or '—'}"
            )

        bad_rows = 0
        no_prestige = 0
        for major_id, major_data in self.majors_db.items():
            sw = major_data.get("strategy_weights", [])
            if len(sw) != 25:
                bad_rows += 1
                logger.warning(
                    f"⚠️ رشته/شاخه '{major_data.get('name', major_id)}' به‌جای ۲۵ سطر strategy_weights، "
                    f"{len(sw)} سطر دارد — احتمال جابه‌جایی نگاشت با trait_map."
                )
            if "prestige_level" not in major_data:
                no_prestige += 1

        if no_prestige and no_prestige == len(self.majors_db):
            logger.warning(
                f"⚠️ هیچ‌کدام از {len(self.majors_db)} رشته فیلد 'prestige_level' ندارند؛ "
                f"market_demand_level برای همه None خواهد بود."
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

    # ──────────────────────────────────────────────────────────────
    # محاسبه M-Score برای شاخه‌ها (مخرج ۳۰)
    # ──────────────────────────────────────────────────────────────
    def _compute_branch_m_score(self, user_motives: List[str], branch_data: Dict) -> Tuple[float, List[Dict]]:
        if not user_motives:
            return 0.0, []

        raw_codes = branch_data.get("micro_motive_codes", [])
        if not raw_codes:
            return 0.0, []

        user_set = {str(m).strip().lower() for m in user_motives if m and str(m).strip()}
        branch_set = {str(c).strip().lower() for c in raw_codes if c and str(c).strip()}
        matched = user_set & branch_set

        if not matched:
            return 0.0, []

        denom_limit = branch_data.get("m_score_denom_limit", 30)
        denom = min(len(branch_set), denom_limit)
        score = len(matched) / denom

        matched_details = []
        for code in user_motives:
            code_lower = str(code).strip().lower()
            if code_lower in matched:
                desc = self.motives_map.get(code, "") or self.motives_map.get(code.upper(), "")
                matched_details.append({"code": code, "description": desc})

        return min(1.0, score), matched_details

    # ── S-Score ──
    def _compute_s_score(self, strategy_answers: List[int], strategy_weights: List[List[float]]) -> Tuple[float, List[str]]:
        if not strategy_weights or not strategy_answers:
            return 0.0, []

        total_score = 0.0
        valid = 0
        highlights = []

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
            valid += 1

            if normalized >= 0.7:
                q_num = i + 1
                question_key = f"S{str(q_num).zfill(2)}"
                traits = self.trait_map.get(question_key, {}).get(idx, [])
                if traits:
                    trait_names = "، ".join(traits)
                    highlights.append(f"سبک «{trait_names}» با این رشته هم‌خوانی بالایی دارد ({int(normalized*100)}%)")
                else:
                    highlights.append(f"گزینه {idx+1} با این رشته هم‌خوانی بالایی دارد ({int(normalized*100)}%)")

        final_score = (total_score / valid) if valid > 0 else 0.0
        return final_score, highlights

    # ── V-Score ──
    def _compute_v_score(self, value_choices: List[str], value_weights: Dict[str, float]) -> Tuple[float, List[str]]:
        if not value_choices or not value_weights:
            return 0.0, []

        total = 0.0
        valid = 0
        highlights = []

        for v in value_choices:
            if not v or not v.strip():
                continue
            weight = value_weights.get(v.strip(), 0.0)
            total += weight
            valid += 1
            if weight > 0.7:
                pole = self.value_poles.get(v.strip(), v)
                highlights.append(f"ارزش «{pole}»: هم‌راستایی قوی")

        score = min(1.0, total / valid) if valid > 0 else 0.0
        return score, highlights

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
    def _find_alternative_paths(self, major_id: str, top_n: int = 3) -> List[Dict]:
        target = self.majors_db.get(major_id)
        if not target:
            return []

        target_vw = target.get("value_weights", {})
        target_sw = target.get("strategy_weights", [])
        target_v_vec = [target_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
        target_s_vec = self._strategy_profile_vector(target_sw)

        distances = []
        for other_id, other_data in self.majors_db.items():
            if other_id == major_id:
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
    def _find_branch_alternative_paths(self, branch_name: str, top_n: int = 3) -> List[Dict]:
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

    # ── استخراج ویژگی‌های ناهمسو ──
    def _extract_s_misaligned_traits(self, strategy_answers, strategy_weights):
        traits = []
        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers):
                continue
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue
            if row[idx] < 0.3:
                q_num = i + 1
                question_key = f"S{str(q_num).zfill(2)}"
                trait_list = self.trait_map.get(question_key, {}).get(idx, [])
                if trait_list:
                    traits.extend(trait_list)
                else:
                    traits.append(f"گزینه {idx+1}")
        return list(dict.fromkeys(traits))[:3]

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
            if s_aligned and v_aligned:
                desc += "اگرچه خرده‌انگیزه‌های شما همخوانی مستقیمی با این رشته ندارد، اما راهبردهای شخصی و ارزش‌های بنیادین شما با روحیهٔ این حرفه هماهنگی خوبی نشان می‌دهد. این رشته می‌تواند یک گزینهٔ آلترناتیو غیرمنتظره اما بالقوه موفق برای شما باشد."
            elif s_aligned:
                desc += "خرده‌انگیزه‌های شما با این رشته همسو نیستند، اما راهبردهای شخصی شما همخوانی خوبی با این حرفه دارد. اگر به این مسیر علاقه دارید، می‌توانید آن را به‌عنوان یک انتخاب نامتعارف در نظر بگیرید."
            elif v_aligned:
                desc += "خرده‌انگیزه‌های شما با این رشته همسو نیستند، اما ارزش‌های بنیادین شما همخوانی خوبی با این حرفه دارد. این رشته می‌تواند از منظر معنا و رضایت درونی برایتان جذاب باشد، هرچند جرقه‌های روزمرهٔ آن را کمتر دوست داشته باشید."
        else:
            desc += "خرده‌انگیزه‌های شما با این رشته همسو هستند. راهبردهای شخصی و ارزش‌های شما در سطح متوسطی با این رشته هماهنگ‌اند. می‌توانید این مسیر را به عنوان یک گزینه در نظر بگیرید."

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
        # به‌جای برگرداندن هر صفتی که از آستانه رد شود (که تا ۸ مورد می‌شد و شلوغ بود)،
        # صفات را بر اساس قدرت واقعی (normalized) رتبه‌بندی می‌کنیم و فقط قوی‌ترین‌ها را نگه می‌داریم.
        trait_strength: Dict[str, float] = {}
        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers):
                continue
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue
            max_w = max(row) if row else 1.0
            chosen_w = row[idx]
            normalized = chosen_w / max_w if max_w > 0 else 0.0
            if normalized >= threshold:
                q_num = i + 1
                question_key = f"S{str(q_num).zfill(2)}"
                traits = self.trait_map.get(question_key, {}).get(idx, [])
                for t in traits:
                    trait_strength[t] = max(trait_strength.get(t, 0.0), normalized)

        ranked = sorted(trait_strength.items(), key=lambda x: -x[1])
        return [t for t, _ in ranked[:top_n]]

    def _extract_dominant_values(self, value_choices: List[str], value_weights: Dict[str, float],
                                  threshold: float = 0.7, top_n: int = 2) -> List[str]:
        value_strength: Dict[str, float] = {}
        for v in value_choices:
            if not v or not v.strip():
                continue
            weight = value_weights.get(v.strip(), 0.0)
            if weight > threshold:
                pole = self.value_poles.get(v.strip(), v)
                value_strength[pole] = max(value_strength.get(pole, 0.0), weight)

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
        strategy_answers = []
        for i in range(1, 26):
            key = f"sjt_{i}"
            ans = (sjt_answers or {}).get(key, "").strip().upper()
            strategy_answers.append(ord(ans) - ord('A') if len(ans) == 1 and 'A' <= ans <= 'E' else -1)

        value_choices = []
        for i in range(1, 16):
            key = f"conj_{i}"
            val = (conjoint_choices or {}).get(key, "").strip().upper()
            if val and val.startswith('Q'):
                value_choices.append(val)
            else:
                value_choices.append("")

        discovered = []
        for major_id, major_data in self.majors_db.items():
            try:
                m_score, m_ev = self._compute_m_score(user_motives or [], major_data)
                # فیلتر سخت خرده‌انگیزه: بدون همپوشانی واقعی جرقه، رشته نباید فقط با S/V بیاید.
                # (حذف قبلی این شرط باعث ظاهر شدن رشته‌ها تا ~۳۰–۴۵٪ فقط از روی راهبرد/ارزش شد.)
                if m_score < 0.15:
                    continue

                s_score, s_high = self._compute_s_score(strategy_answers, major_data.get("strategy_weights", []))
                v_score, v_high = self._compute_v_score(value_choices, major_data.get("value_weights", {}))

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

        return {
            "discovered_majors": discovered,
            "summary": {
                "total_majors_analyzed": len(self.majors_db),
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
                "version": "3.1-alternative-paths",
                "trait_map_version": "v3 (چند ویژگی در هر گزینه)",
                "features": ["کهن‌الگو و منبع رضایت از دیتابیس", "مسیرهای جایگزین با پروفایل کامل ۱۲۵بعدی Strategy", "سناریوهای ۸ گانه"]
            },
            "next_step": "برای مشاهده شانس قبولی دانشگاه‌ها، اطلاعات سنجش خود را وارد کنید",
        }

    # ──────────────────────────────────────────────────────────────
    #  متد ۲: هدایت تحصیلی پایه نهم (توصیه شاخه)
    #  فرمول: Total = 0.60×M + 0.20×S + 0.20×V
    #  M-Score با مخرج ۳۰ محاسبه می‌شود
    # ──────────────────────────────────────────────────────────────
    def recommend_school_branch(self, user_motives, sjt_answers, conjoint_choices) -> Dict:
        strategy_answers = []
        for i in range(1, 26):
            key = f"sjt_{i}"
            ans = (sjt_answers or {}).get(key, "").strip().upper()
            strategy_answers.append(ord(ans) - ord('A') if len(ans) == 1 and 'A' <= ans <= 'E' else -1)

        value_choices = []
        for i in range(1, 16):
            key = f"conj_{i}"
            val = (conjoint_choices or {}).get(key, "").strip().upper()
            if val and val.startswith('Q'):
                value_choices.append(val)
            else:
                value_choices.append("")

        branch_scores = []

        for branch_name, branch_data in self.school_branches.items():
            m_score, m_ev = self._compute_branch_m_score(user_motives, branch_data)
            s_score, s_high = self._compute_s_score(strategy_answers, branch_data.get("strategy_weights", []))
            v_score, v_high = self._compute_v_score(value_choices, branch_data.get("value_weights", {}))
            total = (0.60 * m_score) + (0.20 * v_score) + (0.20 * s_score)

            branch_info = {
                "branch_name": branch_name,
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
            "best_branch": best_branch,
            "summary": {
                "total_majors_analyzed": len(self.majors_db),
                "branches_analyzed": len(branch_scores)
            },
            "method": {
                "principle": "هدایت تحصیلی — توصیه شاخه دبیرستانی",
                "scoring": "Total = 0.60×M + 0.20×S + 0.20×V",
                "m_denom_limit": "30",
                "alternative_path_formula": "D = √(0.60×RMS(V)^2 + 0.40×RMS(S)^2), S = 125D",
                "filter": "بهترین شاخه فقط از بین شاخه‌های با M ≥ 15% انتخاب می‌شود",
                "features": ["M-Score مستقیم از شاخه", "S و V از شاخه", "مسیرهای جایگزین با پروفایل کامل ۱۲۵بعدی Strategy"],
                "version": "3.1-branch-recommendation"
            },
            "next_step": "بر اساس این نتایج، شاخه‌ای که بیشترین امتیاز را دارد و همخوانی انگیزه‌ی بالایی دارد، مناسب‌ترین گزینه برای شماست."
        }
