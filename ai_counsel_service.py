"""AI counseling via Cloudflare Workers AI — Dark Horse philosophy.

Four prompt modes:
  branches + main         → تحلیل شاخه کشف‌شده دبیرستان
  branches + alternatives → تحلیل مسیرهای جایگزین شاخه
  majors   + main         → تحلیل رشته‌های دانشگاهی کشف‌شده
  majors   + alternatives → تحلیل مسیرهای جایگزین رشته

All grounded in M (خرده‌انگیزه/جرقه), S (راهبرد), V (ارزش).

نسخهٔ بازنویسی‌شده — تغییرات کلیدی نسبت به نسخهٔ قبلی:
  ۱) از شواهد متنی واقعی موتور (evidence.micro_motives_matched،
     evidence.strategy_highlights، evidence.value_alignment) استفاده
     می‌شود، نه فقط اعداد درصد خام. این تنها راهی است که مدل زبانی
     می‌تواند توضیحی «اختصاصی» بنویسد نه کلی‌گویی.
  ۲) قید صریح ضدِتوهم: مدل هرگز نباید چیزی را که در داده نیامده حدس
     بزند یا دربارهٔ «نامشخص‌بودن» یک فیلد توضیح بدهد؛ به‌سادگی از آن
     می‌گذرد.
  ۳) قید صریح بی‌طرفی: بدون گرایش به‌خاطر پرستیژ اجتماعی رشته، جنسیت
     مخاطب، یا کلیشه‌های رایج.
  ۴) الزام مقایسهٔ واقعی بین گزینه‌ها (نه توصیف جداگانه و تکراری).
  ۵) کالیبراسیون لحن با باند امتیاز (خیلی‌بالا/بالا/متوسط/پایین) که
     در پایتون محاسبه می‌شود، نه حدس مدل از روی عدد خام.
  ۶) حذف اعداد خام فاصله (value_distance/strategy_distance) از متنی
     که قرار است عیناً در خروجی ظاهر شود؛ فقط برچسب کیفی به مدل داده
     می‌شود.
  ۷) فهرست صریح عبارات کلیشه‌ای ممنوع + یک مثال کوتاه تضادی (بد/خوب)
     برای لنگر سبک نوشتاری، چون مدل‌های کوچک‌تر بدون نمونه به کلیشه
     برمی‌گردند.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from fastapi import HTTPException

DEFAULT_MODEL = "@cf/meta/llama-4-scout-17b-16e-instruct"


def _cfg() -> tuple[str, str, str]:
    account = (os.getenv("CF_ACCOUNT_ID") or "").strip()
    token = (os.getenv("CF_API_TOKEN") or "").strip()
    model = (os.getenv("CF_AI_MODEL") or DEFAULT_MODEL).strip()
    if not account or not token:
        raise HTTPException(
            status_code=503,
            detail="سرویس توضیح مشاوره‌ای هنوز پیکربندی نشده است.",
        )
    return account, token, model


# ─────────────────────────────────────────────────────────────────────────
# ابزارهای کمکی پایه
# ─────────────────────────────────────────────────────────────────────────

def _clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip())


def _short_motive(m: Any) -> str:
    s = _clean(m)
    if ":" in s:
        s = s.split(":", 1)[0].strip()
    if "：" in s:
        s = s.split("：", 1)[0].strip()
    return s[:48]


def _pct(val: Any) -> float | None:
    try:
        n = float(val)
        if n <= 1:
            n *= 100
        return round(n, 1)
    except Exception:
        return None


def _pct_str(val: Any) -> str:
    n = _pct(val)
    return f"{n:.0f}" if n is not None else "—"


def _score_band(score: float | None) -> str:
    """برچسب کیفی امتیاز — تا مدل مجبور به حدس‌زدن از روی عدد خام نباشد."""
    if score is None:
        return "نامعلوم"
    if score >= 85:
        return "خیلی بالا"
    if score >= 70:
        return "بالا"
    if score >= 55:
        return "متوسط رو به بالا"
    if score >= 40:
        return "متوسط"
    return "پایین (هنوز از آستانهٔ حداقلی رد شده)"


def _is_branch(journey_type: str, profile: dict[str, Any] | None = None) -> bool:
    kind = (journey_type or (profile or {}).get("kind") or "majors").lower()
    return kind in ("branches", "branch")


def _motives_text(profile: dict[str, Any]) -> str:
    """زمینهٔ کلی خرده‌انگیزه‌های کاربر (نه لزوماً مرتبط با یک رشتهٔ خاص)."""
    raw = (
        profile.get("micro_motives")
        or profile.get("liked_motives")
        or profile.get("likedCodes")
        or profile.get("sparks")
        or []
    )
    items = [_short_motive(m) for m in raw[:15]]
    items = [m for m in items if m]
    return "، ".join(items) if items else ""


# ─────────────────────────────────────────────────────────────────────────
# استخراج شواهد واقعی از خروجی موتور (بخش کلیدیِ اصلاح‌شده)
# ─────────────────────────────────────────────────────────────────────────

def _matched_evidence_lines(r: dict[str, Any], limit: int = 4) -> list[str]:
    """جملات شاهدِ اختصاصیِ همین گزینه (نه زمینهٔ کلی کاربر).

    این دقیقاً همان متنی است که در discover_individuality زیر
    evidence.micro_motives_matched برمی‌گردد؛ تا امروز در پرامپت
    استفاده نمی‌شد و بزرگ‌ترین علت کلی‌گویی بود.
    """
    ev = r.get("evidence") or {}
    items = ev.get("micro_motives_matched") or []
    out: list[str] = []
    for it in items[:limit]:
        if isinstance(it, dict):
            desc = _clean(it.get("description") or it.get("desc") or "")
        else:
            desc = _clean(it)
        if desc:
            out.append(desc)
    return out


def _narrative_bullets(r: dict[str, Any]) -> tuple[list[str], list[str]]:
    """جملات آماده و شواهدمحورِ خودِ موتور — استفاده نکردن از این‌ها
    یعنی دور ریختن دقیق‌ترین چیزی که سیستم برای این کاربر تولید کرده.
    """
    ev = r.get("evidence") or {}
    strat = [_clean(x) for x in (ev.get("strategy_highlights") or [])]
    val = [_clean(x) for x in (ev.get("value_alignment") or [])]
    return [s for s in strat if s], [v for v in val if v]


def _arch_bits(r: dict[str, Any]) -> tuple[str, list[str], list[str], str]:
    """برمی‌گرداند: نام کهن‌الگو، ارزش‌های غالب، راهبردهای غالب، منبع رضایت.
    هرکدام موجود نبود، رشتهٔ خالی برمی‌گردد (نه «—») تا در متن نهایی
    غیبتش دیده/اشاره نشود.
    """
    arch = r.get("archetype") or {}
    if isinstance(arch, str):
        arch = {"archetype": arch}
    name = _clean(arch.get("archetype") or "")
    vals = [str(x) for x in (arch.get("dominant_values") or []) if str(x).strip()]
    traits = [str(x) for x in (arch.get("dominant_traits") or []) if str(x).strip()]
    fulfill = _clean(r.get("fulfillment_source") or arch.get("fulfillment_source") or "")
    return name, vals, traits, fulfill


def _alt_line(a: Any) -> str:
    """برچسب کیفیِ یک مسیر جایگزین — بدون درز کردن عدد خام فاصله به متن."""
    if not isinstance(a, dict):
        return _clean(a)
    name = _clean(
        a.get("branch_name") or a.get("major_name") or a.get("name") or a.get("title") or ""
    )
    if not name:
        return ""
    try:
        vd = float(a["value_distance"]) if a.get("value_distance") is not None else None
    except Exception:
        vd = None
    try:
        sd = float(a["strategy_distance"]) if a.get("strategy_distance") is not None else None
    except Exception:
        sd = None
    if vd is not None and sd is not None:
        gap = abs(vd - sd)
        if gap < 0.02:
            why = "از نظر ترکیب ارزش و راهبرد، هر دو تقریباً یکسان نزدیک‌اند"
        elif vd < sd:
            why = "بیشتر به‌خاطر نزدیکی در ارزش‌ها (V)"
        else:
            why = "بیشتر به‌خاطر نزدیکی در سبک/راهبرد (S)"
        return f"{name} ({why})"
    return name


def _result_block(r: dict[str, Any], idx: int, *, with_alts: bool) -> str:
    if not isinstance(r, dict):
        return f"{idx}. {_clean(r)}"

    name = _clean(r.get("name") or r.get("title") or "")
    score = _pct(r.get("fit_score", r.get("score")))
    band = _score_band(score)
    raw = r.get("raw_components") or r.get("avg_components") or {}
    m = _pct_str(raw.get("m_score", r.get("m_score")))
    s = _pct_str(raw.get("s_score", r.get("s_score")))
    v = _pct_str(raw.get("v_score", r.get("v_score")))

    arch_name, dom_vals, dom_traits, fulfill = _arch_bits(r)
    matched = _matched_evidence_lines(r)
    strat_bullets, val_bullets = _narrative_bullets(r)

    lines = [f"{idx}. «{name}» — همخوانی کلی: {score if score is not None else '—'}٪ (باند: {band})"]
    lines.append(f"   اعداد خام (فقط زمینه؛ در پاسخ عیناً تکرار نکن): M={m}٪ | S={s}٪ | V={v}٪")

    if matched:
        lines.append("   شواهد خرده‌انگیزهٔ اختصاصیِ این گزینه (این‌ها را بازنویسی/ترکیب کن، نه کپی):")
        for d in matched:
            lines.append(f"     • {d}")

    if strat_bullets:
        lines.append("   نکات راهبردیِ محاسبه‌شده توسط سیستم:")
        for b in strat_bullets[:3]:
            lines.append(f"     • {b}")

    if val_bullets:
        lines.append("   نکات ارزشیِ محاسبه‌شده توسط سیستم:")
        for b in val_bullets[:3]:
            lines.append(f"     • {b}")

    if arch_name:
        lines.append(f"   کهن‌الگو: {arch_name}")
    if dom_traits:
        lines.append(f"   راهبردهای غالب: {'، '.join(dom_traits[:5])}")
    if dom_vals:
        lines.append(f"   ارزش‌های غالب: {'، '.join(dom_vals[:5])}")
    if fulfill:
        lines.append(f"   منبع رضایت توصیف‌شده: {fulfill}")

    if with_alts:
        alts = [_alt_line(a) for a in (r.get("alternative_paths") or [])[:5]]
        alts = [a for a in alts if a]
        if alts:
            lines.append("   مسیرهای جایگزین ثبت‌شده: " + "؛ ".join(alts))

    return "\n".join(lines)


def _result_blocks(top_results: list[Any], *, with_alts: bool) -> str:
    blocks = [
        _result_block(r, i, with_alts=with_alts)
        for i, r in enumerate((top_results or [])[:4], 1)
    ]
    return "\n\n".join(blocks) if blocks else ""


# ─────────────────────────────────────────────────────────────────────────
# قواعد مشترک پرامپت — برای جلوگیری از تکرار و ناهماهنگی بین ۴ حالت
# ─────────────────────────────────────────────────────────────────────────

_PHILOSOPHY = """سه شاخص که هر تحلیل باید صریحاً روی آن‌ها بنا شود:
۱) خرده‌انگیزه‌ها / جرقه‌ها (M) — پایدارترین لایهٔ هویت؛ چیزی که فرد
   بدون بیرونی‌ترین انگیزه هم از انجامش لذت می‌برد.
