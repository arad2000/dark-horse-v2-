"""AI counseling via Cloudflare Workers AI — Dark Horse philosophy.

Modes:
  main         → personalized M/S/V + archetype counseling
  alternatives → alternative paths counseling
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


def _build_main_prompt(profile: dict[str, Any], top_results: list[Any], journey_type: str) -> tuple[str, str]:
    system = """تو مشاور هدایت تحصیلی در ایران هستی و کاملاً بر فلسفه کتاب «اسب سیاه» (تاد رز) کار می‌کنی.

اصول:
- هر فرد مسیر منحصربه‌فرد دارد
- رضایت از همخوانی جرقه (انگیزه)، راهبرد و ارزش می‌آید
- فردیت مهم‌تر از استاندارد کلی است

قوانین:
1) فقط فارسی معیار. بدون واژه انگلیسی/آلمانی/لاتین
2) تکرار نکن
3) برای شاخه دبیرستان، شغل مهندسی دانشگاه نساز
4) لحن گرم، دقیق و واقعی؛ بدون شعار"""

    kind = (journey_type or profile.get("kind") or "majors").lower()
    is_branch = kind in ("branches", "branch")
    kind_fa = "شاخه‌های دبیرستان" if is_branch else "رشته‌های دانشگاهی"

    motives_raw = profile.get("micro_motives") or profile.get("liked_motives") or profile.get("sparks") or []
    motives = [_short_motive(m) for m in motives_raw[:12]]
    motives = [m for m in motives if m]
    motives_txt = "، ".join(motives) if motives else "نامشخص"

    blocks = []
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
        arch = r.get("archetype") or {}
        if isinstance(arch, str):
            arch = {"archetype": arch}
        arch_name = arch.get("archetype") or "—"
        identity = arch.get("identity_sentence") or "—"
        fulfill = r.get("fulfillment_source") or arch.get("fulfillment_source") or "—"
        blocks.append(
            f"{i}. {name} (همخوانی: {score}٪)\n"
            f"   - انگیزه M: {m}٪ | راهبرد S: {s}٪ | ارزش V: {v}٪\n"
            f"   - کهن‌الگو: {arch_name}\n"
            f"   - جمله هویتی: {identity}\n"
            f"   - منبع رضایت: {fulfill}"
        )
    results_txt = "\n".join(blocks) if blocks else "نامشخص"

    if is_branch:
        task = """برای هر شاخه جدا بنویس (بدون تکرار):
### نام شاخه
- همخوانی با جرقه‌ها (۲ جمله)
- اشاره کوتاه به ترکیب انگیزه/راهبرد/ارزش اگر عدد دارند (۱ جمله)
- درس/مهارت طبیعی در دبیرستان (۱–۲ جمله)
- نکته واقع‌بینانه (۱ جمله)
پایان: ۲ جمله جمع‌بندی برای انتخاب شاخه متوسطه."""
    else:
        task = """شامل این بخش‌ها بنویس:
1) بازتاب فردیت و کهن‌الگو (اگر کهن‌الگو «—» بود، از روی جرقه‌ها بگو)
2) صریحاً بگو ترکیب M و S و V چه معنایی دارد (از اعداد داده‌شده استفاده کن)
3) چرا این رشته‌ها با فلسفه اسب سیاه برای او مناسب‌اند
4) پیام پایانی کوتاه و واقعی
حداکثر ۳۵۰ کلمه. اگر برای شاخه دبیرستان هستی از ساختار شاخه‌ای بالا استفاده کن نه این لیست."""

    user = f"""نوع تحلیل: {kind_fa}
جرقه‌های اصلی: {motives_txt}

نتایج برتر:
{results_txt}

{task}
فقط فارسی."""
    return system, user


def _build_alt_prompt(profile: dict[str, Any], top_results: list[Any], journey_type: str) -> tuple[str, str]:
    """پرامپت مسیرهای جایگزین — بر اساس نسخه ارزیاب + فاصله V/S موتور."""
    system = """تو یک مشاور هدایت تحصیلی هستی که کاملاً بر اساس فلسفه کتاب «اسب سیاه» (تاد رز و اُگی اُگاس) کار می‌کنی.

قوانین قطعی فلسفه اسب سیاه که باید رعایت کنی:
1. خرده‌انگیزه‌ها (جرقه‌ها) پایدارترین و مهم‌ترین لایه هویت فرد هستند.
2. ارزش‌های بنیادی نیز نسبتاً پایدارند.
3. راهبردها پویا هستند و با آزمون و خطا قابل تقویت‌اند.
4. مسیر جایگزین عمدتاً به‌خاطر هم‌راستایی «ارزش‌ها» یا «راهبردها» پیشنهاد می‌شود، نه به‌خاطر شباهت جرقه‌ها.
5. جرقه‌ها اولویت اصلی باقی می‌مانند؛ مسیر جایگزین نباید جرقه‌ها را بی‌اهمیت نشان دهد.

