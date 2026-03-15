from fastapi import HTTPException

from app.config import get_settings


def normalize_shop_domain(value: str) -> str:
    return value.strip().lower()


def require_shopify_ingest_secret(
    x_vizualizd_shopify_secret: str | None,
    settings_getter=get_settings,
) -> None:
    settings = settings_getter()
    expected_secret = (settings.shopify_ingest_shared_secret or "").strip()
    if not expected_secret:
        raise HTTPException(status_code=503, detail="Shopify ingest secret is not configured")
    if not x_vizualizd_shopify_secret or x_vizualizd_shopify_secret.strip() != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid Shopify ingest secret")