۲) راهبرد (S) — سبک فکر/کار/یادگیری؛ پویا و در طول زمان قابل تقویت.
۳) ارزش (V) — منبع رضایت بلندمدت و معنا؛ نسبتاً پایدار، کندتر از S تغییر می‌کند."""

_ANTI_HALLUCINATION = """قوانین ضدِتوهم (رعایت اکید):
- فقط از داده‌های زیر استفاده کن. هیچ آمار، شغل آینده، بازار کار، حقوق،
  دانشگاه خاص، یا جزئیاتی که در داده نیامده نساز.
- اگر بخشی از داده (مثل کهن‌الگو یا منبع رضایت) برای یک گزینه نیامده،
  به‌سادگی دربارهٔ آن ننویس. هرگز نگو «اطلاعاتی موجود نیست» یا
  «نامشخص» — فقط از کنارش رد شو، انگار اصلاً نپرسیده بودی.
- عدد خام فاصله یا شناسه‌های داخلی (کد رشته، اعداد اعشاری فاصله) را
  در متن نهایی عیناً تکرار نکن؛ فقط برای فهم خودت استفاده کن."""

_NEUTRALITY = """قوانین بی‌طرفی (رعایت اکید):
- هیچ گرایشی به‌خاطر پرستیژ اجتماعی رشته/شغل، جنسیت مخاطب، یا کلیشه‌های
  رایج («این رشته برای پسرها/دخترها مناسب‌تر است») نداشته باش.
