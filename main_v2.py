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
from ai_counsel_service import generate_counseling
from ai_rate_limit import COUNSEL_RATE_LIMITER

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("darkhorse_api_v2")


class DarkHorseDiscoverRequest(BaseModel):
    micro_motives: list = Field(default_factory=list)
    sjt_answers: dict = Field(default_factory=dict)
    conjoint_choices: dict = Field(default_factory=dict)
    session_id: str | None = Field(default=None, min_length=8, max_length=64)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Dark Horse API V2.0 ...")

    logger.info("✅ COMMERCIAL_ROUTER_IMPORTED=%s", commercial_router is not None)
    logger.info("✅ ADMIN_ROUTER_IMPORTED=%s", admin_router is not None)
    logger.info("✅ FEEDBACK_ROUTER_IMPORTED=%s", feedback_router is not None)

    try:
        import billing_models  # noqa: F401
        import models  # noqa: F401
        from database import init_db, is_configured

        if is_configured():
            init_db()
            logger.info("✅ Operational DB tables ready (init_db).")
        else:
            logger.warning("⚠️ DATABASE_URL not configured; operational DB disabled.")
    except Exception as e:
        logger.error("❌ Operational DB init failed: %s", e, exc_info=True)

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


app = FastAPI(title="Dark Horse API V2.0", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://asbe-siah.ir"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(commercial_router)
app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(feedback_legacy_router)
logger.info("✅ ROUTERS_MOUNTED commercial=/api/v1 admin=/api/v1/admin feedback=/api/v1/feedback legacy=/api/feedback/submit")


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
        "ai_counsel_endpoint": "/api/v2/darkhorse/counsel",
    }


@app.get("/")
async def root():
    return {"name": "Dark Horse API V2.0", "status": "online"}


