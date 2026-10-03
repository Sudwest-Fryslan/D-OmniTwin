from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html # Local Swagger UI
from sqlalchemy.orm import Session
from sqlalchemy import event, text
from omnitwin.config import CORS_ALLOW_HEADERS, STATEMENT_TIMEOUT_MS, instellingen
from omnitwin.database import get_db, engine
from omnitwin.statisch import StatischeBestanden, cache_control
import os
import time

from omnitwin.services.logging_service import AppLogger, init_logging, shutdown_logging
from omnitwin.services.log_cleanup_service import start_cleanup_scheduler, stop_cleanup_scheduler

# Import routers
from omnitwin.routers import gebiedsmonitor, kompas, admin, dashboard, visualisatie
from omnitwin.version import __version__

app = FastAPI(
    title="D-OmniTwin API",
    description="Backend API voor D-OmniTwin: The Omni Twin - Digitale spiegel van de fysieke leefomgeving",
    version=__version__,  # bron: VERSION (zie docs/9-beheer/releasebeleid.md)
    docs_url=None, # Disable default docs (served locally)
    redoc_url=None # Disable default redoc (served locally)
)

# Grens per databasequery van de webapp (#203). Alleen hier, niet in database.py:
# db-init, migraties en ETL-scripts gebruiken dezelfde engine en mogen langer duren.
@event.listens_for(engine, "connect")
def _zet_statement_timeout(dbapi_connection, _record):
    with dbapi_connection.cursor() as cursor:
        cursor.execute(f"SET statement_timeout = {int(STATEMENT_TIMEOUT_MS)}")
    dbapi_connection.commit()  # anders draait de rollback bij teruggave aan de pool de SET terug

# Centrale foutafhandeling (#203): details in de log, naar buiten een generieke
# melding met correlatie-id; ongeldige invoer in de database → 422, conflict → 409
from omnitwin.fouten import registreer_foutafhandeling
registreer_foutafhandeling(app)

# ============================================================================
# SECURITY: Headers Middleware
# ============================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.

    Terugval voor `python run_dev.py` zonder Traefik. In de Docker-stack zijn de
    headers uit deploy/traefik/dynamic.yml leidend (ook voor /api/data en
    /api/geo); Traefik overschrijft deze waarden.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy - STRICT LOCAL ONLY
        # MapLibre GL, D3.js, deck.gl, Chart.js en het lettertype Inter worden zelf gehost
        # onder /static/vendor (#117); geen CDN- of font-domeinen meer nodig.
        # Externe verbindingen zijn alleen data-API's (basiskaart en kaartlagen: PDOK).
        # Local Swagger UI assets (no external CDNs needed for docs)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.3dbag.nl https://service.pdok.nl https://api.pdok.nl; "
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
    # /api/viewer/toegang: forwardAuth van Traefik bij elk verzoek naar /api/data en /api/geo (#266)
    _SKIP_PREFIXES = ("/static/", "/health", "/api/viewer/toegang")
    
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


# Toegang tot de viewer (#266, ADR 0009): bij VIEWER_TOEGANG=inloggen alleen met rol lezer of
# beheerder. Binnenste middleware, zodat redirects en 401's ook de headers en de log krijgen.
from omnitwin import viewer_toegang
app.add_middleware(viewer_toegang.ViewerToegangMiddleware)