- قوت‌ها و ملاحظات واقعی هر گزینه را متوازن بنویس؛ گزینه‌ای را صرفاً
  به‌خاطر رتبهٔ بالاتر در فهرست «بهتر» جلوه نده — تفاوت را با دلیل
  مشخص (کدام شاخص M/S/V) توضیح بده.
- قضاوت را فقط بر پایهٔ داده‌های M/S/V و شواهد زیر بنا کن، نه تصورات
  عمومی دربارهٔ اعتبار اجتماعی رشته‌ها."""

_ANTI_CLICHE = """ممنوعیت کلیشه:
از عبارات فرسوده و بی‌محتوا مثل این‌ها استفاده نکن:
«با پشتکار به موفقیت می‌رسی»، «این رشته برای علاقه‌مندان به X مناسب
است»، «دنیای شگفت‌انگیزی در انتظارت است»، «آینده‌ای روشن خواهی داشت»،
«شایان ذکر است»، «جالب است بدانید».
به‌جای بازخوانیِ عدد («راهبرد او ۹۶٪ است»)، بگو آن عدد در رفتار روزمره
چه معنایی دارد — با تکیه بر شواهد اختصاصی دادهشده، نه با حدس عمومی.

مثال بد (سطحی، از عدد به توصیف کلی می‌پرد):
«چون راهبرد او بالاست، در کارهای تحلیلی موفق خواهد بود.»
مثال خوب (مستقیماً به شاهد متکی است):
«رگهٔ راهبردی‌اش دقیقاً همان چیزی است که در «کشف علت پنهان بیماری در
کمتر از سی ثانیه» می‌بینیم — یعنی به تحلیل سریع و قاطع علاقه دارد، نه
فقط جمع‌آوری آرام اطلاعات.»"""

_CALIBRATION = """کالیبراسیون لحن با باند امتیاز هر گزینه:
«خیلی بالا»/«بالا» → می‌توانی با اطمینان بنویسی، ولی باز هم مطلق نگو
(«قطعاً»، «حتماً موفق می‌شوی» ممنوع است).
«متوسط رو به بالا»/«متوسط» → صریحاً بگو این گزینه هم‌خوانی نسبی/خوب
دارد، نه هم‌خوانی کامل؛ یک نکتهٔ احتیاط واقعی از دل داده‌ها بیاور.
هیچ‌وقت به شکلی ننویس که انگار همهٔ گزینه‌ها یک‌درجه اطمینان دارند."""

_COMPARISON = """اگر بیش از یک گزینه داده شده:
گزینه‌ها را جدا جدا توصیف کن، ولی حتماً یک بخش پایانی مقایسه‌ای هم
بنویس که تفاوت واقعیِ بین دو گزینهٔ برتر را — بر پایهٔ کدام شاخص
(M یا S یا V) یا کدام شاهد — روشن کند. توصیف‌های جدا و بی‌ارتباط که
فقط اسم عوض می‌کنند، کافی نیست."""


# ── ۱) شاخه دبیرستان — تحلیل اصلی ──────────────────────────────────────────
def _prompt_branch_main(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = f"""تو مشاور هدایت تحصیلی متوسطهٔ ایران هستی و بر فلسفهٔ «اسب سیاه» کار می‌کنی.
موضوع: تحلیل شاخهٔ (یا شاخه‌های) دبیرستان کشف‌شده برای یک دانش‌آموز.
این مرحله انتخاب شاخهٔ متوسطه است، نه رشتهٔ دانشگاهی یا شغل.

