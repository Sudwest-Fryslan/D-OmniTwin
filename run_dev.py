import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env zodat LOG_LEVEL beschikbaar is
load_dotenv(Path(__file__).resolve().parent / '.env')

def run():
    print("🚀 Starten van D-OmniTwin Development Server met geoptimaliseerde reload...")
    
    # LOG_LEVEL uit .env koppelen aan uvicorn (was hardcoded "info")
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()
    
    # Gebruik uvicorn.run met specifieke reload settings
    # Dit voorkomt dat uvicorn de tienduizenden bestanden in admin-panel/node_modules scant.
    
    uvicorn.run(
        "omnitwin.main:app",
        app_dir="src",  # pakket omnitwin staat in src/ (#182)
        host="0.0.0.0",
        port=8000,
        reload=True,
        # Alleen deze mappen/bestanden in de gaten houden voor server restarts
        reload_includes=[
            "src/omnitwin/*.py",
            "src/omnitwin/routers/*.py",
            "src/omnitwin/services/*.py",
            "templates/*.html",
            "static/js/*.js",
            "static/css/*.css",
        ],
        # Expliciet deze zware mappen negeren
        reload_excludes=[
            "admin-panel/*", 
            "data/*",
            "*/__pycache__/*",
            "*.pyc",
            "*.log",
            "logs/*",
            "exports/*"
        ],
        log_level=log_level
    )

if __name__ == "__main__":
    run()
