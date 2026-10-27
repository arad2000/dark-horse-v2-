"""
Dark Horse API V2.0 — نسخه اصلاح‌شده با پشتیبانی کامل از فیلدهای جدید
"""

import json
import asyncio
import hashlib
import logging
import os
import uuid
import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from admin_router import router as admin_router
import admission_chance_api as admission_chance_api_module
import commercial_api as commercial_api_module
from commercial_api import router as commercial_router
from dark_horse_engine_v2 import DarkHorseEngineV2
from feedback_api import router as feedback_router, legacy_router as feedback_legacy_router
from ai_counsel_service import generate_counseling
from ai_rate_limit import COUNSEL_RATE_LIMITER, DISCOVERY_RATE_LIMITER
from request_body_limit_middleware import RequestBodyLimitMiddleware

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

_ADMISSION_RUNTIME_FINGERPRINT_FILES = (
    "admission_chance_api.py",
)

_RUNTIME_CODE_FINGERPRINT_FILES = (
    "main_v2.py",
    "admission_chance_api.py",
)


def _runtime_env_commit() -> str | None:
    return (
        os.getenv("GIT_COMMIT")
        or os.getenv("SOURCE_COMMIT")
        or os.getenv("COMMIT_SHA")
        or os.getenv("LIARA_GIT_COMMIT")
        or None
    )


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("utf-8")
    return hashlib.sha1(header + payload).hexdigest()


def _runtime_build_fingerprint() -> dict:
    root = os.path.dirname(os.path.abspath(__file__))
    files = {}
    aggregate = hashlib.sha256()
    git_blobs = {}
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
        if relative_path in {"majors_database_v2.json", "school_branches_v2.json"}:
            git_blobs[relative_path] = _git_blob_sha1(payload)
        aggregate.update(relative_path.encode("utf-8"))
        aggregate.update(b"\\0")
        aggregate.update(payload)
    return {
        "algorithm": "sha256",
        "fingerprint": aggregate.hexdigest(),
        "files": files,
        "git_sha": _runtime_env_commit(),
        "runtime_commit": _runtime_env_commit(),
        "runtime_version": os.getenv("APP_VERSION") or os.getenv("RELEASE_VERSION") or None,
        "majors_blob_sha": git_blobs.get("majors_database_v2.json"),
        "school_branches_blob_sha": git_blobs.get("school_branches_v2.json"),
        "engine_file_sha": files.get("dark_horse_engine_v2.py", {}).get("sha256"),
        "cutover": str(os.getenv("POSTGRES_RUNTIME_CUTOVER_APPROVED", "false")).strip().lower() == "true",
        "admission_runtime_files": _runtime_file_fingerprints(root, _ADMISSION_RUNTIME_FINGERPRINT_FILES),
        "runtime_code_files": _runtime_file_fingerprints(root, _RUNTIME_CODE_FINGERPRINT_FILES),
    }


