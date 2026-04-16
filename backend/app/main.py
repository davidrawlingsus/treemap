from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, or_, func, inspect, MetaData, Table, Column as SAColumn, Integer, String, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import sqltypes
from typing import List, Optional
import os
import csv
import io
import uuid
import hashlib
from uuid import UUID
from pathlib import Path
from urllib.parse import quote, urlparse
import re
import logging
from dotenv import load_dotenv

# Configure logging to output INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file
load_dotenv()

from app.database import get_db, engine, Base
from app.models import (
    Client,
    DataSource,
    DimensionName,
    DimensionSummary,
    User,
    Membership,
    ProcessVoc,
    AuthorizedDomain,
    AuthorizedDomainClient,
    Insight,
)
from app.schemas import (
    ClientCreate,
    ClientResponse,
    DataSourceCreate,
    DataSourceDetail,
    DataSourceResponse,
    DimensionNameBatchUpdate,
    DimensionNameCreate,
    DimensionNameResponse,
    DimensionQuestionInfo,
    FieldMetadata,
    FieldMetadataResponse,
    FounderUserMembership,
    FounderUserSummary,
    ImpersonateRequest,
    InsightCreate,
    InsightUpdate,
    InsightResponse,
    InsightListResponse,
    InsightOrigin,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    ProcessVocAdminListResponse,
    ProcessVocBulkUpdateRequest,
    ProcessVocBulkUpdateResponse,
    ProcessVocListResponse,
    ProcessVocResponse,
    QuestionInfo,
    AuthorizedDomainCreate,
    AuthorizedDomainResponse,
    AuthorizedDomainUpdate,
    DataSourceWithQuestions,
    DynamicBulkUpdateRequest,
    Token,
    UserLogin,
    UserResponse,
    UserWithClients,
    VocClientInfo,
    VocProjectInfo,
    VocSourceInfo,
    TableInfo,
    ColumnInfo,
    TableDataResponse,
    RowCreateRequest,
    RowUpdateRequest,
    TableCreateRequest,
    ColumnAddRequest,
    CsvColumnMapping,
    CsvUploadResponse,
    CsvColumnMappingRequest,
    CsvSaveResponse,
)
from app.transformers import DataTransformer, DataSourceType
from app.config import get_settings, get_cors_origins
from app.auth import (
    get_current_user, get_current_active_founder,
    create_access_token, verify_password,
    generate_magic_link_token, is_magic_link_token_valid,
)
from app.services import EmailService, MagicLinkEmailParams
from app.services.openai_service import OpenAIService, DimensionData
from app.services.dimension_sampler import DimensionSampler
from app.utils import extract_origin, build_email_service, serialize_authorized_domain, find_frontend_path
from datetime import datetime, timedelta, timezone
import time


logger = logging.getLogger(__name__)


settings_for_cors = get_settings()
cors_allow_origins: List[str] = get_cors_origins(settings_for_cors)

if cors_allow_origins:
    logger.info("Allowing additional CORS origins: %s", cors_allow_origins)


