"""AI counseling via Cloudflare Workers AI — Dark Horse philosophy.

Four prompt modes:
  branches + main         → تحلیل شاخه کشف‌شده دبیرستان
  branches + alternatives → تحلیل مسیرهای جایگزین شاخه
  majors   + main         → تحلیل رشته‌های دانشگاهی کشف‌شده
  majors   + alternatives → تحلیل مسیرهای جایگزین رشته
All grounded in M (خرده‌انگیزه/جرقه), S (راهبرد), V (ارزش).
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


def _short_motive(m: Any) -> str:
    s = str(m or "").strip()
    if ":" in s:
        s = s.split(":", 1)[0].strip()
    if "：" in s:
        s = s.split("：", 1)[0].strip()
    s = re.sub(r"\s+", " ", s)
    return s[:48]


def _pct(val: Any) -> str:
    try:
        n = float(val)
        if n <= 1:
            n *= 100
        return f"{n:.0f}"
    except Exception:
        return "—"


def _is_branch(journey_type: str, profile: dict[str, Any] | None = None) -> bool:
    kind = (journey_type or (profile or {}).get("kind") or "majors").lower()
    return kind in ("branches", "branch")


def _motives_text(profile: dict[str, Any]) -> str:
    raw = (
        profile.get("micro_motives")
        or profile.get("liked_motives")
        or profile.get("likedCodes")
        or profile.get("sparks")
        or []
    )
    items = [_short_motive(m) for m in raw[:15]]
    items = [m for m in items if m]
    return "، ".join(items) if items else "نامشخص"


def _arch_bits(r: dict[str, Any]) -> tuple[str, str, str, str]:
    arch = r.get("archetype") or {}
    if isinstance(arch, str):
        arch = {"archetype": arch}
    name = arch.get("archetype") or "—"
    identity = arch.get("identity_sentence") or "—"
    vals = arch.get("dominant_values") or []
    traits = arch.get("dominant_traits") or []
    val_txt = "، ".join(str(x) for x in vals[:6]) if vals else "—"
    trait_txt = "، ".join(str(x) for x in traits[:6]) if traits else "—"
    return str(name), str(identity), val_txt, trait_txt


def _alt_line(a: Any) -> str:
    if not isinstance(a, dict):
        return str(a).strip()
    name = (
        a.get("branch_name")
        or a.get("major_name")
        or a.get("name")
        or a.get("title")
        or ""
    ).strip()
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
        if vd < sd:
            why = "نزدیک‌تر از نظر ارزش (V)"
        elif sd < vd:
            why = "نزدیک‌تر از نظر راهبرد (S)"
        else:
            why = "نزدیک از نظر ترکیب ارزش و راهبرد"
        return f"{name} — {why} (فاصله‌V={vd:.3f}، فاصله‌S={sd:.3f})"
    return name


def _result_blocks(top_results: list[Any], *, with_alts: bool) -> str:
    blocks: list[str] = []
    for i, r in enumerate((top_results or [])[:4], 1):
        if not isinstance(r, dict):
            blocks.append(f"{i}. {r}")
            continue
        name = r.get("name") or r.get("title") or "نامشخص"
        score = _pct(r.get("fit_score", r.get("score")))
        raw = r.get("raw_components") or r.get("avg_components") or {}
        m = _pct(raw.get("m_score", r.get("m_score")))
        s = _pct(raw.get("s_score", r.get("s_score")))
        v = _pct(raw.get("v_score", r.get("v_score")))
        arch_name, identity, val_txt, trait_txt = _arch_bits(r)
        fulfill = r.get("fulfillment_source") or "—"
        line = (
            f"{i}. {name} (همخوانی کلی: {score}٪)\n"
            f"   - خرده‌انگیزه / جرقه (M): {m}٪\n"
            f"   - راهبرد (S): {s}٪\n"
            f"   - ارزش (V): {v}٪\n"
            f"   - کهن‌الگو: {arch_name}\n"
            f"   - جمله هویتی: {identity}\n"
            f"   - ارزش‌های غالب: {val_txt}\n"
            f"   - راهبردهای غالب: {trait_txt}\n"
            f"   - منبع رضایت: {fulfill}"
        )
        if with_alts:
            alts = [_alt_line(a) for a in (r.get("alternative_paths") or [])[:5]]
            alts = [a for a in alts if a]
            line += "\n   - مسیرهای جایگزین: " + ("؛ ".join(alts) if alts else "ثبت نشده")
        blocks.append(line)
    return "\n".join(blocks) if blocks else "نامشخص"


# ── ۱) شاخه دبیرستان — تحلیل اصلی ──────────────────────────────────────────
def _prompt_branch_main(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = """تو مشاور هدایت تحصیلی متوسطه در ایران هستی و بر فلسفه کتاب «اسب سیاه» کار می‌کنی.