def _runtime_file_fingerprints(root: str, relative_paths: tuple[str, ...]) -> dict:
    result = {}
    for relative_path in relative_paths:
        path = os.path.join(root, relative_path)
        try:
            with open(path, "rb") as fh:
                payload = fh.read()
        except OSError as exc:
            result[relative_path] = {"available": False, "error": str(exc)}
            continue
        result[relative_path] = {
            "available": True,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
    return result


def _describe_routes(routes) -> list[dict]:
    described = []
    for route in routes:
        endpoint = getattr(route, "endpoint", None)
        described.append(
            {
                "path": getattr(route, "path", None),
                "methods": sorted(getattr(route, "methods", None) or []),
                "name": getattr(route, "name", None),
                "endpoint_module": getattr(endpoint, "__module__", None),
                "endpoint_name": getattr(endpoint, "__name__", None),
            }
        )
    return described


def _runtime_admission_route_probe() -> dict:
    expected_path = "/api/v1/admission/chance"
    try:
        resolved = str(app.url_path_for("admission_chance"))
    except Exception as exc:
        return {
            "registered": False,
            "resolved_path": None,
            "error": str(exc),
        }
    return {
        "registered": resolved == expected_path,
        "resolved_path": resolved,
    }


def _runtime_module_diagnostics() -> dict:
    admission_router = getattr(admission_chance_api_module, "router", None)
    commercial_module_router = getattr(commercial_api_module, "router", None)
    return {
        "commercial_api": {
            "loaded": True,
            "file": getattr(commercial_api_module, "__file__", None),
            "router_route_count": len(getattr(commercial_module_router, "routes", ()) or ()),
        },
        "admission_chance_api": {
            "loaded": True,
            "file": getattr(admission_chance_api_module, "__file__", None),
            "router_route_count": len(getattr(admission_router, "routes", ()) or ()),
        },
        "admission_module_routes": _describe_routes(
            getattr(admission_router, "routes", ()) or ()
        ),
        "commercial_router_routes": _describe_routes(
            getattr(commercial_router, "routes", ()) or ()
        ),
        "app_registered_routes": _describe_routes(app.routes),
    }


class DarkHorseDiscoverRequest(BaseModel):
    micro_motives: list = Field(default_factory=list, max_length=100)
    sjt_answers: dict = Field(default_factory=dict, max_length=25)
    conjoint_choices: dict = Field(default_factory=dict, max_length=15)
    session_id: str | None = Field(default=None, min_length=8, max_length=64)


MAX_DISCOVERY_PAYLOAD_BYTES = 16 * 1024
MAX_COUNSEL_PAYLOAD_BYTES = 32 * 1024


def _enforce_payload_limit(
    req: Request,
    payload: BaseModel | dict,
    *,
    max_bytes: int,
    endpoint_label: str,
) -> None:
    """Bound discover/counsel JSON payloads before expensive processing."""
    declared_length = (getattr(req, "headers", None) or {}).get("content-length")
    if declared_length is not None:
        try:
            declared_bytes = int(declared_length)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="طول درخواست نامعتبر است") from exc
        if declared_bytes < 0 or declared_bytes > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"حجم درخواست {endpoint_label} از سقف مجاز بیشتر است.",
            )

    serializable = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    try:
        actual_bytes = len(
            json.dumps(serializable, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="محتوای درخواست نامعتبر است") from exc
    if actual_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"حجم درخواست {endpoint_label} از سقف مجاز بیشتر است.",
        )


def _enforce_public_rate_limit(req: Request, limiter, endpoint_label: str) -> None:
    """Rate-limit intentionally public endpoints by client address."""
    client = getattr(req, "client", None)
    client_key = client.host if client else "unknown"
    allowed, retry_after = limiter.allow(client_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"تعداد درخواست‌های {endpoint_label} بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(retry_after)},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Dark Horse API V2.0 ...")

    logger.info("✅ COMMERCIAL_ROUTER_IMPORTED=%s", commercial_router is not None)
    logger.info("✅ ADMIN_ROUTER_IMPORTED=%s", admin_router is not None)
    logger.info("✅ FEEDBACK_ROUTER_IMPORTED=%s", feedback_router is not None)

    try:
        import billing_models  # noqa: F401
        import models  # noqa: F401
        from database import is_configured

        if is_configured():
            logger.info("✅ Operational DB configured; schema lifecycle is Alembic-only.")
        else:
            logger.warning("⚠️ DATABASE_URL not configured; operational DB disabled.")
    except Exception as e:
        logger.error("❌ Operational DB init failed: %s", e, exc_info=True)

    # Keep runtime state fail-closed across startup attempts. Do not yield the
    # ASGI lifespan until all mandatory reference data and the engine are ready.
    app.state.engine = None
    app.state.branch_engine = None
    try:
        engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json"
        )
    except Exception as exc:
        app.state.engine = None
        app.state.branch_engine = None
        logger.exception(
            "❌ Required scoring references or DarkHorseEngineV2 initialization failed; startup aborted."
        )
        raise RuntimeError(
            "Required scoring references or DarkHorseEngineV2 initialization failed; refusing startup."
        ) from exc

    app.state.engine = engine
    app.state.branch_engine = engine
    logger.info("✅ DarkHorseEngineV2 آماده است (shared engine for majors + branches).")

    yield
    logger.info("🛑 Shutting down V2.0 ...")


app = FastAPI(title="Dark Horse API V2.0", version="2.0", lifespan=lifespan)

