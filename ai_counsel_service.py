"""AI counseling text via Cloudflare Workers AI (Dark Horse philosophy)."""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from fastapi import HTTPException

# مدل قوی‌تر برای فارسی ساخت‌یافته
DEFAULT_MODEL = "@cf/meta/llama-3.1-8b-instruct"


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


SYSTEM_PROMPT = """تو مشاور هدایت تحصیلی در ایران هستی و بر فلسفه کتاب «اسب سیاه» کار می‌کنی.

قوانین سخت:
1) فقط فارسی معیار بنویس. هیچ کلمه انگلیسی/آلمانی/لاتین ننویس.
2) هرگز یک پاراگراف را تکرار نکن.
3) از روی جرقه‌های فنی، شغل مهندسی دانشگاهی نساز مگر کاربر در مسیر رشته دانشگاهی باشد.
4) برای «شاخه دبیرستان» فقط درباره انتخاب رشته متوسطه حرف بزن (ریاضی‌فیزیک، علوم تجربی، علوم انسانی، فنی‌حرفه‌ای، کاردانش و ...).
5) واقعیت‌های ساختگی (راکتور، پایلوت پلنت، Aspen و ...) را به عنوان مسیر شغلی شاخه دبیرستان ننویس.
6) اگر داده ناکافی است، صادقانه کوتاه بگو؛ اغراق نکن.
7) لحن گرم، روشن و قابل اعتماد."""


def _short_motive(m: Any) -> str:
    s = str(m or "").strip()
    if ":" in s:
        s = s.split(":", 1)[0].strip()
    if "：" in s:
        s = s.split("：", 1)[0].strip()
    s = re.sub(r"\s+", " ", s)
    return s[:40]


def _build_user_content(profile: dict[str, Any], top_results: list[Any]) -> str:
    motives_raw = profile.get("micro_motives") or profile.get("sparks") or profile.get("liked_motives") or []
    motives = [_short_motive(m) for m in motives_raw[:10]]
    motives = [m for m in motives if m]
    kind = (profile.get("kind") or "majors").lower()
    is_branch = kind in ("branches", "branch")
    kind_fa = "شاخه‌های دبیرستان (هدایت تحصیلی متوسطه)" if is_branch else "رشته‌های دانشگاهی"

    lines = []
    for i, item in enumerate(top_results[:5], 1):
        if isinstance(item, dict):
            name = item.get("name") or item.get("title") or "نامشخص"
            score = item.get("fit_score", item.get("score"))
            try:
                score_n = float(score)
                if score_n <= 1:
                    score_n *= 100
                score_txt = f"{score_n:.0f}٪"
            except Exception:
                score_txt = "—"
            mm = item.get("micro_motives_matched") or []
            mm_s = "، ".join(_short_motive(x) for x in mm[:5] if _short_motive(x)) or "—"
            lines.append(f"{i}) {name} | همخوانی {score_txt} | نشانه‌ها: {mm_s}")
        else:
            lines.append(f"{i}) {item}")

    results_txt = "\n".join(lines) if lines else "نامشخص"
    motives_txt = "، ".join(motives) if motives else "نامشخص"
    n = min(5, max(1, len(top_results) or 1))

    if is_branch:
        task = f"""برای هر کدام از {n} شاخه بالا، جدا و بدون تکرار بنویس:

### نام شاخه
- چرا با سبک یادگیری و جرقه‌های این دانش‌آموز جور است (۲ جمله، بدون داستان صنعتی)
- در دبیرستان چه مهارت‌ها یا درس‌هایی برایش طبیعی‌تر است (۱–۲ جمله)
- یک مسیر مکمل یا نکته واقع‌بینانه (۱ جمله)

در پایان فقط ۲ جمله جمع‌بندی برای انتخاب شاخه دبیرستان بنویس.
یادآوری: این مرحله متوسطه است، نه انتخاب شغل مهندسی دانشگاه."""
    else:
        task = f"""برای هر کدام از {n} رشته دانشگاهی بالا، جدا و بدون تکرار بنویس:

### نام رشته
- چرا با فردیت و جرقه‌های این فرد هم‌خوان است (۲–۳ جمله واقعی)
- چه نوع فعالیت یا محیط کاری برایش مناسب‌تر است (۱–۲ جمله)
- یک نکته احتیاط یا مسیر مکمل (۱ جمله)

در پایان فقط ۲ جمله جمع‌بندی انگیزشی بنویس."""

    return f"""نوع تحلیل: {kind_fa}
خلاصه جرقه‌های کاربر (کوتاه): {motives_txt}

نتایج به ترتیب:
{results_txt}

{task}

فقط فارسی. بدون تکرار. بدون واژه غیرفارسی."""


async def generate_counseling(profile: dict[str, Any], top_results: list[Any]) -> str:
    account, token, model = _cfg()
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(profile or {}, top_results or [])},
        ],
        "max_tokens": 850,
        "temperature": 0.4,
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