موضوع: تحلیل شاخه(های) دبیرستان کشف‌شده برای دانش‌آموز.

سه شاخص اصلی که باید همیشه روی آن‌ها بنا کنی:
1) خرده‌انگیزه‌ها / جرقه‌ها (M) — پایدارترین لایه هویت
2) راهبردها (S) — سبک فکر و یادگیری؛ پویا و قابل تقویت
3) ارزش‌ها (V) — معنای رضایت بلندمدت؛ نسبتاً پایدار

قوانین:
- فقط فارسی
- این مرحله انتخاب شاخه متوسطه است، نه شغل مهندسی دانشگاه
- برای هر شاخه جدا بنویس؛ تکرار نکن
- از اعداد M/S/V داده‌شده استفاده کن"""

    user = f"""جرقه‌های دانش‌آموز:
{_motives_text(profile)}

نتایج شاخه:
{_result_blocks(top_results, with_alts=False)}

برای هر شاخه با این ساختار بنویس:
### نام شاخه
- جرقه (M): چرا با خرده‌انگیزه‌های او جور است
- راهبرد (S): چه سبک یادگیری‌ای در دبیرستان برایش طبیعی‌تر است
- ارزش (V): چه نوع معنا/رضایتی برایش مهم است
- نکته واقع‌بینانه کوتاه

پایان: ۲ جمله جمع‌بندی برای انتخاب شاخه متوسطه.
حداکثر ۳۲۰ کلمه. فقط فارسی."""
    return system, user


# ── ۲) شاخه دبیرستان — مسیرهای جایگزین ────────────────────────────────────
def _prompt_branch_alt(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = """تو مشاور هدایت تحصیلی متوسطه هستی (فلسفه اسب سیاه).

موضوع: فقط مسیرهای جایگزین شاخه دبیرستان.

منطق سیستم:
- جایگزین عمدتاً به‌خاطر نزدیکی ارزش (V) یا راهبرد (S) پیشنهاد می‌شود
- نه به‌خاطر شباهت جرقه
- جرقه‌ها همچنان اولویت اصلی هویت‌اند؛ جایگزین مکمل است نه جایگزین کور
- راهبرد پویا است؛ ارزش پایدارتر است

قوانین:
- فقط فارسی
- مسیر اصلی را مثل مشاوره اصلی دوباره شرح نده
- اگر فاصله V/S در داده هست، صریحاً بگو نزدیک‌تر از نظر ارزش است یا راهبرد
- محور توضیح را جرقه نکن"""

    user = f"""جرقه‌ها (فقط زمینه؛ محور جایگزین نباشند):
{_motives_text(profile)}

داده مسیر اصلی و جایگزین‌ها:
{_result_blocks(top_results, with_alts=True)}

بنویس:
### مسیرهای جایگزین
برای هر جایگزین:
- نام
- از نظر ارزش نزدیک‌تر است یا راهبرد (بر اساس داده)
- این نزدیکی برای انتخاب شاخه چه معنایی دارد
- تأکید: مکمل است، نه اجبار