# Byte limits apply before JSON parsing on request paths that had no transport-level cap.
# Feedback routes already stream and enforce their own 32 KiB cap.
# Billing create-payment and the gateway callback are deliberately excluded from this change.
REQUEST_BODY_LIMITS = {
    ("POST", "/api/v1/auth/register"): 8 * 1024,
    ("POST", "/api/v1/auth/register/verify"): 4 * 1024,
    ("POST", "/api/v1/auth/login"): 8 * 1024,
    ("POST", "/api/v1/admission/chance"): 32 * 1024,
    ("POST", "/api/v1/me/consume-test"): 4 * 1024,
    ("POST", "/api/v1/me/save-result"): 128 * 1024,
    ("POST", "/api/v2/darkhorse/discover"): 16 * 1024,
    ("POST", "/api/v2/darkhorse/branch-discovery"): 16 * 1024,
    ("POST", "/api/v2/darkhorse/counsel"): 32 * 1024,
}
# Register this first so CORS middleware remains outside and keeps its existing policy.
app.add_middleware(RequestBodyLimitMiddleware, limits=REQUEST_BODY_LIMITS)
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
    build = _runtime_build_fingerprint()
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
        "git_sha": build["git_sha"],
        "majors_blob_sha": build["majors_blob_sha"],
        "school_branches_blob_sha": build["school_branches_blob_sha"],
        "cutover": build["cutover"],
        "engine_file_sha": build["engine_file_sha"],
        "runtime_commit": build["runtime_commit"],
        "runtime_version": build["runtime_version"],
        "scoring_build_fingerprint": build["fingerprint"],
        "fingerprint_algorithm": build["algorithm"],
        "scoring_fingerprinted_files": build["files"],
        "admission_runtime_files": build["admission_runtime_files"],
        "runtime_code_files": build["runtime_code_files"],
        # Check the route by its FastAPI name/path resolution and OpenAPI method.
        # A direct app.routes path scan can be false-negative for included routers.
        "admission_chance_route_mounted": (
            _runtime_admission_route_probe().get("registered") is True
            and "post" in (
                app.openapi().get("paths", {}).get("/api/v1/admission/chance", {}) or {}
            )
        ),
        "runtime_module_diagnostics": _runtime_module_diagnostics(),
        "admission_route_probe": _runtime_admission_route_probe(),
        "openapi_has_admission_route": "/api/v1/admission/chance" in (
            app.openapi().get("paths", {}) or {}
        ),
    }


@app.get("/")
async def root():
    return {"name": "Dark Horse API V2.0", "status": "online"}


def _authenticated_user_id(req: Request) -> int | None:
    authorization = (getattr(req, "headers", None) or {}).get("authorization")
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


def _journey_charge_exists(user_id: int, session_uuid: str) -> bool:
    """Fail closed unless commercial billing records a charge for this user/session."""
    db = None
    try:
        from billing_models import JourneyCreditConsumption
        from database import SessionLocal
        from sqlalchemy import select

        db = SessionLocal()
        return db.scalar(
            select(JourneyCreditConsumption.session_uuid)
            .where(
                JourneyCreditConsumption.user_id == user_id,
                JourneyCreditConsumption.session_uuid == session_uuid,
            )
            .limit(1)
        ) is not None
    except Exception as exc:
        logger.warning("Journey charge lookup failed closed: %s", exc)
        return False
    finally:
        if db is not None:
            db.close()


def _require_charged_journey(req: Request, session_uuid: str | None) -> int:
    """Require both a valid commercial session and an idempotently charged journey."""
    user_id = _authenticated_user_id(req)
    if user_id is None:
        raise HTTPException(status_code=401, detail="برای دریافت نتیجه، وارد حساب کاربری شوید.")
    if not session_uuid or not (8 <= len(str(session_uuid)) <= 64):
        raise HTTPException(status_code=400, detail="شناسهٔ سفر معتبر نیست.")
    if not _journey_charge_exists(user_id, str(session_uuid)):
        raise HTTPException(
            status_code=402,
            detail="برای این سفر اعتبار تجاری تأییدشده‌ای ثبت نشده است.",
        )
    return user_id


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
                    user_agent=(getattr(req, "headers", None) or {}).get("user-agent"),
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
            "user_agent": (getattr(req, "headers", None) or {}).get("user-agent"),
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


