"""
Founder admin module - aggregates all founder-only admin routers.
"""
from fastapi import APIRouter

# Import sub-routers
from .users import router as users_router
from .domains import router as domains_router
from .voc_editor import router as voc_editor_router
from .database import router as database_router
from .prompts import router as prompts_router

# Create main router that includes all sub-routers
router = APIRouter(tags=["founder-admin"])

# Include all sub-routers
router.include_router(users_router)
router.include_router(domains_router)
router.include_router(voc_editor_router)
router.include_router(database_router)
router.include_router(prompts_router)

