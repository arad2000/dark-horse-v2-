"""
Dark Horse Engine V2 — نسخه یکپارچه و نهایی
موتور توصیه رشته/شاخه (جایگزین V2 + V22 + V23)
با فرمول جدید: Total = 0.55×M + 0.30×V + 0.15×S
با قابلیت‌های: کهن‌الگو، جمله هویت، مسیرهای جایگزین
فیلترها: M ≥ 15% و Total ≥ 30%
"""
import json
import logging
import os
from typing import Dict, List, Optional, Tuple
from math import sqrt
from collections import Counter

logger = logging.getLogger("dark_horse_engine_v2")


class DarkHorseEngineV2:
    """موتور توصیه رشته/شاخه — نسخه یکپارچه با قابلیت‌های جدید"""

    def __init__(
        self,
        motives_path: str = "micro_motives.json",
        majors_path: str = "majors_database_v2_final.json",
        trait_map_path: str = "trait_map_v3.json",
        value_poles_path: str = "value_poles_v2.json",
    ):
        self.motives_map: Dict[str, str] = {}
        self.majors_db: Dict[str, Dict] = {}
        self.trait_map: Dict[str, Dict] = {}
        self.value_poles: Dict[str, str] = {}
        self._load_data(motives_path, majors_path, trait_map_path, value_poles_path)

    @staticmethod
    def _resolve(path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)

    def _load_data(self, motives_path, majors_path, trait_map_path, value_poles_path):
        try:
            self.motives_map = self._load_json(motives_path, key_field="code", value_field="description_fa")
            logger.info(f"✅ {len(self.motives_map)} میکروموتیو بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری میکروموتیوها: {e}")

        try:
            self.majors_db = self._load_json(majors_path, key_field="id")
            logger.info(f"✅ {len(self.majors_db)} رشته/شاخه بارگذاری شد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری رشته‌ها: {e}")

        try:
            self.trait_map = self._load_json(trait_map_path)
            logger.info(f"✅ تریت مپ بارگذاری شد ({len(self.trait_map)} کلید).")
        except Exception as e:
            logger.error(f"خطا در بارگذاری تریت مپ: {e}")

        try:
            with open(self._resolve(value_poles_path), "r", encoding="utf-8") as f:
                self.value_poles = json.load(f)
            logger.info(f"✅ value_poles بارگذاری شد ({len(self.value_poles)} قطب).")
        except Exception as e:
            logger.error(f"خطا در بارگذاری value_poles: {e}")

    def _load_json(self, path: str, key_field: Optional[str] = None,
                   value_field: Optional[str] = None) -> Dict:
        full = self._resolve(path)
        with open(full, "r", encoding="utf-8") as f:
            data = json.load(f)
        if key_field and isinstance(data, list):
            if value_field:
                return {item[key_field]: item.get(value_field, "") for item in data if key_field in item}
            return {item[key_field]: item for item in data if key_field in item}
        return data

    # ── M: امتیاز میکروموتیو ──
    def _compute_m_score(self, user_motives: List[str], major_data: Dict) -> Tuple[float, List[Dict]]:
        if not user_motives:
            return 0.0, []
        raw_codes = major_data.get("micro_motive_codes", [])
        if not raw_codes:
            return 0.0, []
        user_set = {str(m).strip().lower() for m in user_motives if m and str(m).strip()}
        major_set = {str(c).strip().lower() for c in raw_codes if c and str(c).strip()}
        matched = user_set & major_set
        if not matched:
            return 0.0, []
        denom = len(major_set)  # استفاده از مخرج واقعی
        score = len(matched) / denom * 100 if denom > 0 else 0.0
        evidence = []
        for code in matched:
            orig = next((c for c in raw_codes if str(c).strip().lower() == code), code)
            desc = self.motives_map.get(orig, self.motives_map.get(code.upper(), code))
            evidence.append({"code": orig, "description": desc})
        return round(score, 1), evidence

    # ── S: امتیاز راهبرد ──
    def _compute_s_score(self, strategy_answers: List[int],
                         strategy_weights: List[List[float]]) -> Tuple[float, List[Dict]]:
        if not strategy_weights or not strategy_answers:
            return 0.0, []
        total = 0.0
        highlights = []
        n = len(strategy_weights)
        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers):
                break
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue
            max_w = max(row)
            if max_w <= 0:
                continue
            chosen_w = row[idx]
            total += chosen_w / max_w
            if chosen_w >= 0.15:
                traits = self.trait_map.get(f"S{i+1:02d}", {}).get(str(idx), [])
                highlights.append({
                    "question": f"S{i+1:02d}",
                    "choice": idx,
                    "weight": round(chosen_w, 3),
                    "traits": traits,
                })
        score = (total / n) * 100 if n else 0.0
        return round(score, 1), highlights

    # ── V: امتیاز ارزش ──
    def _compute_v_score(self, value_choices: List[str],
                         value_weights: Dict[str, float]) -> Tuple[float, List[Dict]]:
        if not value_choices or not value_weights:
            return 0.0, []
        total = 0.0
        count = 0
        highlights = []
        for v in value_choices:
            if not v or not str(v).strip():
                continue
            v = str(v).strip()
            weight = value_weights.get(v, 0.0)
            total += weight
            count += 1
            pole = self.value_poles.get(v, v)
            highlights.append({"pole": v, "label": pole, "weight": round(weight, 3)})
        score = (total / count * 100) if count else 0.0
        return round(score, 1), highlights

    # ── کهن‌الگو و جمله هویت ──
    def _generate_archetype_and_identity(self, major_data: Dict) -> Dict:
        vw = major_data.get("value_weights", {})
        sw = major_data.get("strategy_weights", [])
        sorted_vals = sorted(vw.items(), key=lambda x: x[1], reverse=True)
        top_poles = [p for p, w in sorted_vals[:3]]
        
        # تشخیص کهن‌الگو با اولویت‌بندی
        archetype = "هماهنگ‌کننده"
        if "Q4A" in top_poles and "Q11A" in top_poles:
            archetype = "حقیقت‌یاب و تحلیل‌گر"
        elif "Q6A" in top_poles and "Q11B" in top_poles:
            archetype = "مراقب و همدل"
        elif "Q4B" in top_poles and "Q7A" in top_poles:
            archetype = "خالق و آفریننده"
        elif "Q6B" in top_poles and "Q1B" in top_poles:
            archetype = "مدیر و راهبر سیستم"
        elif "Q5A" in top_poles and "Q12B" in top_poles:
            archetype = "دقیق‌کار و پایدار"
        elif "Q3A" in top_poles and "Q15A" in top_poles:
            archetype = "دانشمند و نظریه‌پرداز"
        elif "Q5B" in top_poles and "Q8A" in top_poles:
            archetype = "آزاداندیش و نوآور"

        # استخراج تریت‌های غالب
        dominant_traits = []
        for row in sw:
            if not row:
                continue
            max_w = max(row)
            if max_w > 0.4:
                idx = row.index(max_w)
                q_num = sw.index(row) + 1
                q_key = f"S{q_num:02d}"
                traits = self.trait_map.get(q_key, {}).get(str(idx), [])
                dominant_traits.extend(traits)
        top_traits = list(dict.fromkeys(dominant_traits))[:3]

        domain = major_data.get("group", "حوزه تخصصی")
        identity_base = f"حل مسئله در {domain}" if not top_traits else f"کشف الگوهای پنهان در {domain}"
        identity_sentence = f"{identity_base}؛ با نگاه یک {archetype}"

        return {
            "archetype": archetype,
            "identity_sentence": identity_sentence,
            "dominant_traits": top_traits,
            "dominant_values": [self.value_poles.get(p, p) for p in top_poles[:3]]
        }

    # ── مسیرهای جایگزین ──
    def _find_alternative_paths(self, major_id: str, top_n: int = 3) -> List[Dict]:
        target = self.majors_db.get(major_id)
        if not target:
            return []
        target_vw = target.get("value_weights", {})
        target_sw = target.get("strategy_weights", [])
        target_v_vec = [target_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
        target_s_vec = [max(row) if row else 0.0 for row in target_sw]

        distances = []
        for other_id, other_data in self.majors_db.items():
            if other_id == major_id:
                continue
            other_vw = other_data.get("value_weights", {})
            other_sw = other_data.get("strategy_weights", [])
            other_v_vec = [other_vw.get(f"Q{i}{l}", 0.0) for i in range(1, 16) for l in ["A", "B"]]
            other_s_vec = [max(row) if row else 0.0 for row in other_sw]
            
            v_dist = sqrt(sum((a-b)**2 for a,b in zip(target_v_vec, other_v_vec)) / len(target_v_vec))
            s_dist = sqrt(sum((a-b)**2 for a,b in zip(target_s_vec, other_s_vec)) / len(target_s_vec))
            total_dist = 0.6*v_dist + 0.4*s_dist
            
            distances.append({
                "major_id": other_id,
                "major_name": other_data.get("name", ""),
                "distance": round(total_dist, 3),
                "group": other_data.get("group", "")
            })
        distances.sort(key=lambda x: x["distance"])
        return distances[:top_n]

    # ── هشدار راهبردی دلگرم‌کننده ──
    def _generate_strategy_warning(self, s_score: float, major_name: str) -> Optional[str]:
        if s_score < 40:
            return (
                f"هرچند راهبردهای شخصی شما با رشته‌ی «{major_name}» همخوانی کمتری دارد، "
                f"اما کتاب «اسب سیاه» می‌گوید راهبردها پویا هستند و با آزمون و خطا می‌توانید "
                f"سبک منحصربه‌فرد خود را پیدا کنید. پس خیلی نگران این موضوع نباشید!"
            )
        return None

    # ── ساخت شواهد ──
    def _build_evidence(self, m_evidence, s_highlights, v_highlights,
                        mis_traits, mis_poles) -> Dict:
        evidence = {"micro_motives_matched": m_evidence}
        if s_highlights:
            evidence["strategy_highlights"] = s_highlights[:5]
        if v_highlights:
            evidence["value_alignment"] = v_highlights[:5]
        if mis_traits:
            evidence["misaligned_traits"] = mis_traits[:5]
        if mis_poles:
            evidence["misaligned_poles"] = mis_poles[:5]
        return evidence

    # ── سطح تناسب ──
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

    # ── استخراج ویژگی‌های ناهمسو ──
    def _extract_s_misaligned_traits(self, strategy_answers, strategy_weights) -> List[Dict]:
        mis = []
        for i, row in enumerate(strategy_weights):
            if i >= len(strategy_answers):
                break
            idx = strategy_answers[i]
            if idx < 0 or idx >= len(row):
                continue
            max_w = max(row)
            if max_w <= 0:
                continue
            if row[idx] / max_w < 0.4:
                traits = self.trait_map.get(f"S{i+1:02d}", {}).get(str(idx), [])
                mis.append({"question": f"S{i+1:02d}", "traits": traits})
        return mis

    def _extract_v_misaligned_poles(self, value_choices, value_weights) -> List[Dict]:
        mis = []
        for v in value_choices:
            if not v or not str(v).strip():
                continue
            v = str(v).strip()
            user_weight = value_weights.get(v, 0.0)
            opposite = v[:-1] + ("B" if v.endswith("A") else "A")
            opp_weight = value_weights.get(opposite, 0.0)
            if opp_weight > user_weight:
                mis.append({"pole": v, "label": self.value_poles.get(v, v)})
        return mis

    # ── توضیح سناریو ──
    def _generate_scenario_description(self, major_name, m_evidence,
                                       m_score, s_score, v_score) -> str:
        if not m_evidence:
            return ""
        top = m_evidence[0].get("description", "")
        return (
            f"بر اساس خرده‌انگیزه‌هایت، «{major_name}» می‌تواند گزینه مناسبی برایت باشد. "
            f"قوی‌ترین انگیزه‌ات: {top}"
        )

    # ── متد اصلی ──
    def discover_individuality(self, user_motives, sjt_answers, conjoint_choices) -> Dict:
        # تبدیل پاسخ‌های SJT
        strategy_answers = []
        for i in range(1, 26):
            key = f"sjt_{i}"
            ans = str((sjt_answers or {}).get(key, "")).strip().upper()
            strategy_answers.append(ord(ans) - ord('A') if len(ans) == 1 and 'A' <= ans <= 'E' else -1)

        # تبدیل پاسخ‌های ارزشی
        value_choices = []
        for i in range(1, 16):
            key = f"conj_{i}"
            val = str((conjoint_choices or {}).get(key, "")).strip().upper()
            value_choices.append(val if val.startswith('Q') else "")

        discovered = []
        for major_id, major_data in self.majors_db.items():
            try:
                m_score, m_ev = self._compute_m_score(user_motives or [], major_data)
                if m_score < 15.0:
                    continue

                s_score, s_high = self._compute_s_score(
                    strategy_answers, major_data.get("strategy_weights", [])
                )
                v_score, v_high = self._compute_v_score(
                    value_choices, major_data.get("value_weights", {})
                )

                # ✅ فرمول جدید
                total = (0.55 * m_score) + (0.30 * v_score) + (0.15 * s_score)
                final_score = round(total, 1)

                if final_score < 30.0:
                    continue

                mis_traits = self._extract_s_misaligned_traits(
                    strategy_answers, major_data.get("strategy_weights", [])
                )
                mis_poles = self._extract_v_misaligned_poles(
                    value_choices, major_data.get("value_weights", {})
                )
                evidence = self._build_evidence(m_ev, s_high, v_high, mis_traits, mis_poles)
                
                # هشدار راهبردی
                strategy_warning = self._generate_strategy_warning(s_score, major_data.get("name", ""))
                if strategy_warning:
                    evidence.setdefault("warnings", []).append(strategy_warning)

                description = self._generate_scenario_description(
                    major_data.get("name", ""), m_ev, m_score, s_score, v_score
                )

                # تولید کهن‌الگو و مسیرهای جایگزین
                archetype_info = self._generate_archetype_and_identity(major_data)
                alt_paths = self._find_alternative_paths(major_id, top_n=3)

                discovered.append({
                    "major_id": major_id,
                    "major_name_fa": major_data.get("name", ""),
                    "realm_fa": major_data.get("group", ""),
                    "cluster": major_data.get("cluster", ""),
                    "individuality_fit": {
                        "score": final_score,
                        "level": self._get_fit_level(final_score),
                        "market_demand_level": major_data.get("market_demand_level", 2),
                        "raw_components": {
                            "m_score": m_score,
                            "s_score": s_score,
                            "v_score": v_score,
                        },
                        "evidence": evidence,
                        "personalized_description": description,
                        "archetype": archetype_info,
                        "alternative_paths": alt_paths,
                    },
                })
            except Exception as e:
                logger.error(f"خطا در پردازش رشته {major_id}: {e}")
                continue

        discovered.sort(key=lambda x: x["individuality_fit"]["score"], reverse=True)

        high = sum(1 for d in discovered if d["individuality_fit"]["score"] >= 80)
        med = sum(1 for d in discovered if 60 <= d["individuality_fit"]["score"] < 80)
        low = sum(1 for d in discovered if d["individuality_fit"]["score"] < 60)

        return {
            "discovered_majors": discovered,
            "summary": {
                "total_majors_analyzed": len(self.majors_db),
                "total_matches": len(discovered),
                "high_compatibility": high,
                "medium_compatibility": med,
                "low_compatibility": low,
            },
            "method": {
                "principle": "کشف فردیت — نسخه یکپارچه با قابلیت‌های جدید",
                "scoring": "Total = 0.55×M + 0.30×V + 0.15×S",
                "s_score_formula": "S = (1/25) × Σ(chosen_w / max_w)",
                "filter": "نمایش رشته‌ها با Total ≥ 30% و M ≥ 15%",
                "version": "2.1-enhanced",
                "trait_map_version": "v3 (چند ویژگی در هر گزینه)",
                "features": ["کهن‌الگو", "جمله هویت", "مسیرهای جایگزین"]
            },
            "next_step": "لطفاً رشته‌های معرفی‌شده را بررسی کن و گزینه‌های مورد علاقه‌ات را انتخاب کن.",
        }