{_PHILOSOPHY}

{_ANTI_HALLUCINATION}

{_NEUTRALITY}

{_ANTI_CLICHE}

{_CALIBRATION}

{_COMPARISON}

فقط فارسی بنویس. برای هر شاخه یک بخش جدا بساز؛ چیزی را عیناً تکرار نکن."""

    motives_ctx = _motives_text(profile)
    motives_line = f"زمینهٔ خرده‌انگیزه‌های دانش‌آموز: {motives_ctx}\n\n" if motives_ctx else ""

    user = f"""{motives_line}نتایج شاخه (شواهد و اعداد را زیر هر گزینه ببین):
{_result_blocks(top_results, with_alts=False)}

برای هر شاخه با این ساختار بنویس:
### نام شاخه
- جرقه (M): با تکیه بر شواهد اختصاصیِ بالا (نه فقط عدد)، چرا این شاخه با انگیزه‌های روزمرهٔ او هم‌خوان است
- راهبرد (S): بر اساس نکات راهبردی دادهشده، چه سبک یادگیری‌ای در دبیرستان برایش طبیعی‌تر است
- ارزش (V): بر اساس نکات ارزشی دادهشده، چه نوع رضایتی برایش مهم است
- یک نکتهٔ واقع‌بین (نه لزوماً منفی؛ می‌تواند یک هشدار سازگاری یا یک پیشنهاد تقویت مهارت باشد)

