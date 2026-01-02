"""
Tests for utility functions extracted from main.py.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.utils import extract_origin, build_email_service, serialize_authorized_domain, find_frontend_path
from app.database import normalize_database_url
from app.models import AuthorizedDomain, Client
from app.schemas import AuthorizedDomainResponse


class TestExtractOrigin:
    """Tests for extract_origin function."""

    def test_extract_origin_with_full_url(self):
        """Extract origin from a full URL."""
        url = "https://example.com/path/to/resource?query=value"
        result = extract_origin(url)
        assert result == "https://example.com"

    def test_extract_origin_with_port(self):
        """Extract origin from URL with port."""
        url = "http://localhost:3000/some/path"
        result = extract_origin(url)
        assert result == "http://localhost:3000"

    def test_extract_origin_with_https(self):
        """Extract origin from HTTPS URL."""
        url = "https://api.example.com/v1/endpoint"
        result = extract_origin(url)
        assert result == "https://api.example.com"

    def test_extract_origin_with_trailing_slash(self):
        """Extract origin from URL with trailing slash."""
        url = "https://example.com/"
        result = extract_origin(url)
        assert result == "https://example.com"

    def test_extract_origin_with_whitespace(self):
        """Extract origin from URL with whitespace."""
        url = "  https://example.com  "
        result = extract_origin(url)
        assert result == "https://example.com"

    def test_extract_origin_none(self):
        """Return None when URL is None."""
        result = extract_origin(None)
        assert result is None

    def test_extract_origin_empty_string(self):
        """Return None when URL is empty string."""
        result = extract_origin("")
        assert result is None

    def test_extract_origin_invalid_url(self):
        """Return None when URL has no scheme or netloc."""
        url = "not-a-valid-url"
        result = extract_origin(url)
        assert result is None

    def test_extract_origin_path_only(self):
        """Return None when URL has no scheme."""
        url = "/path/to/resource"
        result = extract_origin(url)
        assert result is None


class TestBuildEmailService:
    """Tests for build_email_service function."""

    def test_build_email_service_with_all_settings(self):
        """Build EmailService with all settings provided."""
        mock_settings = Mock()
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.resend_from_email = "test@example.com"
        mock_settings.resend_reply_to_email = "reply@example.com"

        email_service = build_email_service(mock_settings)

        assert email_service.api_key == "test_api_key"
        assert email_service.from_email == "test@example.com"
        assert email_service.reply_to_email == "reply@example.com"

    def test_build_email_service_with_none_reply_to(self):
        """Build EmailService with reply_to_email as None."""
        mock_settings = Mock()
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.resend_from_email = "test@example.com"
        mock_settings.resend_reply_to_email = None

        email_service = build_email_service(mock_settings)

        assert email_service.api_key == "test_api_key"
        assert email_service.from_email == "test@example.com"
        assert email_service.reply_to_email is None

    def test_build_email_service_with_empty_strings(self):
        """Build EmailService with empty string values."""
        mock_settings = Mock()
        mock_settings.resend_api_key = ""
        mock_settings.resend_from_email = ""
        mock_settings.resend_reply_to_email = ""

        email_service = build_email_service(mock_settings)

        assert email_service.api_key == ""
        assert email_service.from_email == ""
        assert email_service.reply_to_email == ""


class TestSerializeAuthorizedDomain:
    """Tests for serialize_authorized_domain function."""

    def test_serialize_authorized_domain_with_clients(self):
        """Serialize AuthorizedDomain with associated clients."""
        # Create mock domain
        domain_id = uuid4()
        domain = Mock(spec=AuthorizedDomain)
        domain.id = domain_id
        domain.domain = "example.com"
        domain.description = "Test domain"
        domain.created_at = datetime.now(timezone.utc)
        domain.updated_at = datetime.now(timezone.utc)

        # Create mock clients with all required fields
        now = datetime.now(timezone.utc)
        client1 = Mock(spec=Client)
        client1.id = uuid4()
        client1.name = "Client B"
        client1.slug = "client-b"
        client1.is_active = True
        client1.business_summary = None
        client1.client_url = None
        client1.created_at = now
        client1.updated_at = now
        
        client2 = Mock(spec=Client)
        client2.id = uuid4()
        client2.name = "Client A"
        client2.slug = "client-a"
        client2.is_active = True
        client2.business_summary = None
        client2.client_url = None
        client2.created_at = now
        client2.updated_at = now

        # Create mock client links
        link1 = Mock()
        link1.client = client1
        link2 = Mock()
        link2.client = client2
        domain.client_links = [link1, link2]

        result = serialize_authorized_domain(domain)

        assert isinstance(result, AuthorizedDomainResponse)
        assert result.id == domain_id
        assert result.domain == "example.com"
        assert result.description == "Test domain"
        assert len(result.clients) == 2
        # Clients should be sorted alphabetically by name
        assert result.clients[0].name == "Client A"
        assert result.clients[1].name == "Client B"

    def test_serialize_authorized_domain_with_no_clients(self):
        """Serialize AuthorizedDomain with no associated clients."""
        domain_id = uuid4()
        domain = Mock(spec=AuthorizedDomain)
        domain.id = domain_id
        domain.domain = "example.com"
        domain.description = None
        domain.created_at = datetime.now(timezone.utc)
        domain.updated_at = datetime.now(timezone.utc)
        domain.client_links = []

        result = serialize_authorized_domain(domain)

        assert isinstance(result, AuthorizedDomainResponse)
        assert result.id == domain_id
        assert result.domain == "example.com"
        assert result.description is None
        assert len(result.clients) == 0

    def test_serialize_authorized_domain_with_none_client_link(self):
        """Serialize AuthorizedDomain with client_links containing None client."""
        domain_id = uuid4()
        domain = Mock(spec=AuthorizedDomain)
        domain.id = domain_id
        domain.domain = "example.com"
        domain.description = "Test"
        domain.created_at = datetime.now(timezone.utc)
        domain.updated_at = datetime.now(timezone.utc)

        # Create mock client link with None client
        link = Mock()
        link.client = None
        domain.client_links = [link]

        result = serialize_authorized_domain(domain)

        assert isinstance(result, AuthorizedDomainResponse)
        assert len(result.clients) == 0  # None clients should be filtered out

    def test_serialize_authorized_domain_clients_sorted(self):
        """Verify that clients are sorted alphabetically by name (case-insensitive)."""
        domain_id = uuid4()
        domain = Mock(spec=AuthorizedDomain)
        domain.id = domain_id
        domain.domain = "example.com"
        domain.description = "Test"
        domain.created_at = datetime.now(timezone.utc)
        domain.updated_at = datetime.now(timezone.utc)

        # Create clients with mixed case names and all required fields
        now = datetime.now(timezone.utc)
        client1 = Mock(spec=Client)
        client1.id = uuid4()
        client1.name = "Zebra Client"
        client1.slug = "zebra-client"
        client1.is_active = True
        client1.business_summary = None
        client1.client_url = None
        client1.created_at = now
        client1.updated_at = now
        
        client2 = Mock(spec=Client)
        client2.id = uuid4()
        client2.name = "apple client"
        client2.slug = "apple-client"
        client2.is_active = True
        client2.business_summary = None
        client2.client_url = None
        client2.created_at = now
        client2.updated_at = now
        
        client3 = Mock(spec=Client)
        client3.id = uuid4()
        client3.name = "Banana Client"
        client3.slug = "banana-client"
        client3.is_active = True
        client3.business_summary = None
        client3.client_url = None
        client3.created_at = now
        client3.updated_at = now

        link1 = Mock()
        link1.client = client1
        link2 = Mock()
        link2.client = client2
        link3 = Mock()
        link3.client = client3
        domain.client_links = [link1, link2, link3]

        result = serialize_authorized_domain(domain)

        assert len(result.clients) == 3
        # Should be sorted case-insensitively: apple, Banana, Zebra
        assert result.clients[0].name == "apple client"
        assert result.clients[1].name == "Banana Client"
        assert result.clients[2].name == "Zebra Client"


class TestNormalizeDatabaseUrl:
    """Tests for normalize_database_url function."""

    def test_normalize_postgresql_url(self):
        """Normalize standard postgresql:// URL to use psycopg driver."""
        url = "postgresql://user:pass@localhost/dbname"
        result = normalize_database_url(url)
        assert result == "postgresql+psycopg://user:pass@localhost/dbname"

    def test_normalize_postgresql_url_with_port(self):
        """Normalize postgresql:// URL with port."""
        url = "postgresql://user:pass@localhost:5432/dbname"
        result = normalize_database_url(url)
        assert result == "postgresql+psycopg://user:pass@localhost:5432/dbname"

    def test_keep_already_normalized_url(self):
        """Keep URL that already has psycopg driver specified."""
        url = "postgresql+psycopg://user:pass@localhost/dbname"
        result = normalize_database_url(url)
        assert result == "postgresql+psycopg://user:pass@localhost/dbname"

    def test_keep_sqlite_url(self):
        """Keep SQLite URL unchanged."""
        url = "sqlite:///./treemap.db"
        result = normalize_database_url(url)
        assert result == "sqlite:///./treemap.db"

    def test_keep_postgres_url_with_other_driver(self):
        """Keep URL with other driver (e.g., psycopg2) unchanged."""
        url = "postgresql+psycopg2://user:pass@localhost/dbname"
        result = normalize_database_url(url)
        assert result == "postgresql+psycopg2://user:pass@localhost/dbname"

    def test_keep_url_containing_psycopg_in_path(self):
        """Keep URL unchanged even if 'psycopg' appears in the path."""
        # This tests the exact logic: '+psycopg' must be in the URL (for driver spec)
        url = "postgresql://user:pass@localhost/psycopg_db"
        result = normalize_database_url(url)
        # Should still normalize because '+psycopg' is not in the URL
        assert result == "postgresql+psycopg://user:pass@localhost/psycopg_db"

    def test_normalize_url_with_query_params(self):
        """Normalize postgresql:// URL with query parameters."""
        url = "postgresql://user:pass@localhost/dbname?sslmode=require"
        result = normalize_database_url(url)
        assert result == "postgresql+psycopg://user:pass@localhost/dbname?sslmode=require"


class TestFindFrontendPath:
    """Tests for find_frontend_path function."""

    def test_find_frontend_path_returns_path(self):
        """Test that find_frontend_path returns a Path object."""
        # Use real filesystem for this test since we're in a real project
        result = find_frontend_path()
        assert isinstance(result, Path)
        assert result.is_absolute() or result == Path.cwd()

    def test_find_frontend_path_with_main_file_path(self):
        """Test find_frontend_path with explicit main_file_path parameter."""
        # Use real filesystem for this test since we're in a real project
        main_file = Path(__file__).parent.parent / "app" / "main.py"
        if main_file.exists():
            result = find_frontend_path(main_file_path=main_file)
            assert isinstance(result, Path)
            # Result should be a valid path
            assert result.exists() or result == Path.cwd()

    def test_find_frontend_path_checks_cwd_first(self):
        """Test that find_frontend_path checks cwd first (characterization test)."""
        # This is a characterization test - we verify the function works
        # with the real filesystem since we're in a real project
        result = find_frontend_path()
        # Result should be a valid Path
        assert isinstance(result, Path)
        # If index.html exists in cwd, result should be cwd
        # Otherwise, it should be one of the fallback paths
        assert result.exists() or result == Path.cwd()
