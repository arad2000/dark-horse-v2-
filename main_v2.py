"""
Dark Horse API V2.0 — نسخه اصلاح‌شده با پشتیبانی کامل از فیلدهای جدید
"""

import asyncio
import hashlib
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from admin_router import router as admin_router
from commercial_api import router as commercial_router
from dark_horse_engine_v2 import DarkHorseEngineV2
from feedback_api import router as feedback_router, legacy_router as feedback_legacy_router
from ai_counsel_service import generate_counseling
from ai_rate_limit import COUNSEL_RATE_LIMITER

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("darkhorse_api_v2")


_SCORING_FINGERPRINT_FILES = (
    "dark_horse_engine_v2.py",
    "docs/data/micro_motives.json",
    "docs/data/questions_v2.json",
    "majors_database_v2.json",
    "trait_map_v3.json",
    "value_poles_v2.json",
    "school_branches_v2.json",
)


def _runtime_build_fingerprint() -> dict:
    root = os.path.dirname(os.path.abspath(__file__))
    files = {}
    aggregate = hashlib.sha256()
    for relative_path in _SCORING_FINGERPRINT_FILES:
        path = os.path.join(root, relative_path)
        try:
            with open(path, "rb") as fh:
                payload = fh.read()
        except OSError as exc:
            files[relative_path] = {"available": False, "error": str(exc)}
            continue
        digest = hashlib.sha256(payload).hexdigest()
        files[relative_path] = {"available": True, "sha256": digest, "bytes": len(payload)}
        aggregate.update(relative_path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(payload)
    return {
        "algorithm": "sha256",
        "fingerprint": aggregate.hexdigest(),
        "files": files,
        "runtime_commit": os.getenv("GIT_COMMIT") or os.getenv("SOURCE_COMMIT") or None,
        "runtime_version": os.getenv("APP_VERSION") or os.getenv("RELEASE_VERSION") or None,
    }



class DarkHorseDiscoverRequest(BaseModel):
    micro_motives: list = Field(default_factory=list)
    sjt_answers: dict = Field(default_factory=dict)
    conjoint_choices: dict = Field(default_factory=dict)