### جمع‌بندی
جرقه‌ها اولویت‌اند؛ ارزش پایدارتر و راهبرد قابل تقویت است؛ مسیر اصلی تضعیف نشود.
حداکثر ۲۸۰ کلمه. فقط فارسی."""
    return system, user


# ── ۳) رشته دانشگاهی — تحلیل اصلی ─────────────────────────────────────────
def _prompt_major_main(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = """تو مشاور هدایت تحصیلی و انتخاب رشته دانشگاهی هستی و بر فلسفه کتاب «اسب سیاه» کار می‌کنی.

موضوع: تحلیل رشته‌های دانشگاهی کشف‌شده.

سه شاخص اصلی:
1) خرده‌انگیزه‌ها / جرقه‌ها (M) — پایدارترین لایه
2) راهبردها (S) — سبک کار و یادگیری؛ قابل رشد
3) ارزش‌ها (V) — منبع رضایت عمیق؛ نسبتاً پایدار

قوانین:
- فقط فارسی
- برای هر رشته جدا و بدون تکرار
- از اعداد M/S/V و کهن‌الگو استفاده کن
- بدون شعار و کلیشه"""

    user = f"""جرقه‌های فرد:
{_motives_text(profile)}

نتایج رشته:
{_result_blocks(top_results, with_alts=False)}

برای هر رشته بنویس:
### نام رشته
- جرقه (M): همخوانی با خرده‌انگیزه‌ها
- راهبرد (S): چه سبک کار/یادگیری‌ای می‌طلبد و با او چه نسبتی دارد
- ارزش (V): چه معنایی برای رضایت بلندمدتش دارد
- یک نکته احتیاط یا مسیر مکمل کوتاه

پایان: ۲ جمله جمع‌بندی واقعی.
حداکثر ۳۵۰ کلمه. فقط فارسی."""
    return system, user


# ── ۴) رشته دانشگاهی — مسیرهای جایگزین ────────────────────────────────────
def _prompt_major_alt(profile: dict[str, Any], top_results: list[Any]) -> tuple[str, str]:
    system = """تو مشاور انتخاب رشته دانشگاهی هستی (فلسفه اسب سیاه).

موضوع: فقط مسیرهای جایگزین رشته.

منطق سیستم:
- جایگزین عمدتاً از نزدیکی نیمرخ ارزش (V) و راهبرد (S) می‌آید
- نه از شباهت جرقه
- جرقه‌ها اولویت هویت‌اند؛ جایگزین مکمل/افق‌بازکن است
- راهبرد قابل تقویت است؛ ارزش پایدارتر است

قوانین:
- فقط فارسی
- مسیر اصلی را دوباره مثل تحلیل اصلی تکرار نکن
- از فاصله‌های V/S داده برای تفکیک دلیل نزدیکی استفاده کن"""

    user = f"""جرقه‌ها (فقط زمینه):
{_motives_text(profile)}

داده رشته اصلی و جایگزین‌ها:
{_result_blocks(top_results, with_alts=True)}

بنویس:
### مسیرهای جایگزین
برای هر جایگزین:
- نام
- دلیل نزدیکی: ارزش یا راهبرد
- معنای عملی برای انتخاب رشته
- مکمل بودن، نه اجبار

### جمع‌بندی
اولویت جرقه، پایداری ارزش، پویایی راهبرد؛ بدون تضعیف مسیر اصلی.
حداکثر ۲۸۰ کلمه. فقط فارسی."""
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
        return system, user, 700, 0.55
    if branch and alt:
        system, user = _prompt_branch_alt(profile, top_results)
        return system, user, 500, 0.60
    if not branch and not alt:
        system, user = _prompt_major_main(profile, top_results)
        return system, user, 750, 0.55
    system, user = _prompt_major_alt(profile, top_results)
    return system, user, 500, 0.60


async def generate_counseling(
    profile: dict[str, Any],
    top_results: list[Any],
    journey_type: str = "majors",
    mode: str = "main",
) -> str:
    account, token, model = _cfg()
    mode = (mode or "main").strip().lower()
    if mode not in ("main", "alternatives"):
        mode = "main"

    system_prompt, user_content, max_tokens, temperature = _select_prompt(
        profile or {},
        top_results or [],
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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"خطا در ارتباط با مدل زبانی: {e}")

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