اگر بیش از یک شاخه هست، در پایان یک بخش «### تفاوت کلیدی» اضافه کن.
حداکثر ۳۲۰ کلمه."""
    return system, user


# ── ۲) شاخه دبیرستان — مسیرهای جایگزین ────────────────────────────────────
def _prompt_branch_alt(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = f"""تو مشاور هدایت تحصیلی متوسطه هستی (فلسفهٔ اسب سیاه).
موضوع: فقط مسیرهای جایگزینِ شاخهٔ دبیرستان — نه بازگویی مسیر اصلی.

منطق سیستم (این را رعایت کن، نه فقط بیان):
- جایگزین عمدتاً به‌خاطر نزدیکی در ارزش (V) یا راهبرد (S) پیشنهاد
  می‌شود، نه شباهت جرقه (M). جرقه‌ها همچنان اولویت اصلی هویت‌اند؛
  جایگزین «مکمل» است، نه رقیب.

{_ANTI_HALLUCINATION}

{_NEUTRALITY}

{_ANTI_CLICHE}

فقط فارسی بنویس. مسیر اصلی را دوباره کامل شرح نده — فقط در حد لازم برای مقایسه به آن اشاره کن."""

    motives_ctx = _motives_text(profile)
    motives_line = f"زمینهٔ خرده‌انگیزه‌ها (فقط بافت؛ محور توضیح جایگزین نباشد): {motives_ctx}\n\n" if motives_ctx else ""

    user = f"""{motives_line}دادهٔ مسیر اصلی و جایگزین‌ها:
{_result_blocks(top_results, with_alts=True)}

