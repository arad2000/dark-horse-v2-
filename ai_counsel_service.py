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
- همخوانی با جرقه‌ها و سبک یادگیری (۲ جمله)
- درس/مهارت طبیعی در دبیرستان (۱–۲ جمله)
- نکته واقع‌بینانه (۱ جمله)
پایان: ۲ جمله جمع‌بندی برای انتخاب شاخه متوسطه."""
    else:
        task = """شامل این بخش‌ها بنویس:
1) بازتاب فردیت و کهن‌الگو بر اساس جرقه‌ها
2) معنای ترکیب امتیازهای M و S و V
3) چرا این رشته‌ها با فلسفه اسب سیاه برای او مناسب‌اند
4) پیام پایانی کوتاه و واقعی
حداکثر ۳۵۰ کلمه."""

    user = f"""نوع تحلیل: {kind_fa}
جرقه‌های اصلی: {motives_txt}

نتایج برتر:
{results_txt}

{task}
فقط فارسی."""
    return system, user


def _build_alt_prompt(profile: dict[str, Any], top_results: list[Any], journey_type: str) -> tuple[str, str]:
    system = """تو مشاور هدایت تحصیلی همدل هستی (فلسفه اسب سیاه).
وظیفه: معرفی مسیرهای جایگزین به‌صورت امیدوارکننده و واقعی، بدون تضعیف مسیر اصلی.
فقط فارسی. بدون واژه غیرفارسی. تکرار نکن."""

    motives_raw = profile.get("micro_motives") or profile.get("liked_motives") or []
    motives = [_short_motive(m) for m in motives_raw[:12]]
    motives_txt = "، ".join(m for m in motives if m) or "نامشخص"

    alt_lines = []
    for r in (top_results or [])[:4]:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or "—"
        alts = r.get("alternative_paths") or []
        names = []
        for a in alts[:4]:
            if isinstance(a, dict):
                names.append(a.get("branch_name") or a.get("major_name") or a.get("name") or "")
            else:
                names.append(str(a))
        names = [n for n in names if n]
        if names:
            alt_lines.append(f"• برای {name}: {', '.join(names)}")
        else:
            alt_lines.append(f"• برای {name}: مسیر جایگزین ثبت‌نشده")
    alt_txt = "\n".join(alt_lines) if alt_lines else "مسیر جایگزین مشخصی در داده‌ها نیست."

    kind = (journey_type or "majors").lower()
    kind_fa = "شاخه دبیرستان" if kind in ("branches", "branch") else "رشته دانشگاهی"

    user = f"""نوع: {kind_fa}
جرقه‌های کاربر: {motives_txt}

مسیرهای جایگزین سیستم:
{alt_txt}

بنویس:
1) چرا این مسیرها ممکن است با جرقه‌ها جور شوند
2) معرفی به‌عنوان مکمل/جایگزین اختیاری (نه اجباری)
3) افق باز بدون تضعیف مسیر اصلی
4) پایان امیدوارکننده
حداکثر ۲۸۰ کلمه. فقط فارسی."""
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
