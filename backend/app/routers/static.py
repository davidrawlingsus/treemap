"""
Static file serving routes.
"""
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, Response

from app.utils import find_frontend_path

router = APIRouter()

# Find frontend path - calculate from routers/static.py location
# routers/static.py -> app/routers/static.py -> backend/app/main.py
main_file_path = Path(__file__).parent.parent / "main.py"
frontend_path = find_frontend_path(main_file_path)

if (frontend_path / "index.html").exists():
    @router.get("/", response_class=FileResponse)
    def serve_index():
        """Serve the frontend index.html"""
        return FileResponse(frontend_path / "index.html")
    
    @router.get("/magic-login", response_class=FileResponse)
    def serve_magic_login():
        """Serve the magic login page (same as index for SPA routing)"""
        return FileResponse(frontend_path / "index.html")
    
    @router.get("/index.html", response_class=FileResponse)
    def serve_index_html():
        """Serve the frontend index.html"""
        return FileResponse(frontend_path / "index.html")
    
    @router.get("/config.js")
    def serve_config(request: Request):
        """Serve dynamic config.js with API URL based on request origin"""
        import os
        
        # Get API URL from environment variable if set (for Railway/production)
        api_url = os.getenv("API_BASE_URL")
        
        # If not set, use the request URL (where the backend is running)
        # This ensures the API_BASE_URL points to the backend server
        if not api_url:
            scheme = request.url.scheme
            host = request.headers.get("host", "localhost:8000")
            api_url = f"{scheme}://{host}"
        
        # Default fallback for local development
        if not api_url or api_url == "http://" or api_url == "https://":
            api_url = "http://localhost:8000"
        
        config_content = f"window.APP_CONFIG = {{ API_BASE_URL: '{api_url}' }};"
        return Response(content=config_content, media_type="application/javascript")
    
    @router.get("/styles.css")
    def serve_styles():
        """Serve styles.css"""
        file_path = frontend_path / "styles.css"
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
            return Response(content=content, media_type="text/css")
        raise HTTPException(status_code=404, detail="File not found")
    
    @router.get("/header.js")
    def serve_header():
        """Serve header.js"""
        file_path = frontend_path / "header.js"
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
            return Response(content=content, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="File not found")

    @router.get("/auth.js")
    def serve_auth_js():
        """Serve auth.js"""
        file_path = frontend_path / "auth.js"
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
            return Response(content=content, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="File not found")

if (frontend_path / "founder_admin.html").exists():
    @router.get("/founder_admin", response_class=FileResponse)
    def serve_founder_admin():
        """Serve the founder admin page"""
        return FileResponse(frontend_path / "founder_admin.html")
    
    @router.get("/founder_admin.html", response_class=FileResponse)
    def serve_founder_admin_html():
        """Serve the founder admin page"""
        return FileResponse(frontend_path / "founder_admin.html")

if (frontend_path / "founder_impersonation.html").exists():
    @router.get("/founder_impersonation", response_class=FileResponse)
    def serve_founder_impersonation():
        """Serve the founder impersonation helper page"""
        return FileResponse(frontend_path / "founder_impersonation.html")

    @router.get("/founder_impersonation.html", response_class=FileResponse)
    def serve_founder_impersonation_html():
        """Serve the founder impersonation helper page"""
        return FileResponse(frontend_path / "founder_impersonation.html")

if (frontend_path / "founder_database.html").exists():
    @router.get("/founder_database", response_class=FileResponse)
    def serve_founder_database():
        """Serve the founder database management page"""
        return FileResponse(frontend_path / "founder_database.html")
    
    @router.get("/founder_database.html", response_class=FileResponse)
    def serve_founder_database_html():
        """Serve the founder database management page"""
        return FileResponse(frontend_path / "founder_database.html")

if (frontend_path / "add.html").exists():
    @router.get("/add", response_class=FileResponse)
    def serve_add():
        """Serve the add data page"""
        return FileResponse(frontend_path / "add.html")
    
    @router.get("/add.html", response_class=FileResponse)
    def serve_add_html():
        """Serve the add data page"""
        return FileResponse(frontend_path / "add.html")

if (frontend_path / "choose-data-source.html").exists():
    @router.get("/choose-data-source", response_class=FileResponse)
    def serve_choose_data_source():
        """Serve the choose data source page"""
        return FileResponse(frontend_path / "choose-data-source.html")
    
    @router.get("/choose-data-source.html", response_class=FileResponse)
    def serve_choose_data_source_html():
        """Serve the choose data source page"""
        return FileResponse(frontend_path / "choose-data-source.html")

if (frontend_path / "founder_voc_editor.html").exists():
    @router.get("/founder_voc_editor", response_class=FileResponse)
    def serve_founder_voc_editor():
        """Serve the founder VOC editor page"""
        return FileResponse(frontend_path / "founder_voc_editor.html")
    
    @router.get("/founder_voc_editor.html", response_class=FileResponse)
    def serve_founder_voc_editor_html():
        """Serve the founder VOC editor page"""
        return FileResponse(frontend_path / "founder_voc_editor.html")

if (frontend_path / "founder_authorized_domains.html").exists():
    @router.get("/founder_authorized_domains", response_class=FileResponse)
    def serve_founder_authorized_domains():
        """Serve the founder authorized domains page"""
        return FileResponse(frontend_path / "founder_authorized_domains.html")
    
    @router.get("/founder_authorized_domains.html", response_class=FileResponse)
    def serve_founder_authorized_domains_html():
        """Serve the founder authorized domains page"""
        return FileResponse(frontend_path / "founder_authorized_domains.html")

