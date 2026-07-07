"""
Dark Horse Engine V2.0 — با دیباگ داخلی برای عیب‌یابی V-Score
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger("darkhorse_engine_v2")


class DarkHorseEngineV2:
    def __init__(
        self,
        motives_path: str = "micro_motives.json",
        majors_path: str = "majors_database_v2.json",
        trait_map_path: str = "trait_map_v2.json",
        value_poles_path: str = "value_poles_v2.json"
    ):
        self.motives_map: Dict[str, str] = {}
        self.majors_db: Dict[str, Dict] = {}
        self.trait_map: Dict[int, List[str]] = {}
        self.value_poles: Dict[str, str] = {}
        self._load_data(motives_path, majors_path, trait_map_path, value_poles_path)

    def _load_data(self, motives_path, majors_path, trait_map_path, value_poles_path):
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
                raw_trait_map = json.load(f)
                self.trait_map = {int(k): v for k, v in raw_trait_map.items()}
            logger.info(f"✅ trait_map برای {len(self.trait_map)} سؤال بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری trait_map: {e}")
            self.trait_map = {}

        try:
            with open(value_poles_path, "r", encoding="utf-8") as f:
                self.value_poles = json.load(f)
            logger.info(f"✅ value_poles با {len(self.value_poles)} قطب بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری value_poles: {e}")
            self.value_poles = {}

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

        denom_limit = major_data.get("m_score_denom_limit", len(major_set))
        denom = min(len(major_set), denom_limit)
        score = len(matched) / denom

        matched_details = []
        for code in user_motives:
            code_lower = str(code).strip().lower()
            if code_lower in matched:
                desc = self.motives_map.get(code, "") or self.motives_map.get(code.upper(), "")
                matched_details.append({"code": code, "description": desc})

        return min(1.0, score), matched_details

    def _compute_s_score(self, strategy_answers: List[int], strategy_weights: List[List[float]]) -> Tuple[float, List[str]]:
        if not strategy_weights or not strategy_answers:
            return 0.0, []

        total_weight = 0.0
        valid = 0
        highlights = []

        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers):
                continue
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue
            total_weight += row[idx]
            valid += 1
            if row[idx] > 0.7:
                q_num = i + 1
                trait_name = "نامشخص"
                if q_num in self.trait_map and idx < len(self.trait_map[q_num]):
                    trait_name = self.trait_map[q_num][idx]
                highlights.append(f"سبک «{trait_name}» با این رشته هم‌خوانی بالایی دارد")

        score = min(1.0, total_weight / valid) if valid > 0 else 0.0
        return score, highlights

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
                highlights.append(f"ارزش {v}: هم‌راستایی قوی")

        score = min(1.0, total / valid) if valid > 0 else 0.0
        return score, highlights

    def _build_evidence(self, m_evidence, s_score, s_highlights, v_score, v_highlights):
        evidence = {"micro_motives_matched": m_evidence}
        if s_highlights:
            evidence["strategy_highlights"] = s_highlights
        if v_highlights:
            evidence["value_alignment"] = v_highlights
        warnings = []
        if s_score < 0.4:
            warnings.append("راهبردهای شخصی شما با الگوی رایج این رشته/شاخه تفاوت‌هایی دارد.")
        if v_score < 0.4:
            warnings.append("برخی ارزش‌های بنیادین شما با اولویت‌های این رشته/شاخه فاصله دارد.")
        if warnings:
            evidence["warnings"] = warnings
        return evidence

    @staticmethod
    def _get_fit_level(score: float) -> str:
        if score >= 80: return "همخوانی بسیار بالا"
        elif score >= 60: return "همخوانی بالا"
        elif score >= 40: return "همخوانی متوسط"
        else: return "همخوانی پایین"

    def _extract_s_misaligned_traits(self, strategy_answers, strategy_weights):
        traits = []
        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers): continue
            ans = strategy_answers[i]
            if ans < 0 or ans >= len(row): continue
            if row[ans] < 0.3:
                q_num = i + 1
                trait = "نامشخص"
                if q_num in self.trait_map and ans < len(self.trait_map[q_num]):
                    trait = self.trait_map[q_num][ans]
                traits.append(trait)
        return list(dict.fromkeys(traits))[:3]

    def _extract_v_misaligned_poles(self, value_choices, value_weights):
        poles = []
        for v in value_choices:
            if not v or not v.strip() or not v.startswith('Q'): continue
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

    def _generate_scenario_description(self, major_name, m_evidence, m_score, s_score, v_score,
                                       strategy_answers, strategy_weights, value_choices, value_weights):
        m_aligned = m_score >= 0.3
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
            logger.warning(f"Unexpected scenario for {major_name}: M={m_score:.2f}, S={s_score:.2f}, V={v_score:.2f}")
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

    # ======================= متد اصلی =======================
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
            # val is expected to be a full code like 'Q1A' or 'Q1B'
            if val and val.startswith('Q'):
                value_choices.append(val)
            else:
                value_choices.append("")


        discovered = []
        for major_id, major_data in self.majors_db.items():
            try:
                m_score, m_ev = self._compute_m_score(user_motives or [], major_data)
                if m_score < 0.15: continue

                s_score, s_high = self._compute_s_score(strategy_answers, major_data.get("strategy_weights", []))
                v_score, v_high = self._compute_v_score(value_choices, major_data.get("value_weights", {}))
                total = (0.60 * m_score) + (0.20 * s_score) + (0.20 * v_score)
                final_score = round(total * 100, 1)
                if final_score < 30.0: continue

                evidence = self._build_evidence(m_ev, s_score, s_high, v_score, v_high)
                personalized = self._generate_scenario_description(
                    major_data.get("name", ""), m_ev, m_score, s_score, v_score,
                    strategy_answers, major_data.get("strategy_weights", []),
                    value_choices, major_data.get("value_weights", {})
                )

                discovered.append({
                    "major_id": major_id,
                    "major_name_fa": major_data.get("name", ""),
                    "realm_fa": major_data.get("group", ""),
                    "individuality_fit": {
                        "score": final_score,
                        "level": self._get_fit_level(final_score),
                        "market_demand_level": major_data.get("prestige_level", 2),
                        "raw_components": {"m_score": round(m_score*100,1), "s_score": round(s_score*100,1), "v_score": round(v_score*100,1)},
                        "evidence": evidence,
                        "personalized_description": personalized,
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
            "summary": {"total_majors_analyzed": len(self.majors_db), "total_matches": len(discovered), "high_compatibility": high, "medium_compatibility": med, "low_compatibility": low},
            "method": {"principle": "کشف فردیت — نسخه ۲.۰", "scoring": "Total = 0.60×M + 0.20×S + 0.20×V", "filter": "نمایش رشته‌ها با Total ≥ 30% و M ≥ 15%", "version": "2.0"},
            "next_step": "برای مشاهده شانس قبولی دانشگاه‌ها، اطلاعات سنجش خود را وارد کنید",
        }