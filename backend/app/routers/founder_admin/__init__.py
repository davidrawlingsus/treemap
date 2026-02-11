"""
Founder admin module - aggregates all founder-only admin routers.
"""
from fastapi import APIRouter

# Import sub-routers
from .users import router as users_router
from .domains import router as domains_router
from .emails import router as emails_router
from .voc_editor import router as voc_editor_router
from .database import router as database_router
from .prompts import router as prompts_router
from .context_menu_groups import router as context_menu_groups_router
from .facebook_ads import router as facebook_ads_router
from .ad_images import router as ad_images_router
from .meta_ads import router as meta_ads_router
from .saved_emails import router as saved_emails_router
from .ad_library_imports import router as ad_library_imports_router
from .voc_ads_comparison import router as voc_ads_comparison_router
from .creative_mri import router as creative_mri_router

# Create main router that includes all sub-routers
router = APIRouter(tags=["founder-admin"])

# Include all sub-routers
router.include_router(users_router)
router.include_router(domains_router)
router.include_router(emails_router)
router.include_router(voc_editor_router)
router.include_router(database_router)
router.include_router(prompts_router)
router.include_router(context_menu_groups_router)
router.include_router(facebook_ads_router)
router.include_router(ad_images_router)
router.include_router(meta_ads_router)
router.include_router(saved_emails_router)
router.include_router(ad_library_imports_router)
router.include_router(voc_ads_comparison_router)
router.include_router(creative_mri_router)