def _rankable_score(score, components):
    """Never coerce null to zero or persist unavailable results as numeric fits."""
    return (isinstance(score, (int, float)) and not isinstance(score, bool)
            and math.isfinite(score)
            and ("v_score" not in components or
                 isinstance(components["v_score"], (int, float))
                 and not isinstance(components["v_score"], bool)
                 and math.isfinite(components["v_score"])))


@app.post("/api/v2/darkhorse/discover")
async def discover_v2(request: DarkHorseDiscoverRequest, req: Request):
    _enforce_public_rate_limit(req, DISCOVERY_RATE_LIMITER, "کشف رشته")
    _enforce_payload_limit(
        req, request, max_bytes=MAX_DISCOVERY_PAYLOAD_BYTES, endpoint_label="کشف رشته"
    )
    engine = req.app.state.engine
    if engine is None:
        raise HTTPException(503, detail="موتور امتیازدهی V2.0 در دسترس نیست")
    try:
        user_id = _require_charged_journey(req, request.session_id)
        session_uuid, persisted_session_id = _persist_discovery_session(req, request, user_id=user_id)

        discovery = await asyncio.to_thread(
            engine.discover_individuality,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {},
        )

        recommendations = []
        incomplete = list(discovery.get("incomplete_assessments", []))
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
            if not _rankable_score(rec["fit_score"], rec["raw_components"]):
                incomplete.append({**item, "status": "incomplete", "score": None,
                                   "v_result": fit.get("value_assessment", {"score": None, "status": fit.get("status", "incomplete")})})
                continue
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
                "status": "incomplete" if incomplete else discovery.get("status", "complete"),
                "incomplete_assessments": incomplete,
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
    _enforce_public_rate_limit(req, DISCOVERY_RATE_LIMITER, "هدایت تحصیلی")
    _enforce_payload_limit(
        req, request, max_bytes=MAX_DISCOVERY_PAYLOAD_BYTES, endpoint_label="هدایت تحصیلی"
    )
    engine = req.app.state.branch_engine
    if engine is None:
        raise HTTPException(503, detail="موتور شاخه‌ها V2.0 در دسترس نیست")
    try:
        user_id = _require_charged_journey(req, request.session_id)
        session_uuid, persisted_session_id = _persist_discovery_session(req, request, user_id=user_id)
        result = await asyncio.to_thread(
            engine.recommend_school_branch,
            request.micro_motives,
            request.sjt_answers or {},
            request.conjoint_choices or {},
        )

        branches = []
        incomplete = list(result.get("incomplete_assessments", []))
        for branch in result.get("recommended_branches", []):
            branch_item = {
                "branch_name_fa": branch.get("branch_name_fa") or branch.get("branch_name") or "",
                "fit_score": branch.get("average_score", branch.get("fit_score")),
                "status": branch.get("status", "complete"),
                "value_assessment": branch.get("value_assessment"),
                "count": branch.get("count", 0),
                "avg_components": branch.get("avg_components", {}),
                "evidence": branch.get("evidence", {}),
            }
            if not _rankable_score(branch_item["fit_score"], branch_item["avg_components"]):
                incomplete.append({**branch, "status": "incomplete", "score": None,
                                   "v_result": branch.get("value_assessment") or {"score": None, "status": branch.get("status", "incomplete")}})
                continue
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
                "status": "incomplete" if incomplete else result.get("status", "complete"),
                "incomplete_assessments": incomplete,
                "best_branch": result.get("best_branch") if any(b["branch_name_fa"] == result.get("best_branch") for b in branches) else None,
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
    client = getattr(req, "client", None)
    client_key = client.host if client else "unknown"
    allowed, retry_after = COUNSEL_RATE_LIMITER.allow(client_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="تعداد درخواست‌های مشاوره هوش مصنوعی بیش از حد مجاز است؛ لطفاً کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(retry_after)},
        )
    _enforce_payload_limit(
        req, request, max_bytes=MAX_COUNSEL_PAYLOAD_BYTES, endpoint_label="مشاوره"
    )

    profile = request.get("profile") or {}
    session_uuid = (
        request.get("session_id")
        or request.get("session_uuid")
        or (profile.get("session_id") if isinstance(profile, dict) else None)
    )
    _require_charged_journey(req, session_uuid)
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