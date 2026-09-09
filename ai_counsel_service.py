"""AI counseling text via Cloudflare Workers AI (Dark Horse philosophy)."""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

DEFAULT_MODEL = "@cf/meta/llama-3.2-3b-instruct"


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


SYSTEM_PROMPT = """تو مشاور هدایت تحصیلی فارسی‌زبان هستی؛ بر اساس فلسفه کتاب «اسب سیاه» (تاد رز).

قوانین اجباری:
1) فقط و فقط به زبان فارسی بنویس. هیچ واژه انگلیسی، آلمانی یا لاتین ننویس.
2) اگر نام رشته به‌ناچار خارجی است، همان نام رایج فارسی‌اش را بنویس (مثلاً مهندسی انرژی‌های تجدیدپذیر).
3) لحن گرم، ساده، امیدوارکننده و بدون کلیشه خشک.
4) برای هر رشته/شاخه یک بخش جدا با عنوان واضح بنویس.
5) تکرار بی‌معنی نکن. وعده قطعی موفقیت نده.
6) خروجی را ساخت‌یافته بنویس نه یک پاراگراف درهم."""


def _build_user_content(profile: dict[str, Any], top_results: list[Any]) -> str:
    motives = profile.get("micro_motives") or profile.get("sparks") or profile.get("liked_motives") or []
    kind = profile.get("kind") or "majors"
    kind_fa = "شاخه دبیرستان" if kind in ("branches", "branch") else "رشته دانشگاهی"

    lines = []
    for i, item in enumerate(top_results[:5], 1):
        if isinstance(item, dict):
            name = item.get("name") or item.get("title") or item.get("code") or "نامشخص"
            score = item.get("fit_score", item.get("score"))
            mm = item.get("micro_motives_matched") or []
            mm_txt = "، ".join(str(x) for x in mm[:6]) if mm else "—"
            score_txt = f"{score}" if score is not None else "—"
            lines.append(f"{i}) نام: {name} | همخوانی: {score_txt} | جرقه‌های مرتبط: {mm_txt}")
        else:
            lines.append(f"{i}) {item}")

    results_txt = "\n".join(lines) if lines else "نامشخص"
    motives_txt = "، ".join(str(m) for m in motives[:12]) if motives else "نامشخص"
    n = min(5, max(1, len(top_results) or 1))

    return f"""داده‌های تحلیل اسب سیاه:

نوع نتیجه: {kind_fa}
جرقه‌ها / خرده‌انگیزه‌های کاربر: {motives_txt}

فهرست نتایج (به ترتیب اولویت):
{results_txt}

دقیقاً این ساختار را رعایت کن:

برای هر مورد از {n} نتیجه بالا، جداگانه بنویس:

### [نام فارسی رشته یا شاخه]
- چرا با فردیت این کاربر هم‌خوان است (۲ تا ۳ جمله)
- چه مسیر یا فعالیتی برایش طبیعی‌تر است (۱ تا ۲ جمله)
- یک نکته احتیاط یا مسیر مکمل کوتاه (۱ جمله)

بعد از همه موارد، فقط ۲ جمله جمع‌بندی انگیزشی بنویس.

یادآوری: تمام متن فقط فارسی. بدون کلمه غیرفارسی."""


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
        "max_tokens": 900,
        "temperature": 0.55,
    }

    try:
        async with httpx.AsyncClient(timeout=50.0) as client:
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