app = FastAPI(
    title="Vizualizd API",
    version="1.0.0",
    description="""
Voice of Customer (VOC) analytics API.

## Authentication

**API Key** (external/agent access): Pass your key via the `X-API-Key` header.
Each key is scoped to a single client — all data is automatically filtered.

**JWT Bearer** (web app): Pass a Bearer token via the `Authorization` header.

## Quick start (API key)

```
# 1. Discover your client
GET /api/voc/clients  →  returns your scoped client

# 2. Explore available data
GET /api/voc/sources     →  data sources (e.g. trustpilot, email_survey)
GET /api/voc/questions   →  dimensions/questions with response counts
GET /api/voc/projects    →  projects

# 3. Fetch data
GET /api/voc/data        →  raw verbatim rows (filterable)
GET /api/voc/summary     →  category → topic → verbatim hierarchy
```
""",
    openapi_tags=[
        {
            "name": "VOC Data",
            "description": "Voice of Customer data endpoints. All endpoints accept API key auth via `X-API-Key` header.",
        },
        {
            "name": "API Keys",
            "description": "Manage API keys for programmatic access. Requires JWT auth (web session).",
        },
    ],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: StarletteRequest, exc: Exception):
    """Return 500 with CORS headers so the client sees the error instead of CORS block."""
    logger.exception("Unhandled exception: %s", exc)
    origin = request.headers.get("origin") or ""
    headers = {}
    if origin and re.match(r"^https?://(.*\.up\.railway\.app|.*\.mapthegap\.ai|localhost|127\.0\.0\.1)(:\d+)?$", origin):
        headers["access-control-allow-origin"] = origin
        headers["access-control-allow-credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
        headers=headers,
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Verify google-genai is available for Creative MRI video transcripts
    try:
        from google import genai  # noqa: F401
        logger.info("google-genai available for Creative MRI video analysis")
    except ImportError:
        logger.error(
            "google-genai NOT installed - Creative MRI video transcripts will fail. "
            "Run: pip install google-genai"
        )

    settings = get_settings()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Initialize OpenAI service for dimension summaries (backward compatibility)
    app.state.openai_service = OpenAIService(
        api_key=openai_api_key,
        model="gpt-4o-mini"
    )
    logger.info(f"OpenAI service initialized: {app.state.openai_service.is_configured()}")
    
    # Initialize unified LLM service for prompt engineering
    from app.services.llm_service import LLMService
    app.state.llm_service = LLMService(
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key
    )
    logger.info(f"LLM service initialized (OpenAI: {bool(openai_api_key)}, Anthropic: {bool(anthropic_api_key)})")

    # Start background email sender thread
    import threading

    def _background_loop():
        import time as _time
        from datetime import datetime, timedelta, timezone as tz
        from app.database import SessionLocal
        from app.config import get_settings as _get_settings
        from app.services.lead_email_service import send_due_emails
        from app.models.leadgen_voc import LeadgenVocRun
        from app.services.leadgen_pipeline_runner import run_full_pipeline_background

        _settings = _get_settings()
        _active_runs = set()  # track runs we've already kicked off

        while True:
            try:
                _db = SessionLocal()

                # Send scheduled emails
                count = send_due_emails(_settings, _db)
                if count:
                    logger.info("[background] Sent %d scheduled emails", count)

                # Pick up rerun_analysis requests
                from app.services.leadgen_pipeline_runner import rerun_analysis_background
                rerun_requests = (
                    _db.query(LeadgenVocRun)
                    .filter(LeadgenVocRun.coding_status == "rerun_analysis")
                    .all()
                )
                for run in rerun_requests:
                    if run.run_id not in _active_runs:
                        logger.info("[background] Rerunning analysis for %s (%s)",
                                    run.run_id[:16], run.company_name)
                        _active_runs.add(run.run_id)
                        rerun_analysis_background(run.run_id)

                # Restart runs with stale heartbeats (thread died)
                from app.services.leadgen_pipeline_runner import HEARTBEAT_STALE_SECONDS
                bg_cutoff = datetime.now(tz.utc) - timedelta(hours=24)
                terminal = {"completed", "failed", "disabled", "rerun_analysis", "pending_import"}
                active_runs = (
                    _db.query(LeadgenVocRun)
                    .filter(
                        ~LeadgenVocRun.coding_status.in_(terminal),
                        LeadgenVocRun.created_at >= bg_cutoff,
                    )
                    .all()
                )
                now = datetime.now(tz.utc)
                for run in active_runs:
                    payload = run.payload or {}
                    heartbeat = payload.get("heartbeat")
                    if not heartbeat:
                        last_alive = run.updated_at or run.created_at
                    else:
                        try:
                            last_alive = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            last_alive = run.updated_at or run.created_at

                    seconds_since = (now - last_alive).total_seconds()
                    if seconds_since < HEARTBEAT_STALE_SECONDS:
                        # Run has a fresh heartbeat — it's alive.
                        # If we were tracking it as active, keep tracking.
                        continue

                    # Heartbeat is stale. If we already tried restarting
                    # this run and it's STILL stale, allow re-detection
                    # by removing from _active_runs so it can be retried.
                    if run.run_id in _active_runs:
                        # Already tried once — remove from tracking so we
                        # can restart it on the next loop iteration.
                        _active_runs.discard(run.run_id)
                        logger.info("[background] Run %s still stale after restart — will retry next loop",
                                    run.run_id[:16])
                        continue

                    _active_runs.add(run.run_id)
                    if payload.get("is_rerun"):
                        logger.info("[background] Heartbeat stale (%ds) for rerun %s (%s). Re-triggering analysis.",
                                    int(seconds_since), run.run_id[:16], run.company_name)
                        rerun_analysis_background(run.run_id)
                    else:
                        logger.info("[background] Heartbeat stale (%ds) for %s (%s, status=%s). Restarting.",
                                    int(seconds_since), run.run_id[:16], run.company_name, run.coding_status)
                        run_full_pipeline_background(run.run_id)

                # Clean up completed/failed from active tracking
                if _active_runs:
                    done = (
                        _db.query(LeadgenVocRun.run_id)
                        .filter(
                            LeadgenVocRun.run_id.in_(_active_runs),
                            LeadgenVocRun.coding_status.in_({"completed", "failed"}),
                        )
                        .all()
                    )
                    for (rid,) in done:
                        _active_runs.discard(rid)

                _db.close()
            except Exception as _e:
                logger.error("[background] Error: %s", _e)
            _time.sleep(60)

    _bg = threading.Thread(target=_background_loop, daemon=True)
    _bg.start()
    logger.info("Background loop started (email sender + pipeline recovery)")

    # Recover orphaned pipeline runs (e.g. killed by deploy SIGTERM)
    try:
        from app.database import SessionLocal
        from app.models.leadgen_voc import LeadgenVocRun
        from app.services.leadgen_pipeline_runner import run_full_pipeline_background
        from sqlalchemy.orm.attributes import flag_modified as _startup_fm

        from datetime import datetime, timedelta, timezone as tz

        _db = SessionLocal()
        terminal_states = {"completed", "failed", "disabled", "pending_import"}
        hard_cutoff = datetime.now(tz.utc) - timedelta(hours=24)
        MAX_RESTART_COUNT = 5

        # Mark anything older than 24h as permanently failed
        very_old = (
            _db.query(LeadgenVocRun)
            .filter(
                ~LeadgenVocRun.coding_status.in_(terminal_states),
                LeadgenVocRun.created_at < hard_cutoff,
            )
            .update({"coding_status": "failed"})
        )
        if very_old:
            logger.info("[startup-recovery] Marked %d very old runs as failed", very_old)

        # Find ALL non-terminal runs (including older ones) and restart if
        # they haven't exceeded the max restart count.  Railway deploys can
        # kill long-running extractions repeatedly, so we need to keep
        # retrying until the pipeline completes or hits the limit.
        orphaned = (
            _db.query(LeadgenVocRun)
            .filter(
                ~LeadgenVocRun.coding_status.in_(terminal_states),
                LeadgenVocRun.created_at >= hard_cutoff,
            )
            .all()
        )

        to_restart = []
        for run in orphaned:
            payload = run.payload or {}
            restart_count = payload.get("restart_count", 0)
            if restart_count >= MAX_RESTART_COUNT:
                logger.warning("[startup-recovery] Run %s (%s) exceeded %d restarts — marking failed",
                               run.run_id[:16], run.company_name, MAX_RESTART_COUNT)
                run.coding_status = "failed"
            else:
                payload["restart_count"] = restart_count + 1
                run.payload = payload
                _startup_fm(run, "payload")
                to_restart.append(run)

        _db.commit()
        _db.close()

        for run in to_restart:
            logger.info("[startup-recovery] Restarting run %s (%s, status=%s, restart #%d)",
                        run.run_id, run.company_name, run.coding_status,
                        (run.payload or {}).get("restart_count", 0))
            run_full_pipeline_background(run.run_id)

        if to_restart:
            logger.info("[startup-recovery] Restarted %d orphaned pipeline run(s)", len(to_restart))
    except Exception as _e:
        logger.error("[startup-recovery] Failed: %s", _e)


# CORS configuration - allow frontend to communicate with backend
# Allow all Railway origins (they use *.up.railway.app pattern) for flexibility
# Also allow the production frontend domains (both old and new during migration)
production_origins = [
    "https://mapthegap.ai",           # New primary domain
    "https://vizualizd.mapthegap.ai", # Subdomain for vizualizd app
    "https://marketably.ai",          # Old domain (keep during migration)
]
all_cors_origins = cors_allow_origins.copy()
for origin in production_origins:
    if origin not in all_cors_origins:
        all_cors_origins.append(origin)

# Always allow localhost development origins
localhost_origins = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]
for origin in localhost_origins:
    if origin not in all_cors_origins:
        all_cors_origins.append(origin)

