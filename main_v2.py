"""
Dark Horse API V2.0 — نسخه اصلاح‌شده با پشتیبانی کامل از فیلدهای جدید
"""

import asyncio
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("darkhorse_api_v2")


# ======================= مدل‌های Pydantic =======================
class DarkHorseDiscoverRequest(BaseModel):
    micro_motives: list = Field(default_factory=list)
    sjt_answers: dict = Field(default_factory=dict)
    conjoint_choices: dict = Field(default_factory=dict)


# ======================= Lifespan =======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Dark Horse API V2.0 ...")

    # Explicit runtime fingerprint for Liara deployment diagnostics.
    logger.info("✅ COMMERCIAL_ROUTER_IMPORTED=%s", commercial_router is not None)
    logger.info("✅ ADMIN_ROUTER_IMPORTED=%s", admin_router is not None)
    logger.info("✅ FEEDBACK_ROUTER_IMPORTED=%s", feedback_router is not None)

    # Operational tables for auth/credits/billing/feedback (not psychometric JSON data).
    try:
        import billing_models  # noqa: F401 — register ORM tables on Base.metadata
        import models  # noqa: F401 — user_sessions / user_feedback tables
        from database import init_db, is_configured

        if is_configured():
            init_db()
            logger.info("✅ Operational DB tables ready (init_db).")
        else:
            logger.warning("⚠️ DATABASE_URL not configured; operational DB disabled.")
    except Exception as e:
        logger.error("❌ Operational DB init failed: %s", e, exc_info=True)

    # موتور اصلی (برای رشته‌های دانشگاهی)
    try:
        app.state.engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json"
        )
        logger.info("✅ DarkHorseEngineV2 آماده است.")
    except Exception as e:
        logger.error(f"❌ DarkHorseEngineV2 init failed: {e}")
        app.state.engine = None

    # موتور شاخه‌ها (برای هدایت تحصیلی)
    try:
        app.state.branch_engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json"
        )
        logger.info("✅ BranchEngineV2 آماده است.")
    except Exception as e:
        logger.error(f"❌ BranchEngineV2 init failed: {e}")
        app.state.branch_engine = None

    yield
    logger.info("🛑 Shutting down V2.0 ...")


# ======================= FastAPI App =======================
app = FastAPI(title="Dark Horse API V2.0", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(commercial_router)
app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(feedback_legacy_router)
logger.info("✅ ROUTERS_MOUNTED commercial=/api/v1 admin=/api/v1/admin feedback=/api/v1/feedback legacy=/api/feedback/submit")


# ======================= Runtime Diagnostics =======================
@app.get("/__runtime_fingerprint")
async def runtime_fingerprint():
    return {
        "service": "dark-horse-v2",
        "commercial_router_mounted": True,
        "admin_router_mounted": True,
        "feedback_router_mounted": True,
        "commercial_prefix": "/api/v1",
        "admin_prefix": "/api/v1/admin",
        "feedback_prefix": "/api/v1/feedback",
        "legacy_feedback_submit": "/api/feedback/submit",
        "commit_hint": "deploy/liara-commercial-sandbox",
    }


# ======================= Endpoints =======================
@app.get("/")
async def root():
    return {"name": "Dark Horse API V2.0", "status": "online"}


@app.post("/api/v2/darkhorse/discover")
async def discover(req: DarkHorseDiscoverRequest, request: Request):
    engine = request.app.state.engine
    if engine is None:
        raise HTTPException(503, detail="موتور امتیازدهی آماده نیست")
    try:
        result = engine.discover(
            micro_motives=req.micro_motives,
            sjt_answers=req.sjt_answers,
            conjoint_choices=req.conjoint_choices,
        )
        recommendations = result.get("recommendations") or result.get("majors") or []
        if isinstance(recommendations, list):
            recommendations = sorted(
                recommendations,
                key=lambda x: x.get("fit_score") or (x.get("individuality_fit") or {}).get("score") or 0,
                reverse=True,
            )
        return {
            "session_id": str(uuid.uuid4()),
            "discovery_result": {
                "total_matches": len(recommendations) if isinstance(recommendations, list) else 0,
                "recommendations": recommendations,
                "method": result.get("method", {}),
                "summary": result.get("summary", {}),
                "next_step": result.get("next_step", ""),
            },
        }
    except Exception as e:
        logger.error(f"Error in /api/v2/darkhorse/discover: {e}", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")


@app.post("/api/v2/darkhorse/branch-discovery")
async def branch_discovery(req: DarkHorseDiscoverRequest, request: Request):
    engine = request.app.state.branch_engine or request.app.state.engine
    if engine is None:
        raise HTTPException(503, detail="موتور امتیازدهی آماده نیست")
    try:
        result = engine.discover_branches(
            micro_motives=req.micro_motives,
            sjt_answers=req.sjt_answers,
            conjoint_choices=req.conjoint_choices,
        ) if hasattr(engine, "discover_branches") else engine.discover(
            micro_motives=req.micro_motives,
            sjt_answers=req.sjt_answers,
            conjoint_choices=req.conjoint_choices,
        )
        branches = result.get("branches") or result.get("recommendations") or []
        if isinstance(branches, list):
            branches = sorted(
                branches,
                key=lambda x: x.get("fit_score") or (x.get("individuality_fit") or {}).get("score") or 0,
                reverse=True,
            )

        return {
            "session_id": str(uuid.uuid4()),
            "branch_discovery_result": {
                "total_matches": len(branches),
                "best_branch": result.get("best_branch"),
                "branches": branches,
                "method": result.get("method", {}),
                "summary": result.get("summary", {}),
                "next_step": result.get("next_step", ""),
            },
        }
    except Exception as e:
        logger.error(f"Error in /api/v2/darkhorse/branch-discovery: {e}", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
