from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html # Local Swagger UI
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db, engine
from dotenv import load_dotenv
from pathlib import Path
import os
import time

from services.logging_service import AppLogger, init_logging, shutdown_logging

# Load environment variables
project_root = Path(__file__).resolve().parent
load_dotenv(project_root / '.env')

# Import routers
from routers import gebiedsmonitor, kompas, admin, gemeenten, dashboard, visualisatie

app = FastAPI(
    title="D-OmniTwin API",
    description="Backend API voor D-OmniTwin: The Omni Twin - Digitale spiegel van de fysieke leefomgeving",
    version="1.5.0",  # Visualisatie Standaard
    docs_url=None, # Disable default docs (served locally)
    redoc_url=None # Disable default redoc (served locally)
)

# ============================================================================
# SECURITY: Headers Middleware
# ============================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy - STRICT LOCAL ONLY
        # Required for: Mapbox GL, D3.js, deck.gl, Chart.js
        # Local Swagger UI assets (no external CDNs needed for docs)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://api.mapbox.com https://d3js.org https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://api.mapbox.com https://cdn.jsdelivr.net https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.mapbox.com https://*.tiles.mapbox.com https://events.mapbox.com wss://*.mapbox.com https://data.3dbag.nl https://api.3dbag.nl; "
            "worker-src 'self' blob:; "
            "child-src 'self' blob:; "
            "frame-src 'self';"
        )
        
        # XSS and Clickjacking Protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


