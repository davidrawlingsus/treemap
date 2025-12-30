"""
Tests for CORS configuration functions.
"""
import pytest
from unittest.mock import Mock, patch

from app.config import Settings, get_cors_origins


class TestGetCorsOrigins:
    """Tests for get_cors_origins function."""

    def test_get_cors_origins_with_frontend_base_url_only(self):
        """Test CORS origins with only frontend_base_url."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "http://localhost:3000"
        settings.get_additional_cors_origins.return_value = []
        
        origins = get_cors_origins(settings)
        
        assert len(origins) == 1
        assert "http://localhost:3000" in origins

    def test_get_cors_origins_with_additional_origins_comma_separated(self):
        """Test CORS origins with comma-separated additional origins."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "http://localhost:3000"
        settings.get_additional_cors_origins.return_value = [
            "https://example.com",
            "https://app.example.com"
        ]
        
        origins = get_cors_origins(settings)
        
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins

    def test_get_cors_origins_deduplicates_origins(self):
        """Test that duplicate origins are not added."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "http://localhost:3000"
        settings.get_additional_cors_origins.return_value = [
            "http://localhost:3000",  # Duplicate of frontend_base_url
            "https://example.com"
        ]
        
        origins = get_cors_origins(settings)
        
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins
        # Verify no duplicates
        assert origins.count("http://localhost:3000") == 1

    def test_get_cors_origins_filters_invalid_origins(self):
        """Test that invalid origins are filtered out."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "http://localhost:3000"
        settings.get_additional_cors_origins.return_value = [
            "https://example.com",
            "not-a-valid-url",  # Should be filtered out
            "https://app.example.com"
        ]
        
        origins = get_cors_origins(settings)
        
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins
        assert "not-a-valid-url" not in origins

    def test_get_cors_origins_with_empty_additional_origins(self):
        """Test CORS origins when additional_origins is empty."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "https://app.example.com"
        settings.get_additional_cors_origins.return_value = []
        
        origins = get_cors_origins(settings)
        
        assert len(origins) == 1
        assert "https://app.example.com" in origins

    def test_get_cors_origins_with_invalid_frontend_base_url(self):
        """Test CORS origins when frontend_base_url is invalid."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "not-a-valid-url"
        settings.get_additional_cors_origins.return_value = [
            "https://example.com"
        ]
        
        origins = get_cors_origins(settings)
        
        # Invalid frontend_base_url should be filtered out
        assert len(origins) == 1
        assert "https://example.com" in origins
        assert "not-a-valid-url" not in origins

    def test_get_cors_origins_with_ports(self):
        """Test CORS origins with ports in URLs."""
        settings = Mock(spec=Settings)
        settings.frontend_base_url = "http://localhost:3000"
        settings.get_additional_cors_origins.return_value = [
            "https://example.com:8080",
            "http://localhost:8000"
        ]
        
        origins = get_cors_origins(settings)
        
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "https://example.com:8080" in origins
        assert "http://localhost:8000" in origins

