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


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Visualizd API", version="0.1.0")


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

    def _origin_allowed(self, origin: str) -> bool:
        if not origin:
            return False
        origin_stripped = origin.rstrip("/")
        if origin_stripped in self._allowed:
            return True
        if origin in self._allowed:
            return True
        return bool(_CORS_ORIGIN_REGEX.match(origin))

    async def dispatch(self, request: StarletteRequest, call_next):
        origin = request.headers.get("origin") or ""
        # Handle OPTIONS preflight ourselves so it always gets CORS headers (avoids proxy stripping).
        if request.method == "OPTIONS" and self._origin_allowed(origin):
            return Response(
                status_code=200,
                headers={
                    "access-control-allow-origin": origin,
                    "access-control-allow-credentials": "true",
                    "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "access-control-allow-headers": "*",
                    "access-control-max-age": "86400",
                },
            )
        response = await call_next(request)
        if not self._origin_allowed(origin):
            return response
        if not response.headers.get("access-control-allow-origin"):
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        return response


app.add_middleware(EnsureCORSHeadersMiddleware, allowed_origins=all_cors_origins)

# Include static file serving router
from app.routers import static

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

# Include clients router
from app.routers import clients
app.include_router(clients.router)

# Include dimensions router
from app.routers import dimensions
app.include_router(dimensions.router)

# Include founder admin router (now modularized)
from app.routers import founder_admin
app.include_router(founder_admin.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

