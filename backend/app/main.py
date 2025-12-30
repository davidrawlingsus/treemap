from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, or_, func, inspect, MetaData, Table, Column as SAColumn, Integer, String, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import sqltypes
from typing import List, Optional
import json
import os
import csv
import io
import uuid
import hashlib
from uuid import UUID
from pathlib import Path
from urllib.parse import quote, urlparse
import logging
from dotenv import load_dotenv

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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    settings = get_settings()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    app.state.openai_service = OpenAIService(
        api_key=openai_api_key,
        model="gpt-4o-mini"
    )
    logger.info(f"OpenAI service initialized: {app.state.openai_service.is_configured()}")


# CORS configuration - allow frontend to communicate with backend
# Allow all Railway origins (they use *.up.railway.app pattern) for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(.*\.up\.railway\.app|localhost)(:\d+)?$",  # Allow all Railway URLs and localhost
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Include founder admin router
from app.routers import founder_admin
app.include_router(founder_admin.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