وظیفه تو:
- توضیح بدهی چرا این مسیرهای جایگزین بر اساس ارزش‌ها یا راهبردهای فرد معنا دارند
- آن‌ها را به‌عنوان گزینه مکمل یا جایگزین واقعی معرفی کنی
- بدون تضعیف مسیر اصلی و بدون کلیشه صحبت کنی

فقط فارسی. بدون واژه انگلیسی/آلمانی. تکرار نکن."""

    kind = (journey_type or "majors").lower()
    kind_fa = "شاخه دبیرستان" if kind in ("branches", "branch") else "رشته دانشگاهی"

    blocks = []
    for r in (top_results or [])[:4]:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or "نامشخص"
        raw = r.get("raw_components") or r.get("avg_components") or {}
        m = _pct(raw.get("m_score", r.get("m_score")))
        s = _pct(raw.get("s_score", r.get("s_score")))
        v = _pct(raw.get("v_score", r.get("v_score")))

        archetype = r.get("archetype") or {}
        if isinstance(archetype, str):
            archetype = {"archetype": archetype}
        dominant_values = archetype.get("dominant_values") or []
        dominant_traits = archetype.get("dominant_traits") or []

        alts = r.get("alternative_paths") or []
        alt_lines = []
        for a in alts[:5]:
            if isinstance(a, dict):
                an = a.get("branch_name") or a.get("major_name") or a.get("name") or a.get("title") or ""
                an = (an or "").strip()
                if not an:
                    continue
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
                        why = "نزدیک‌تر از نظر ارزش‌ها (V)"
                    elif sd < vd:
                        why = "نزدیک‌تر از نظر راهبردها (S)"
                    else:
                        why = "نزدیک از نظر ترکیب ارزش و راهبرد"
                    alt_lines.append(f"{an} ({why}; فاصله‌V={vd:.3f}, فاصله‌S={sd:.3f})")
                else:
                    alt_lines.append(an)
            else:
                s_a = str(a).strip()
                if s_a:
                    alt_lines.append(s_a)

        if not alt_lines:
            continue

        val_txt = "، ".join(str(x) for x in dominant_values[:6]) if dominant_values else "نامشخص"
        trait_txt = "، ".join(str(x) for x in dominant_traits[:6]) if dominant_traits else "نامشخص"
        blocks.append(
            f"مسیر اصلی: {name}\n"
            f"- امتیاز انگیزه (M): {m}%\n"
            f"- امتیاز راهبرد (S): {s}%\n"
            f"- امتیاز ارزش (V): {v}%\n"
            f"- ارزش‌های غالب مرتبط: {val_txt}\n"
            f"- راهبردهای غالب مرتبط: {trait_txt}\n"
            f"- مسیرهای جایگزین ثبت‌شده: {', '.join(alt_lines)}"
        )

    results_block = "\n\n".join(blocks) if blocks else "مسیر جایگزین مشخصی در داده‌ها نیست."

    motives_raw = profile.get("liked_motives") or profile.get("micro_motives") or profile.get("likedCodes") or []
    motives = [_short_motive(m) for m in motives_raw[:12]]
    motives_text = "، ".join(m for m in motives if m) or "مشخص نشده"

    user = f"""نوع تحلیل: {kind_fa}

جرقه‌های اصلی کاربر (فقط برای زمینه؛ محور توضیح جایگزین‌ها نباشند):
{motives_text}

داده‌های مسیرهای اصلی و جایگزین:
{results_block}

حالا یک تحلیل مشاوره‌ای دقیق برای «مسیرهای جایگزین» بنویس که:

1. صریحاً بگوید این جایگزین‌ها عمدتاً به‌خاطر هم‌راستایی ارزش‌ها (V) یا راهبردها (S) مطرح شده‌اند
2. توضیح دهد کدام‌یک بیشتر به ارزش‌های بنیادی وصل است و کدام‌یک به راهبردهای فرد (از دلیل فاصله‌ها استفاده کن)
3. یادآوری کند که جرقه‌ها همچنان اولویت اصلی‌اند و این مسیرها مکمل/جایگزین هستند نه جایگزینِ کور
4. راهبردها را پویا بداند (قابل تقویت با آزمون و خطا) و ارزش‌ها را پایدارتر
5. لحن واقعی، شخصی و امیدوارکننده داشته باشد؛ بدون شعار

حداکثر ۲۸۰ کلمه. فقط فارسی روان و مشاوره‌ای."""
    return system, user


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

    if mode == "alternatives":
        system_prompt, user_content = _build_alt_prompt(profile or {}, top_results or [], journey_type)
        max_tokens = 500
        temperature = 0.65
    else:
        system_prompt, user_content = _build_main_prompt(profile or {}, top_results or [], journey_type)
        max_tokens = 700
        temperature = 0.55

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