logger.info(f"CORS configuration: allowing origins from regex '.*\\.up\\.railway\\.app' and explicit origins: {all_cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(.*\.up\.railway\.app|.*\.mapthegap\.ai|localhost|127\.0\.0\.1)(:\d+)?/?$",  # Allow all Railway URLs, mapthegap.ai subdomains, localhost; optional trailing slash
    allow_origins=all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Same regex as CORSMiddleware so safeguard allows *.mapthegap.ai, *.railway.app, localhost
# Optional trailing slash so origins like "https://vizualizd.mapthegap.ai/" are allowed
_CORS_ORIGIN_REGEX = re.compile(
    r"^https?://(.*\.up\.railway\.app|.*\.mapthegap\.ai|localhost|127\.0\.0\.1)(:\d+)?/?$"
)


class EnsureCORSHeadersMiddleware(BaseHTTPMiddleware):
    """Ensure CORS headers are on every response for allowed origins (safeguard for proxies/error paths)."""

    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self._allowed = set(allowed_origins)

    # Widget survey public endpoints accept requests from any origin
    _WIDGET_SURVEY_PATHS = ("/api/widget-surveys/active", "/api/widget-surveys/responses",
                            "/api/widget-surveys/heartbeat", "/api/widget-surveys/impression")

    def _is_widget_survey_path(self, path: str) -> bool:
        return any(path == p or path == p + "/" for p in self._WIDGET_SURVEY_PATHS)

    def _origin_allowed(self, origin: str, path: str = "") -> bool:
        if not origin:
            return False
        # Widget survey public endpoints allow any origin
        if self._is_widget_survey_path(path):
            return True
        origin_stripped = origin.rstrip("/")
        if origin_stripped in self._allowed:
            return True
        if origin in self._allowed:
            return True
        return bool(_CORS_ORIGIN_REGEX.match(origin))

    async def dispatch(self, request: StarletteRequest, call_next):
        origin = request.headers.get("origin") or ""
        path = request.url.path
        is_widget = self._is_widget_survey_path(path)
        # Handle OPTIONS preflight ourselves so it always gets CORS headers (avoids proxy stripping).
        if request.method == "OPTIONS" and self._origin_allowed(origin, path):
            headers = {
                "access-control-allow-origin": origin,
                "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "access-control-allow-headers": "*",
                "access-control-max-age": "86400",
            }
            # Widget endpoints don't use credentials (API key via header, not cookies)
            if not is_widget:
                headers["access-control-allow-credentials"] = "true"
            return Response(status_code=200, headers=headers)
        response = await call_next(request)
        if not self._origin_allowed(origin, path):
            return response
        if not response.headers.get("access-control-allow-origin"):
            response.headers["access-control-allow-origin"] = origin
            if not is_widget:
                response.headers["access-control-allow-credentials"] = "true"
        return response


app.add_middleware(EnsureCORSHeadersMiddleware, allowed_origins=all_cors_origins)

# Include static file serving router
from app.routers import static

# Mount widget JS directory for embeddable survey script (always, independent of frontend)
# Check multiple locations: backend/widget (Railway), or project_root/widget (local dev)
for _widget_candidate in [Path.cwd() / "widget", Path(__file__).parent.parent.parent / "widget"]:
    if _widget_candidate.exists():
        app.mount("/static/widget", StaticFiles(directory=str(_widget_candidate)), name="widget-static")
        break

# Prevent Cloudflare from caching widget JS so deploys take effect immediately
@app.middleware("http")
async def widget_cache_control(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/widget/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["CDN-Cache-Control"] = "no-store"
    return response

# Serve static files from the parent directory (where index.html is)
# This allows accessing the frontend at http://localhost:8000/index.html
frontend_path = find_frontend_path(Path(__file__))
if (frontend_path / "index.html").exists():
    # Mount static files directory to serve CSS, JS, and other assets
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    # Include static file routes
    app.include_router(static.router)

# client-insights.html removed - using SPA approach in index.html with hash routing

@app.get("/api")
def api_info():
    """API information endpoint"""
    return {"message": "Visualizd API", "version": "0.1.0"}


@app.get("/api/debug/users")
def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to list all users - for troubleshooting login"""
    users = db.query(User).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "email": u.email,
                "name": u.name,
                "is_active": u.is_active,
                "is_founder": u.is_founder
            }
            for u in users
        ]
    }





@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check if API and database are working"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Authentication Endpoints
# Include auth router
from app.routers import auth
app.include_router(auth.router)


# Include data sources router
from app.routers import data_sources
app.include_router(data_sources.router)

# Include VOC router
from app.routers import voc
app.include_router(voc.router)

# Include lead VOC router (founder-only lead run visualization endpoints)
from app.routers import voc_leads
app.include_router(voc_leads.router)

# Include clients router
from app.routers import clients
app.include_router(clients.router)

# Include dimensions router
from app.routers import dimensions
app.include_router(dimensions.router)

# Include founder admin router (now modularized)
from app.routers import founder_admin
app.include_router(founder_admin.router)

# Include billing router (Stripe checkout, portal, webhooks)
from app.routers import billing
app.include_router(billing.router)

# Include custom deal billing router (separate from SaaS billing)
from app.routers import deal_billing
app.include_router(deal_billing.router)

# Include help chat router (site widget + Slack bridge)
from app.routers import help_chat
app.include_router(help_chat.router)

# Include public leadgen router (no-auth intake flow)
from app.routers import public_leadgen
app.include_router(public_leadgen.router)

# Include Shopify survey ingest router
from app.routers import shopify
app.include_router(shopify.router)

# Include API keys router
from app.routers import api_keys
app.include_router(api_keys.router)

# Include widget survey router (popup surveys for non-Shopify sites)
from app.routers import widget_survey
app.include_router(widget_survey.router)

# Include ad library extension import router
from app.routers import ad_library_extension
app.include_router(ad_library_extension.router)

# Include extension analysis router (ad analysis, review detection, review signal)
from app.routers import extension_analysis
app.include_router(extension_analysis.router)

# Extension webhook (analytics tracking + lead ingestion)
from app.routers import extension_webhook
app.include_router(extension_webhook.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