# ============================================================================
# LOGGING: Request Logging Middleware (Sprint 17A)
# ============================================================================
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logt elke HTTP request naar AppLogger (category=API).
    
    Uitsluitingen: /static/*, /health (noisy, geen diagnostische waarde).
    Niveau: INFO voor 2xx/3xx, WARNING voor 4xx, ERROR voor 5xx.
    """
    
    # Paden die niet gelogd worden
    _SKIP_PREFIXES = ("/static/", "/health")
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip noisy paden
        if any(path.startswith(prefix) for prefix in self._SKIP_PREFIXES):
            return await call_next(request)
        
        start = time.time()
        
        try:
            response = await call_next(request)
        except Exception:
            # Onverwachte crash: log als ERROR, laat exception door
            elapsed_ms = int((time.time() - start) * 1000)
            ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
            AppLogger.error(
                f"{request.method} {path} → 500 ({elapsed_ms}ms)",
                category="API",
                ip_address=ip,
                endpoint=path,
                response_time_ms=elapsed_ms,
            )
            raise
        
        elapsed_ms = int((time.time() - start) * 1000)
        status = response.status_code
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        
        # Bepaal log niveau op basis van status code
        if status >= 500:
            log_fn = AppLogger.error
        elif status >= 400:
            log_fn = AppLogger.warning
        else:
            log_fn = AppLogger.info
        
        log_fn(
            f"{request.method} {path} → {status} ({elapsed_ms}ms)",
            category="API",
            ip_address=ip,
            endpoint=path,
            response_time_ms=elapsed_ms,
        )
        
        return response


# Add security headers middleware FIRST
app.add_middleware(SecurityHeadersMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# ============================================================================
# SECURITY: CORS Lockdown
# ============================================================================
# Get allowed origins from environment (comma-separated)
cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:8000')
cors_origins = [origin.strip() for origin in cors_origins_str.split(',')]

# In debug mode, also allow common dev origins
if os.getenv('DEBUG', 'false').lower() == 'true':
    dev_origins = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:3000']
    cors_origins.extend([o for o in dev_origins if o not in cors_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # 🔒 LOCKED DOWN (was: ["*"])
    # In debug mode: accepteer ngrok/tunnel origins automatisch
    allow_origin_regex=r"https://.*\.ngrok-free\.dev" if os.getenv('DEBUG', 'false').lower() == 'true' else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# ============================================================================
# App Configuration (from environment)
# ============================================================================
mapbox_token = os.getenv('MAPBOX_TOKEN')
mapbox_style = os.getenv('MAPBOX_STYLE', 'mapbox://styles/mapbox/light-v10')
debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'

# Register routers
app.include_router(gebiedsmonitor.router)
app.include_router(kompas.router)
app.include_router(gemeenten.router)
from routers import auth
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(visualisatie.router)
from routers import kaart_v2
app.include_router(kaart_v2.router)
from routers import report
app.include_router(report.router)
from routers import llm_prompts, data_controle, ai_search, chat, bag3d, omgevingsvisie
app.include_router(llm_prompts.router)
app.include_router(data_controle.router)
app.include_router(ai_search.router)
app.include_router(chat.router)
app.include_router(bag3d.router)
app.include_router(omgevingsvisie.router)

@app.on_event("startup")
async def startup_event():
    """Startup checks and logging."""
    # Initialiseer logging stack (file handler + async DB queue + config cache)
    await init_logging()
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        AppLogger.info("Database connection established successfully", category="SERVER")
        AppLogger.info("Gebiedsmonitor API registered at /api/gebiedsmonitor", category="SERVER")
        AppLogger.info("Kompas API registered at /api/kompas", category="SERVER")
        AppLogger.info("Gemeenten API registered at /api/gemeenten", category="SERVER")
        AppLogger.info(f"CORS origins: {cors_origins}", category="SERVER")
        AppLogger.info(f"Debug mode: {debug_mode}", category="SERVER")
        AppLogger.info("Security headers middleware active", category="SERVER")
        AppLogger.info("Request logging middleware active", category="SERVER")
        AppLogger.info("Frontend available at http://localhost:8000/", category="SERVER")
    except Exception as e:
        AppLogger.error(f"Database connection failed: {e}", category="SERVER")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown — flush log queue."""
    await shutdown_logging()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the frontend application."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mapbox_token": mapbox_token,
        "mapbox_style": mapbox_style
    })

# ============================================================================
# React SPA Support for Admin Panel
# ============================================================================
@app.get("/admin/static/{file_path:path}", include_in_schema=False)
async def serve_admin_static(request: Request, file_path: str):
    """Serve static assets directly for the React Admin Panel, bypassing the catchall."""
    # We map whatever /admin/static/js/... it asks for directly to /static/admin-panel/static/js/...
    actual_path = os.path.join("static", "admin-panel", "static", file_path)
    if os.path.exists(actual_path):
        from fastapi.responses import FileResponse
        return FileResponse(actual_path)
    return HTMLResponse(content="Not Found", status_code=404)

@app.get("/admin/{catchall:path}", response_class=HTMLResponse)
async def serve_admin_spa(request: Request, catchall: str):
    """Fallback route for React Router in the Admin Panel."""
    # Serve static assets that aren't in /static/ directly from the root if they exist 
    # (e.g., manifest.json, favicon.ico which React places in the root build folder)
    root_asset_path = os.path.join("static", "admin-panel", catchall)
    if catchall and "." in catchall and os.path.exists(root_asset_path):
        from fastapi.responses import FileResponse
        return FileResponse(root_asset_path)

    # Build processes put index.html in the static folder under admin-panel
    index_path = os.path.join("static", "admin-panel", "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return HTMLResponse(content=f.read())
    # Development fallback
    return HTMLResponse(content="<h1>Admin Panel Niet Gebouwd</h1><p>Draai `npm run build` in de admin-panel map.</p>", status_code=404)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve custom Swagger UI with local assets."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - D-OmniTwin API Docs",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
    )

@app.get("/api")
def api_root():
    """API root endpoint."""
    return {
        "message": "Welcome to D-OmniTwin API", 
        "status": "running",
        "version": "1.2.0",
        "security": "🔒 CORS locked, Security headers active",
        "apis": {
            "gebiedsmonitor": "/api/gebiedsmonitor",
            "kompas": "/api/kompas",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "database": "online", 
            "api": "online", 
            "version": "1.2.0",
            "security": "headers_active"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# reload trigger 2026-03-15 15:58
