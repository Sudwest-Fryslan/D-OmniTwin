# Gids: Swagger UI Assets Lokaal Hosten voor Maximale Security

Door Swagger UI assets (CSS en JS) lokaal te serveren, hoef je geen externe domeinen zoals `cdn.jsdelivr.net` toe te voegen aan je Content Security Policy (CSP). Dit elimineert het risico op een **CDN compromise** en zorgt ervoor dat je API‑documentatie ook werkt zonder internetverbinding.

---

## Stap 1: Download de Assets

Je hebt vier bestanden nodig van de officiële Swagger UI distributie. Je kunt deze handmatig downloaden of via een script in een map genaamd `static/` plaatsen:

- `swagger-ui-bundle.js`
- `swagger-ui-standalone-preset.js`
- `swagger-ui.css`
- `favicon.png` *(optioneel)*

---

## Stap 2: Implementatie in FastAPI

Hieronder zie je hoe je de standaard `/docs` route overschrijft om de lokale bestanden te gebruiken:

```python
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

app = FastAPI(docs_url=None, redoc_url=None)  # Schakel standaard docs uit

# Mount de static map zodat de browser de bestanden kan vinden
app.mount("/static", StaticFiles(directory="static"), name="static")

# Beveiligingsheaders Middleware met strikte CSP
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Merk op: we laten externe CDN's nu weg!
        csp = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # 'unsafe-inline' is vaak nodig voor swagger styling
            "script-src 'self'; "
            "img-src 'self' data:;"
        )

        response.headers["Content-Security-Policy"] = csp
        return response

app.add_middleware(SecurityHeadersMiddleware)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,

        # Hier wijzen we naar onze LOKALE bestanden:
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )
```

---

## Waarom dit "slim" is

### Strikte CSP

Je `style-src` en `script-src` staan nu op `'self'`. Dit betekent dat de browser weigert code uit te voeren die niet van jouw eigen server komt.

### Geen Tracking

Geen externe partijen die kunnen zien wie jouw documentatie bezoekt.

### Snelheid

Lokale bestanden laden vaak sneller dan bestanden die van een extern CDN moeten komen, omdat er geen extra DNS lookup nodig is.

### Betrouwbaarheid

Als `jsdelivr` offline gaat (zeldzaam, maar het gebeurt), blijft jouw documentatie gewoon werken.

---

## Extra tip: Automatisering

Als je dit in een professionele CI/CD pipeline doet, kun je de assets laten downloaden tijdens de build‑stap van je Docker container. Zo hoef je de bestanden niet in je Git‑repository op te slaan, maar zijn ze wel altijd lokaal aanwezig in je productie‑omgeving.

Voorbeeld Dockerfile snippet:

```dockerfile
RUN mkdir -p /app/static && \
    curl -L https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js -o /app/static/swagger-ui-bundle.js && \
    curl -L https://unpkg.com/swagger-ui-dist/swagger-ui-standalone-preset.js -o /app/static/swagger-ui-standalone-preset.js && \
    curl -L https://unpkg.com/swagger-ui-dist/swagger-ui.css -o /app/static/swagger-ui.css
```

---

## Security Samenvatting

| Aspect | CDN Gebruik | Lokaal Hosten |
|---|---|---|
| CSP complexiteit | Hoog | Laag |
| Supply chain risico | Aanwezig | Geminimaliseerd |
| Offline beschikbaar | Nee | Ja |
| Privacy | Lager | Hoger |
| Performance | Goed | Vaak beter |

---

## Conclusie

Het lokaal hosten van Swagger UI assets is een **best practice** binnen beveiligde omgevingen, met name binnen overheden, enterprise‑netwerken en air‑gapped infrastructuren. Het vermindert afhankelijkheden, verhoogt privacy en maakt een strengere Content Security Policy mogelijk zonder functionaliteitsverlies.