# Add security headers middleware FIRST
app.add_middleware(SecurityHeadersMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# ============================================================================
# SECURITY: CORS Lockdown
# ============================================================================
# Alleen de origins uit CORS_ORIGINS (kommagescheiden). De eigen site en de
# Vite-devserver (proxy) hebben geen CORS nodig; geen wildcards (#203).
cors_origins = list(instellingen().cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=list(CORS_ALLOW_HEADERS),
)

# Mount static files
app.mount("/static", StatischeBestanden(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["app_version"] = __version__

# Register routers
app.include_router(gebiedsmonitor.router)
app.include_router(kompas.router)

from omnitwin.routers import auth
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(visualisatie.router)
app.include_router(visualisatie.admin_router)
from omnitwin.routers import report
app.include_router(report.router)
from omnitwin.routers import data_controle, ai_search, chat, bag3d, log_viewer, externe_lagen
app.include_router(data_controle.router)
app.include_router(ai_search.router)
app.include_router(chat.router)
app.include_router(bag3d.router)
app.include_router(log_viewer.router)
app.include_router(externe_lagen.router)
app.include_router(externe_lagen.admin_router)
from omnitwin.routers import oidc_ik
app.include_router(oidc_ik.router)  # GET /api/oidc/ik: token controleren (#205)
from omnitwin.routers import organisatie
app.include_router(organisatie.router)  # GET /api/organisatie: eigen organisatie (#231)

# forwardAuth van Traefik voor /api/data en /api/geo (#266): 204 = door, anders 401/403
app.add_api_route(viewer_toegang.CONTROLE_PAD, viewer_toegang.controleer, methods=["GET", "HEAD"],
                  include_in_schema=False)

# Laad-API /api/laden/v1 (#205): eigen spec, API-Version, Problem Details, achtergrondverwerking
from omnitwin.routers import laden as laden_api
laden_api.registreer(app)

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
        AppLogger.info(f"CORS origins: {cors_origins}", category="SERVER")
        AppLogger.info(f"Cookie Secure: {instellingen().cookie_secure}", category="SERVER")
        AppLogger.info("Security headers middleware active", category="SERVER")
        AppLogger.info("Request logging middleware active", category="SERVER")
        AppLogger.info("Frontend available at http://localhost:8000/", category="SERVER")
    except Exception as e:
        AppLogger.error(f"Database connection failed: {e}", category="SERVER")

    # X-Admin-Key alleen met een echte key; een lege of voorbeeldwaarde geeft geen toegang (#65)
    from omnitwin.routers.auth import geldige_admin_api_key
    if geldige_admin_api_key() is None:
        AppLogger.warning("ADMIN_API_KEY is leeg of een voorbeeldwaarde: X-Admin-Key is uitgeschakeld", category="AUTH")

    # Inloggen (#251): met OIDC alleen via Keycloak, lokale accounts alleen als noodtoegang
    if instellingen().noodtoegang:
        AppLogger.warning("Noodtoegang aan: lokale accounts kunnen inloggen naast Keycloak (LOKAAL_INLOGGEN=true). "
                          "Zet dit na gebruik weer uit.", category="AUTH")
    elif instellingen().oidc_issuer:
        AppLogger.info("Inloggen in de beheeromgeving via Keycloak; lokaal inloggen staat uit", category="AUTH")

    # Viewer (#266) en soort omgeving (#245)
    ins = instellingen()
    if ins.viewer_dicht:
        AppLogger.info("Viewer alleen na inloggen (VIEWER_TOEGANG=inloggen, of een onbekende waarde)",
                       category="AUTH")
        if not ins.oidc_issuer:
            AppLogger.warning("VIEWER_TOEGANG=inloggen zonder Keycloak (OIDC_ISSUER leeg): alleen een lokale "
                              "beheerder heeft toegang tot de viewer", category="AUTH")
    if ins.demo:
        AppLogger.warning("Demo-omgeving (OMNITWIN_OMGEVING=demo): standaardaccounts met bekende wachtwoorden. "
                          "Niet voor productie.", category="AUTH")

    # Start dagelijkse log cleanup
    start_cleanup_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown — flush log queue + stop cleanup scheduler."""
    await stop_cleanup_scheduler()
    await shutdown_logging()

@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    """Serve the frontend application. Footer-logo's uit de organisatie-instelling (#231).
    In de kop: inloggen/uitloggen en de gebruikersnaam als Keycloak aan staat (#266), en de
    demobalk bij OMNITWIN_OMGEVING=demo (#245)."""
    from omnitwin.services.organisatie import lees_organisatie, thema_css
    organisatie = lees_organisatie(db)
    ins = instellingen()
    gebruiker = getattr(request.state, "viewer_gebruiker", None)
    if gebruiker is None and request.cookies.get("session_token"):
        try:
            gebruiker = viewer_toegang.gebruiker_van(request)
        except Exception:  # provider onbereikbaar: de kaart toont dan gewoon de inlogknop
            gebruiker = None
    account = {
        "oidc": bool(ins.oidc_issuer),
        "naam": (gebruiker or {}).get("username") if gebruiker and gebruiker.get("type") != "api_key" else None,
        "inloggen": viewer_toegang.login_adres("/"),
    }
    return templates.TemplateResponse("index.html", {
        "request": request, "organisatie": organisatie, "thema_css": thema_css(organisatie),
        "account": account, "demo": ins.demo},
        headers={"Cache-Control": "no-cache"})

# ============================================================================
# React SPA Support for Admin Panel
# ============================================================================
@app.get("/admin/{catchall:path}", response_class=HTMLResponse)
async def serve_admin_spa(request: Request, catchall: str):
    """Fallback route for React Router in the Admin Panel."""
    # Serve build files if they exist: Vite-assets (/admin/assets/...) and
    # public-bestanden zoals manifest.json en favicon.ico in de root van de build.
    root_asset_path = os.path.join("static", "admin-panel", catchall)
    if catchall and "." in catchall and os.path.exists(root_asset_path):
        from fastapi.responses import FileResponse
        return FileResponse(root_asset_path, headers={"Cache-Control": cache_control(f"admin-panel/{catchall}")})
    if catchall.startswith("assets/"):
        # Ontbrekend build-asset: 404 i.p.v. index.html (zoals eerder /admin/static/)
        return HTMLResponse(content="Not Found", status_code=404)

    # Build processes put index.html in the static folder under admin-panel
    index_path = os.path.join("static", "admin-panel", "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return HTMLResponse(content=f.read(), headers={"Cache-Control": "no-cache"})
    # Development fallback
    return HTMLResponse(content="<h1>Admin Panel Niet Gebouwd</h1><p>Draai `npm run build` in de admin-panel map.</p>", status_code=404)

@app.get("/.well-known/security.txt", include_in_schema=False)
async def security_txt():
    """security.txt (RFC 9116): waar je kwetsbaarheden meldt."""
    from fastapi.responses import FileResponse
    return FileResponse(
        os.path.join("static", ".well-known", "security.txt"),
        media_type="text/plain; charset=utf-8",
    )

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve custom Swagger UI with local assets."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - D-OmniTwin API Docs",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/admin-panel/favicon.ico",  # lokaal i.p.v. fastapi.tiangolo.com (CSP)
    )

@app.get("/api")
def api_root():
    """API root endpoint."""
    return {
        "message": "Welcome to D-OmniTwin API", 
        "status": "running",
        "version": __version__,
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
    """Health check endpoint. Een databasefout gaat naar de centrale foutafhandeling
    (500 met correlatie-id, details alleen in de log)."""
    db.execute(text("SELECT 1"))
    return {
        "database": "online",
        "api": "online",
        "version": __version__,
        "security": "headers_active"
    }

# reload trigger 2026-03-15 15:58
