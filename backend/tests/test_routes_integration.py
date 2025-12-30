"""
Integration tests for refactored routes.
Tests all router modules to ensure they work correctly after extraction.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCoreRoutes:
    """Test core routes that remain in main.py"""
    
    def test_api_info(self):
        """Test /api endpoint"""
        response = client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Visualizd API"
        assert data["version"] == "0.1.0"
    
    def test_health_check(self):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    
    def test_debug_users(self):
        """Test /api/debug/users endpoint"""
        response = client.get("/api/debug/users")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "users" in data
        assert isinstance(data["users"], list)


class TestStaticRoutes:
    """Test static file serving routes"""
    
    def test_index_html(self):
        """Test / serves index.html"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_index_html_direct(self):
        """Test /index.html"""
        response = client.get("/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_magic_login_route(self):
        """Test /magic-login serves index.html (SPA routing)"""
        response = client.get("/magic-login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_config_js(self):
        """Test /config.js serves dynamic config"""
        response = client.get("/config.js")
        assert response.status_code == 200
        assert "application/javascript" in response.headers["content-type"]
        assert "window.APP_CONFIG" in response.text
        assert "API_BASE_URL" in response.text
    
    def test_styles_css(self):
        """Test /styles.css"""
        response = client.get("/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
    
    def test_header_js(self):
        """Test /header.js"""
        response = client.get("/header.js")
        assert response.status_code == 200
        assert "application/javascript" in response.headers["content-type"]
    
    def test_auth_js(self):
        """Test /auth.js"""
        response = client.get("/auth.js")
        assert response.status_code == 200
        assert "application/javascript" in response.headers["content-type"]


class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_magic_link_request_invalid_email(self):
        """Test magic link request with invalid email"""
        response = client.post("/api/auth/magic-link/request", json={
            "email": "invalid-email"
        })
        assert response.status_code == 400
    
    def test_magic_link_request_unauthorized_domain(self):
        """Test magic link request with unauthorized domain"""
        response = client.post("/api/auth/magic-link/request", json={
            "email": "test@unauthorized-domain.com"
        })
        # Should return 403 for unauthorized domain
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()
    
    def test_magic_link_verify_missing_token(self):
        """Test magic link verify with missing token"""
        response = client.post("/api/auth/magic-link/verify", json={
            "email": "test@example.com",
            "token": ""
        })
        assert response.status_code == 400
    
    def test_google_oauth_not_configured(self):
        """Test Google OAuth endpoints return 501 when not configured"""
        response = client.get("/api/auth/google/init")
        assert response.status_code == 501
    
    def test_auth_me_without_token(self):
        """Test /api/auth/me without authentication"""
        response = client.get("/api/auth/me")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden


class TestClientRoutes:
    """Test client and insight routes"""
    
    def test_list_clients(self):
        """Test GET /api/clients"""
        response = client.get("/api/clients")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_nonexistent_client(self):
        """Test GET /api/clients/{id} with invalid ID"""
        from uuid import uuid4
        fake_id = uuid4()
        response = client.get(f"/api/clients/{fake_id}")
        assert response.status_code == 404
    
    def test_list_insights_without_auth(self):
        """Test insights require authentication"""
        from uuid import uuid4
        fake_id = uuid4()
        response = client.get(f"/api/clients/{fake_id}/insights")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden


class TestDataSourceRoutes:
    """Test data source routes"""
    
    def test_list_data_sources(self):
        """Test GET /api/data-sources"""
        response = client.get("/api/data-sources")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_nonexistent_data_source(self):
        """Test GET /api/data-sources/{id} with invalid ID"""
        from uuid import uuid4
        fake_id = uuid4()
        response = client.get(f"/api/data-sources/{fake_id}")
        assert response.status_code == 404
    
    def test_get_nonexistent_data_source_questions(self):
        """Test GET /api/data-sources/{id}/questions with invalid ID"""
        from uuid import uuid4
        fake_id = uuid4()
        response = client.get(f"/api/data-sources/{fake_id}/questions")
        assert response.status_code == 404


class TestVOCRoutes:
    """Test VOC routes"""
    
    def test_get_voc_data(self):
        """Test GET /api/voc/data"""
        response = client.get("/api/voc/data")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_voc_questions(self):
        """Test GET /api/voc/questions"""
        response = client.get("/api/voc/questions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_voc_sources(self):
        """Test GET /api/voc/sources"""
        response = client.get("/api/voc/sources")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_voc_projects(self):
        """Test GET /api/voc/projects"""
        response = client.get("/api/voc/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_voc_clients(self):
        """Test GET /api/voc/clients"""
        response = client.get("/api/voc/clients")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_upload_csv_without_auth(self):
        """Test CSV upload requires authentication"""
        response = client.post("/api/voc/upload-csv")
        assert response.status_code in [401, 403, 422]  # Auth required or validation error


class TestDimensionRoutes:
    """Test dimension summary routes"""
    
    def test_dimension_summary_nonexistent(self):
        """Test dimension summary with nonexistent data"""
        from uuid import uuid4
        fake_client = uuid4()
        response = client.get(f"/api/dimensions/{fake_client}/test_source/test_ref/summary")
        # Should return 404 or error about no data
        assert response.status_code in [404, 500]


class TestFounderAdminRoutes:
    """Test founder admin routes (require founder auth)"""
    
    def test_founder_users_without_auth(self):
        """Test founder users endpoint requires auth"""
        response = client.get("/api/founder/users")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden
    
    def test_authorized_domains_without_auth(self):
        """Test authorized domains endpoint requires auth"""
        response = client.get("/api/founder/authorized-domains")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden
    
    def test_founder_admin_voc_data_without_auth(self):
        """Test founder admin VOC data requires auth"""
        response = client.get("/api/founder-admin/voc-data")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden
    
    def test_database_tables_without_auth(self):
        """Test database management requires auth"""
        response = client.get("/api/founder/database/tables")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden

