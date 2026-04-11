import uvicorn
import os
from pathlib import Path

def run():
    print("🚀 Starten van D-OmniTwin Development Server met geoptimaliseerde reload...")
    
    # Gebruik uvicorn.run met specifieke reload settings
    # Dit voorkomt dat uvicorn de tienduizenden bestanden in admin-panel/node_modules scant.
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        # Alleen deze mappen/bestanden in de gaten houden voor server restarts
        reload_includes=[
            "main.py",
            "routers/*.py",
            "services/*.py",
            "src/*.py",
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
            "exports/*"
        ],
        log_level="info"
    )

if __name__ == "__main__":
    run()