بنویس:
### مسیرهای جایگزین
برای هر جایگزین:
- نام و اینکه نزدیکی‌اش بیشتر از نظر ارزش است یا راهبرد (طبق برچسبی که داده شده)
- این نزدیکی عملاً برای انتخاب شاخه چه معنایی دارد
- تأکید کوتاه که این گزینه «مکمل» است، نه اجبار به تغییر مسیر

### جمع‌بندی
در ۲-۳ جمله: جرقه‌ها اولویت هویت‌اند، ارزش پایدارتر و راهبرد قابل تقویت
است؛ این جایگزین‌ها افق را باز می‌کنند بدون آنکه مسیر اصلی را زیر سؤال ببرند.
حداکثر ۲۸۰ کلمه."""
    return system, user


# ── ۳) رشته دانشگاهی — تحلیل اصلی ─────────────────────────────────────────
def _prompt_major_main(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = f"""تو مشاور هدایت تحصیلی و انتخاب رشتهٔ دانشگاهی هستی و بر فلسفهٔ «اسب سیاه» کار می‌کنی.
موضوع: تحلیل رشته‌های دانشگاهیِ کشف‌شده برای این فرد.

{_PHILOSOPHY}

{_ANTI_HALLUCINATION}

{_NEUTRALITY}

{_ANTI_CLICHE}

{_CALIBRATION}

{_COMPARISON}

فقط فارسی بنویس. برای هر رشته یک بخش جدا و بدون تکرار بساز."""

    motives_ctx = _motives_text(profile)
    motives_line = f"زمینهٔ خرده‌انگیزه‌های فرد: {motives_ctx}\n\n" if motives_ctx else ""

    user = f"""{motives_line}نتایج رشته (شواهد و اعداد را زیر هر گزینه ببین):
{_result_blocks(top_results, with_alts=False)}

برای هر رشته با این ساختار بنویس:
### نام رشته
- جرقه (M): با تکیه بر شواهد اختصاصیِ بالا، همخوانی‌اش با انگیزه‌های او را نشان بده — نه با تکرار عدد
- راهبرد (S): بر اساس نکات راهبردی دادهشده، این رشته چه سبک کار/تفکری می‌طلبد و با سبک او چه نسبتی دارد
- ارزش (V): بر اساس نکات ارزشی دادهشده، این رشته چه نوع رضایت بلندمدتی می‌تواند بدهد
- یک نکتهٔ واقع‌بینانه: یا یک هشدار سازگاری واقعی، یا یک مهارت لازم برای تقویت (نه ترسناک، نه تعارف)

اگر بیش از یک رشته هست، در پایان یک بخش «### تفاوت کلیدی بین گزینه‌ها» اضافه کن که مشخص کند برتری هرکدام از کجا می‌آید.
حداکثر ۳۸۰ کلمه."""
    return system, user


# ── ۴) رشته دانشگاهی — مسیرهای جایگزین ────────────────────────────────────
def _prompt_major_alt(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = f"""تو مشاور انتخاب رشتهٔ دانشگاهی هستی (فلسفهٔ اسب سیاه).
موضوع: فقط مسیرهای جایگزینِ رشته — نه بازگویی رشتهٔ اصلی.

منطق سیستم (این را رعایت کن، نه فقط بیان):
- جایگزین از نزدیکی نیمرخ ارزش (V) یا راهبرد (S) می‌آید، نه شباهت
  جرقه. جرقه‌ها اولویت هویت‌اند؛ جایگزین افق‌بازکن است، نه اجبار.

{_ANTI_HALLUCINATION}

{_NEUTRALITY}

{_ANTI_CLICHE}

