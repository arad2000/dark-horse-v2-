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

from commercial_api import router as commercial_router
from dark_horse_engine_v2 import DarkHorseEngineV2

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
# Staged commercial router: auth/credits/billing. JSON scoring remains live.
# PostgreSQL runtime cutover remains OFF in migration_control.py.
# Admin HTTP stays on admin_http_api.py and is intentionally not mounted here.
app.include_router(commercial_router)


# ======================= Endpoints =======================
@app.get("/")
async def root():
    return {"name": "Dark Horse API V2.0", "status": "online"}


# ======================= اندپوینت انتخاب رشته دانشگاهی =======================
@app.post("/api/v2/darkhorse/discover")
async def discover_v2(request: DarkHorseDiscoverRequest, req: Request):
    engine = req.app.state.engine
    if engine is None:
        raise HTTPException(503, detail="موتور V2.0 در دسترس نیست")
    try:
        discovery = await asyncio.to_thread(
            engine.discover_individuality,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {}
        )
        recommendations = []
        for item in discovery.get("discovered_majors", []):
            fit = item.get("individuality_fit", {})
            rec = {
                "major_id": item.get("major_id"),
                "major_name_fa": item.get("major_name_fa"),
                "realm_fa": item.get("realm_fa"),
                "fit_score": fit.get("score", 0),
                "fit_level": fit.get("level", ""),
                "market_demand_level": fit.get("market_demand_level", 2),
                "raw_components": fit.get("raw_components", {}),
                "evidence": fit.get("evidence", {}),
                "personalized_description": fit.get("personalized_description", ""),
            }

            if fit.get("archetype"):
                rec["archetype"] = fit["archetype"]

            if fit.get("alternative_paths"):
                rec["alternative_paths"] = fit["alternative_paths"]

            recommendations.append(rec)

        recommendations.sort(key=lambda x: x["fit_score"], reverse=True)
        high = sum(1 for r in recommendations if r["fit_score"] >= 80)
        med = sum(1 for r in recommendations if 60 <= r["fit_score"] < 80)
        low = sum(1 for r in recommendations if r["fit_score"] < 60)

        return {
            "session_id": str(uuid.uuid4()),
            "discovery_result": {
                "total_matches": len(recommendations),
                "high_fit_majors": high,
                "medium_fit_majors": med,
                "low_fit_majors": low,
                "recommendations": recommendations,
                "method": discovery.get("method", {}),
                "summary": discovery.get("summary", {}),
                "next_step": discovery.get("next_step", ""),
            },
        }
    except Exception as e:
        logger.error(f"Error in /api/v2/darkhorse/discover: {e}", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")


# ======================= اندپوینت هدایت تحصیلی (شاخه‌های دبیرستانی) =======================
@app.post("/api/v2/darkhorse/branch-discovery")
async def branch_discovery_v2(request: DarkHorseDiscoverRequest, req: Request):
    engine = req.app.state.branch_engine
    if engine is None:
        raise HTTPException(503, detail="موتور شاخه‌ها V2.0 در دسترس نیست")
    try:
        result = await asyncio.to_thread(
            engine.recommend_school_branch,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {}
        )

        branches = []
        for branch in result.get("recommended_branches", []):
            branch_item = {
                "branch_name_fa": branch.get("branch_name"),
                "fit_score": branch.get("average_score", 0),
                "count": branch.get("count", 0),
                "avg_components": branch.get("avg_components", {}),
                "evidence": branch.get("evidence", {}),
            }

            if branch.get("warning"):
                branch_item["warning"] = branch["warning"]

            if branch.get("alternative_paths"):
                branch_item["alternative_paths"] = branch["alternative_paths"]

            branches.append(branch_item)

        branches.sort(key=lambda x: x["fit_score"], reverse=True)

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


# Defensive invariant: ensure every commercial route is present at the actual
# application router boundary. This is deliberately path-based and idempotent;
# existing routes are preserved and never duplicated.
_COMMERCIAL_ROUTE_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/me",
    "/api/v1/me/quota",
    "/api/v1/me/consume-test",
    "/api/v1/billing/create-payment",
    "/api/v1/billing/callback",
}


def _ensure_commercial_router_mounted() -> None:
    registered_paths = {getattr(route, "path", "") for route in app.router.routes}
    missing_routes = [
        route for route in commercial_router.routes
        if getattr(route, "path", "") in _COMMERCIAL_ROUTE_PATHS
        and getattr(route, "path", "") not in registered_paths
    ]
    for route in missing_routes:
        app.router.routes.append(route)
        registered_paths.add(route.path)


_ensure_commercial_router_mounted()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
