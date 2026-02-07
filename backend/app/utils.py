"""
Utility functions extracted from main.py for better code organization.
"""
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse

from app.services import EmailService
from app.models import AuthorizedDomain, AuthorizedEmail
from app.schemas import AuthorizedDomainResponse, AuthorizedEmailResponse, ClientResponse


def find_frontend_path(main_file_path: Optional[Path] = None) -> Path:
    """
    Find the frontend directory path by checking multiple possible locations.
    
    Prioritizes current working directory (Railway uses /app), then checks
    standard project structure and Railway defaults.
    
    Args:
        main_file_path: Optional Path to main.py file for path calculation.
                       If None, uses utils.py location to infer project root.
    
    Returns:
        Path to frontend directory (where index.html is located)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try multiple possible paths for Railway deployment
    # Prioritize current working directory (Railway uses /app)
    if main_file_path:
        # Use provided main.py path to calculate project root
        project_root = main_file_path.parent.parent.parent
    else:
        # Fallback: calculate from utils.py location (backend/app/utils.py -> project root)
        project_root = Path(__file__).parent.parent.parent
    
    possible_paths = [
        Path.cwd(),  # Current working directory (Railway uses /app) - check this first
        project_root,  # Standard: backend/app/main.py -> project root
        Path("/app"),  # Railway default app directory
        project_root.parent if project_root != Path.cwd() else Path("/app"),  # Railway might have different structure
    ]

    for path in possible_paths:
        test_path = path / "index.html"
        if test_path.exists():
            logger.info(f"Found frontend files at: {path}")
            logger.info(f"index.html exists at: {test_path}")
            return path

    # Fallback to current working directory if none found (Railway default)
    logger.warning(f"Frontend path not found, using current working directory: {Path.cwd()}")
    return Path.cwd()


def extract_origin(url: str | None) -> Optional[str]:
    """Return the origin (scheme + host [+ port]) from a URL-like string."""
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _clean_env_email(value):
    """Strip and remove trailing # comment so .env line concatenation doesn't break Resend."""
    if value is None:
        return None
    s = (value or "").strip()
    if "#" in s:
        s = s.split("#", 1)[0].strip()
    return s or None


def build_email_service(settings):
    """Instantiate an EmailService based on current settings."""
    return EmailService(
        api_key=(settings.resend_api_key or "").strip() or None,
        from_email=_clean_env_email(settings.resend_from_email),
        reply_to_email=_clean_env_email(settings.resend_reply_to_email),
    )


def serialize_authorized_domain(domain: AuthorizedDomain) -> AuthorizedDomainResponse:
    """Convert an AuthorizedDomain ORM object into a response model."""
    clients = [
        ClientResponse.model_validate(link.client)
        for link in domain.client_links
        if link.client is not None
    ]
    clients.sort(key=lambda client: client.name.lower())
    return AuthorizedDomainResponse(
        id=domain.id,
        domain=domain.domain,
        description=domain.description,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        clients=clients,
    )


def serialize_authorized_email(email: AuthorizedEmail) -> AuthorizedEmailResponse:
    """Convert an AuthorizedEmail ORM object into a response model."""
    clients = [
        ClientResponse.model_validate(link.client)
        for link in email.client_links
        if link.client is not None
    ]
    clients.sort(key=lambda client: client.name.lower())
    return AuthorizedEmailResponse(
        id=email.id,
        email=email.email,
        description=email.description,
        created_at=email.created_at,
        updated_at=email.updated_at,
        clients=clients,
    )