فقط فارسی بنویس. رشتهٔ اصلی را دوباره کامل تحلیل نکن."""

    motives_ctx = _motives_text(profile)
    motives_line = f"زمینهٔ خرده‌انگیزه‌ها (فقط بافت): {motives_ctx}\n\n" if motives_ctx else ""

    user = f"""{motives_line}دادهٔ رشتهٔ اصلی و جایگزین‌ها:
{_result_blocks(top_results, with_alts=True)}

بنویس:
### مسیرهای جایگزین
برای هر جایگزین:
- نام و دلیل نزدیکی (ارزش یا راهبرد، طبق برچسب داده‌شده)
- معنای عملیِ این نزدیکی برای انتخاب رشته
- تأکید کوتاه: مکمل است، نه اجبار به تغییر مسیر

### جمع‌بندی
در ۲-۳ جمله: اولویت با جرقه، پایداری با ارزش، پویایی با راهبرد؛ این
جایگزین‌ها گزینه‌های واقعی‌اند، نه لزوماً بهتر یا بدتر از مسیر اصلی.
حداکثر ۲۸۰ کلمه."""
    return system, user


def _select_prompt(
    profile: dict[str, Any],
    top_results: list[Any],
    journey_type: str,
    mode: str,
) -> tuple[str, str, int, float]:
    branch = _is_branch(journey_type, profile)
    alt = (mode or "main").strip().lower() == "alternatives"
    if branch and not alt:
        system, user = _prompt_branch_main(profile, top_results)
        return system, user, 750, 0.5
    if branch and alt:
        system, user = _prompt_branch_alt(profile, top_results)
        return system, user, 550, 0.5
    if not branch and not alt:
        system, user = _prompt_major_main(profile, top_results)
        return system, user, 850, 0.5
    system, user = _prompt_major_alt(profile, top_results)
    return system, user, 550, 0.5


async def generate_counseling(
    profile: dict[str, Any],
    top_results: list[Any],
    journey_type: str = "majors",
    mode: str = "main",
) -> str:
    mode = (mode or "main").strip().lower()
    if mode not in ("main", "alternatives"):
        mode = "main"

    cleaned_results = [r for r in (top_results or []) if r]
    if not cleaned_results:
        # حالت صفر-نتیجه: هرگز مدل را با دادهٔ خالی صدا نزن — او مجبور
        # می‌شود دربارهٔ گزینه‌هایی که وجود ندارند چیزی بسازد.
        if _is_branch(journey_type, profile):
            return (
                "با همین خرده‌انگیزه‌ها، شاخه‌ای به آستانهٔ لازم نرسیده است. "
                "این لزوماً یعنی گزینه‌ای مناسب نیست؛ می‌تواند یعنی خرده‌انگیزه‌های "
                "بیشتری لازم است تا الگوی دقیق‌تری از تو ساخته شود."
            )
        return (
            "با همین خرده‌انگیزه‌ها، رشته‌ای به آستانهٔ لازم نرسیده است. "
            "این لزوماً یعنی گزینه‌ای مناسب نیست؛ می‌تواند یعنی خرده‌انگیزه‌های "
            "بیشتری لازم است تا الگوی دقیق‌تری از تو ساخته شود."
        )

    account, token, model = _cfg()
    system_prompt, user_content, max_tokens, temperature = _select_prompt(
        profile or {},
        cleaned_results,
        journey_type or "majors",
        mode,
    )

    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=55.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="زمان پاسخ مدل زبانی تمام شد. دوباره تلاش کنید.")
    except Exception:
        raise HTTPException(status_code=502, detail="خطا در ارتباط با مدل زبانی. دوباره تلاش کنید.")

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"خطای سرویس هوش مصنوعی ({response.status_code})")

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception:
        text = (
            data.get("result", {}).get("response")
            or data.get("result", {}).get("output_text")
            or ""
        )
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="پاسخ خالی از مدل زبانی")
    return text
