"""
Dark Horse API V2.0 — نسخه موازی برای تست سؤالات و وزن‌های جدید
"""

import json
import logging
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dark_horse_engine_v2 import DarkHorseEngineV2
import asyncio

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
    try:
        app.state.engine = DarkHorseEngineV2(
            motives_path="micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v2.json",
            value_poles_path="value_poles_v2.json"
        )
        logger.info("✅ DarkHorseEngineV2 آماده است.")
    except Exception as e:
        logger.error(f"❌ DarkHorseEngineV2 init failed: {e}")
        app.state.engine = None

    try:
        app.state.branch_engine = DarkHorseEngineV2(
            motives_path="micro_motives.json",
            majors_path="school_branches_v2.json",
            trait_map_path="trait_map_v2.json",
            value_poles_path="value_poles_v2.json"
        )
        logger.info("✅ BranchEngineV2 آماده است.")
    except Exception as e:
        logger.error(f"❌ BranchEngineV2 init failed: {e}")
        app.state.branch_engine = None

    yield
    logger.info("🛑 Shutting down V2.0 ...")

# ======================= FastAPI App =======================
app = FastAPI(title="Dark Horse API V2.0", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

# ======================= Endpoints =======================
@app.get("/")
async def root():
    return {"name": "Dark Horse API V2.0", "status": "online"}

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
            recommendations.append({
                "major_id": item.get("major_id"),
                "major_name_fa": item.get("major_name_fa"),
                "realm_fa": item.get("realm_fa"),
                "fit_score": fit.get("score", 0),
                "fit_level": fit.get("level", ""),
                "market_demand_level": fit.get("market_demand_level", 2),
                "raw_components": fit.get("raw_components", {}),
                "evidence": fit.get("evidence", {}),
                "personalized_description": fit.get("personalized_description", ""),
            })
        recommendations.sort(key=lambda x: x["fit_score"], reverse=True)
        high = sum(1 for r in recommendations if r["fit_score"] >= 80)
        med = sum(1 for r in recommendations if 60 <= r["fit_score"] < 80)
        return {
            "session_id": str(uuid.uuid4()),
            "discovery_result": {
                "total_matches": len(recommendations),
                "high_fit_majors": high, "medium_fit_majors": med,
                "recommendations": recommendations,
                "method": discovery.get("method", {}),
                "summary": discovery.get("summary", {}),
                "next_step": discovery.get("next_step", ""),
            },
        }
    except Exception:
        logger.error("Error in /api/v2/darkhorse/discover", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")

@app.post("/api/v2/darkhorse/branch-discovery")
async def branch_discovery_v2(request: DarkHorseDiscoverRequest, req: Request):
    engine = req.app.state.branch_engine
    if engine is None:
        raise HTTPException(503, detail="موتور شاخه‌ها V2.0 در دسترس نیست")
    try:
        discovery = await asyncio.to_thread(
            engine.discover_individuality,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {}
        )
        branches = []
        for item in discovery.get("discovered_majors", []):
            fit = item.get("individuality_fit", {})
            branches.append({
                "branch_id": item.get("major_id"),
                "branch_name_fa": item.get("major_name_fa"),
                "group": item.get("realm_fa"),
                "fit_score": fit.get("score", 0),
                "fit_level": fit.get("level", ""),
                "raw_components": fit.get("raw_components", {}),
                "evidence": fit.get("evidence", {}),
                "personalized_description": fit.get("personalized_description", ""),
            })
        branches.sort(key=lambda x: x["fit_score"], reverse=True)
        return {
            "session_id": str(uuid.uuid4()),
            "branch_discovery_result": {
                "total_matches": len(branches),
                "branches": branches,
                "method": discovery.get("method", {}),
                "summary": discovery.get("summary", {}),
            },
        }
    except Exception:
        logger.error("Error in /api/v2/darkhorse/branch-discovery", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