def _authenticated_user_id(req: Request) -> int | None:
    authorization = req.headers.get("authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    try:
        from auth_service import resolve_session
        from database import SessionLocal

        db = SessionLocal()
        try:
            user = resolve_session(db, token)
            return int(user.id)
        finally:
            db.close()
    except Exception:
        return None


def _persist_discovery_session(
    req: Request,
    request: DarkHorseDiscoverRequest,
    *,
    user_id: int | None = None,
) -> tuple[str, int | None]:
    """Create or reuse one operational session without changing scoring semantics."""
    try:
        from api_persistence_adapter import OperationalPersistenceAdapter, assert_safe_mode
        from database import SessionLocal
        from models import UserSession
        from operational_store import OperationalStore
        from sqlalchemy import select

        assert_safe_mode()
        requested_uuid = request.session_id.strip() if request.session_id else None

        if requested_uuid and user_id is not None:
            db = SessionLocal()
            try:
                row = db.scalar(select(UserSession).where(UserSession.session_uuid == requested_uuid))
                if row is not None:
                    if row.user_id not in (None, user_id):
                        raise HTTPException(status_code=403, detail="session does not belong to this user")
                    if row.user_id is None:
                        row.user_id = user_id
                        db.commit()
                    return requested_uuid, int(row.id)
            finally:
                db.close()

        session_uuid = requested_uuid if (requested_uuid and user_id is not None) else str(uuid.uuid4())
        payload = {
            "micro_motives": request.micro_motives,
            "sjt_answers": request.sjt_answers or {},
            "conjoint_choices": request.conjoint_choices or {},
            "session_uuid": session_uuid,
        }

        if user_id is not None:
            db = SessionLocal()
            try:
                row = UserSession(
                    user_id=user_id,
                    session_uuid=session_uuid,
                    micro_motives=payload["micro_motives"],
                    sjt_answers=payload["sjt_answers"],
                    conjoint_choices=payload["conjoint_choices"],
                    user_ip=(req.client.host if req.client else None),
                    user_agent=req.headers.get("user-agent"),
                    language_preference="fa",
                )
                db.add(row)
                db.commit()
                return session_uuid, int(row.id)
            finally:
                db.close()

        adapter = OperationalPersistenceAdapter(OperationalStore())
        row = adapter.create_session(payload, request_meta={
            "user_ip": req.client.host if req.client else None,
            "user_agent": req.headers.get("user-agent"),
        })
        return session_uuid, int(row.id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Operational session persistence skipped: %s", exc)
        return str(uuid.uuid4()), None


def _persist_major_results(session_id: int | None, recommendations: list[dict]) -> bool:
    if session_id is None:
        return False
    try:
        from api_persistence_adapter import OperationalPersistenceAdapter, assert_safe_mode
        from operational_store import OperationalStore

        assert_safe_mode()
        OperationalPersistenceAdapter(OperationalStore()).persist_discovery(
            session_id,
            {"discovered_majors": recommendations},
        )
        return True
    except Exception as exc:
        logger.warning("Operational major-result persistence skipped: %s", exc)
        return False


def _persist_branch_results(session_id: int | None, branches: list[dict]) -> bool:
    if session_id is None:
        return False
    try:
        from api_persistence_adapter import OperationalPersistenceAdapter, assert_safe_mode
        from operational_store import OperationalStore

        assert_safe_mode()
        OperationalPersistenceAdapter(OperationalStore()).persist_branch_discovery(
            session_id,
            {"recommended_branches": branches},
        )
        return True
    except Exception as exc:
        logger.warning("Operational branch-result persistence skipped: %s", exc)
        return False


@app.post("/api/v2/darkhorse/discover")
async def discover_v2(request: DarkHorseDiscoverRequest, req: Request):
    engine = req.app.state.engine
    if engine is None:
        raise HTTPException(503, detail="موتور امتیازدهی V2.0 در دسترس نیست")
    try:
        user_id = _authenticated_user_id(req)
        session_uuid, persisted_session_id = _persist_discovery_session(req, request, user_id=user_id)

        discovery = await asyncio.to_thread(
            engine.discover_individuality,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {},
        )

        recommendations = []
        for item in discovery.get("discovered_majors", []):
            fit = item.get("individuality_fit", {}) or {}
            rec = {
                "major_id": item.get("major_id"),
                "major_name_fa": item.get("major_name_fa") or item.get("major_name") or "",
                "realm_fa": item.get("realm_fa"),
                "fit_score": fit.get("score", 0),
                "fit_level": fit.get("level", ""),
                "market_demand_level": fit.get("market_demand_level"),
                "raw_components": fit.get("raw_components", {}),
                "evidence": fit.get("evidence", {}),
                "personalized_description": fit.get("personalized_description", ""),
                "individuality_fit": fit,
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
        persisted = _persist_major_results(persisted_session_id, recommendations)

        return {
            "session_id": session_uuid,
            "operational_session_id": persisted_session_id,
            "operational_result_persisted": persisted,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/v2/darkhorse/discover: {e}", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")


@app.post("/api/v2/darkhorse/branch-discovery")
async def branch_discovery_v2(request: DarkHorseDiscoverRequest, req: Request):
    engine = req.app.state.branch_engine
    if engine is None:
        raise HTTPException(503, detail="موتور شاخه‌ها V2.0 در دسترس نیست")
    try:
        user_id = _authenticated_user_id(req)
        session_uuid, persisted_session_id = _persist_discovery_session(req, request, user_id=user_id)
        result = await asyncio.to_thread(
            engine.recommend_school_branch,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {},
        )

        branches = []
        for branch in result.get("recommended_branches", []):
            branch_item = {
                "branch_name_fa": branch.get("branch_name_fa") or branch.get("branch_name") or "",
                "fit_score": branch.get("average_score", 0) or branch.get("fit_score", 0),
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
        persisted = _persist_branch_results(persisted_session_id, branches)

        return {
            "session_id": session_uuid,
            "operational_session_id": persisted_session_id,
            "operational_result_persisted": persisted,
            "branch_discovery_result": {
                "total_matches": len(branches),
                "best_branch": result.get("best_branch"),
                "branches": branches,
                "method": result.get("method", {}),
                "summary": result.get("summary", {}),
                "next_step": result.get("next_step", ""),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/v2/darkhorse/branch-discovery: {e}", exc_info=True)
        raise HTTPException(500, detail="خطای داخلی سرور")


@app.post("/api/v2/darkhorse/counsel")
async def darkhorse_counsel(request: dict, req: Request):
    """Personalized counseling text for discovery results (Dark Horse philosophy)."""
    client_key = req.client.host if req.client else "unknown"
    allowed, retry_after = COUNSEL_RATE_LIMITER.allow(client_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="تعداد درخواست‌های مشاوره هوش مصنوعی بیش از حد مجاز است؛ لطفاً کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(retry_after)},
        )

    profile = request.get("profile") or {}
    top_results = request.get("top_results") or request.get("results") or []
    journey_type = request.get("journey_type") or profile.get("kind") or "majors"
    mode = request.get("mode") or "main"
    if not isinstance(top_results, list):
        top_results = []
    norm = []
    for item in top_results[:5]:
        if isinstance(item, dict):
            row = dict(item)
            if "fit_score" not in row and "score" in row:
                row["fit_score"] = row.get("score")
            if "name" not in row:
                row["name"] = row.get("major_name_fa") or row.get("branch_name_fa") or row.get("title") or "—"
            norm.append(row)
        else:
            norm.append({"name": str(item)})
    if journey_type and "kind" not in profile:
        profile = {**profile, "kind": journey_type}
    text = await generate_counseling(
        profile=profile,
        top_results=norm,
        journey_type=str(journey_type),
        mode=str(mode),
    )
    return {"success": True, "counseling": text, "ok": True, "mode": mode}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v2:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
