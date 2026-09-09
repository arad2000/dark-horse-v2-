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


SYSTEM_PROMPT = """تو یک مشاور هدایت تحصیلی همدل، گرم و حرفه‌ای هستی که بر اساس فلسفه کتاب «اسب سیاه» (تاد رز و اُگی اُگاس) کار می‌کنی.
هدف تو کمک به دانش‌آموز برای پیدا کردن مسیر منحصربه‌فرد خودش است، نه فقط پیشنهاد یک رشته.
با زبان فارسی ساده، صمیمی و امیدوارکننده حرف بزن. از کلیشه و لحن خشک خودداری کن.
قضاوت اخلاقی یا برچسب‌زدن نکن. وعده قطعی موفقیت نده. مختصر و مفید بنویس."""


def _build_user_content(profile: dict[str, Any], top_results: list[Any]) -> str:
    motives = profile.get("micro_motives") or profile.get("sparks") or profile.get("liked_motives") or []
    kind = profile.get("kind") or "majors"
    kind_fa = "شاخه‌های دبیرستان" if kind in ("branches", "branch") else "رشته‌های دانشگاهی"

    lines = []
    for i, item in enumerate(top_results[:5], 1):
        if isinstance(item, dict):
            name = item.get("name") or item.get("title") or item.get("code") or "—"
            score = item.get("fit_score", item.get("score"))
            extra = f" (امتیاز: {score})" if score is not None else ""
            lines.append(f"{i}. {name}{extra}")
        else:
            lines.append(f"{i}. {item}")

    results_txt = "\n".join(lines) if lines else "نامشخص"
    motives_txt = "، ".join(str(m) for m in motives[:12]) if motives else "نامشخص"

    return f"""اطلاعات کاربر و نتایج تحلیل اسب سیاه:

نوع تحلیل: {kind_fa}
جرقه‌ها / خرده‌انگیزه‌های برجسته: {motives_txt}
نتایج برتر:
{results_txt}

یک توضیح مشاوره‌ای شخصی‌سازی‌شده به فارسی بنویس که:
1) فردیت و نقاط قوت کاربر را برجسته کند
2) بگوید چرا این گزینه‌ها با او هم‌خوانی دارند
3) مسیرهای جایگزین را امیدوارکننده معرفی کند
4) او را تشویق کند مسیر خودش را بسازد

حداکثر ۳۲۰ کلمه. فقط متن مشاوره را برگردان، بدون عنوان اضافه."""


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
        "max_tokens": 700,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
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
