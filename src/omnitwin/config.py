"""
Configuratie van de backend: alle omgevingsvariabelen op één plek (#130, #203).

Elke instelling komt uit een omgevingsvariabele (of `.env` in de root van de
repository) met dezelfde naam en standaardwaarde als voorheen. `instellingen()`
leest de omgeving bij elke aanroep opnieuw, zodat een gewijzigde omgeving
(tests, scripts) direct doorwerkt; het is goedkoop genoeg om per verzoek te doen.

Nieuw in 0.2.1 (#203), los van `DEBUG` (dat is vervallen):
- COOKIE_SECURE    auto (standaard) | true | false. `auto`: het sessiecookie krijgt
                   `Secure` als het verzoek via HTTPS binnenkomt (ook achter Traefik,
                   via X-Forwarded-Proto). Achter een eigen TLS-proxy die naar Traefik
                   over HTTP doorstuurt: zet `true`.
- CORS_ORIGINS     expliciete, kommagescheiden lijst. Geen wildcard meer voor
                   ngrok of localhost-varianten.
- LLM_RATE_LIMIT   maximaal aantal verzoeken per minuut per IP-adres op de
                   LLM-routes (chat, narratives); 0 = geen limiet.

Privacy (#264):
- LOG_BEWAAR_DAGEN     logregels in app_logs (alle niveaus) ouder dan dit worden verwijderd;
                       DEBUG na hoogstens 7 dagen. Standaard 30.
- LOG_IP_BEWAAR_DAGEN  daarna wordt het IP-adres in app_logs ingekort (IPv4 /24, IPv6 /48).
                       Standaard 7.
- TRUSTED_PROXIES      kommagescheiden adressen/netwerken (CIDR) waarvan X-Forwarded-For
                       vertrouwd wordt (Traefik). Standaard loopback en de privé-reeksen
                       (Docker-netwerken); leeg = nooit. Zie omnitwin.grenzen.client_ip.

Laad-API (/api/laden/v1, #205), zie omnitwin.laden:
- LEVERINGEN_DIR   map voor de ruwe leveringen (volume `leveringen`), onveranderlijk
- LADEN_MAX_MB     bodylimiet van een levering (JSON: een tiende, minimaal 1 MB)
- LADEN_WACHT_SECONDEN   time-out van `wacht=true`
- LADEN_BEWAAR_VERSIES, LADEN_BEWAAR_DAGEN, LADEN_BEWAAR_AFGEKEURD_DAGEN   bewaartermijn
OIDC (#205, tokens controleren in de nieuwe API's, zie omnitwin/oidc.py):
- OIDC_ISSUER      issuer zoals in de tokens (bijv. http://localhost/auth/realms/omnitwin);
                   leeg = OIDC uit (routes met vereis_rol geven 503).
- OIDC_AUDIENCE    vereiste `aud`, standaard omnitwin-api; ook de client in resource_access
                   waarvan de client-rollen meetellen.
- OIDC_JWKS_URL    optioneel; standaard via discovery (.well-known/openid-configuration).
- OIDC_INTERN_URL  optioneel; intern adres van de issuer (achter Traefik:
                   http://keycloak:8080/auth/realms/omnitwin). Discovery en JWKS komen dan
                   daarvandaan; `iss` wordt nog steeds tegen OIDC_ISSUER gecontroleerd.
Inloggen in de beheeromgeving via OIDC (#251, ADR 0008, zie omnitwin/oidc_login.py):
- OIDC_CLIENT_ID   client waarmee mensen inloggen (authorization code + PKCE), standaard
                   omnitwin-web.
- OIDC_SCOPE       extra scopes naast `openid profile`, met spaties. Entra ID: `offline_access`
                   (refresh token) en de scope van de eigen API (`api://<client-id>/<scope>`),
                   zodat het access token voor deze app is en de app-rollen bevat (#411).
- OIDC_CLIENT_SECRET  optioneel; geheim van de client (vertrouwelijke client, zoals een
                   Entra-app met platform Web). Leeg = publieke client met alleen PKCE.
- LOKAAL_INLOGGEN  true = noodtoegang: lokale accounts (tabel users) mogen ook inloggen als
                   OIDC_ISSUER gezet is. Standaard uit zodra OIDC aan staat; zonder OIDC werkt
                   lokaal inloggen altijd.
Toegang tot de viewer (#266, ADR 0009, zie omnitwin/viewer_toegang.py):
- VIEWER_TOEGANG   open (standaard) | inloggen. Bij `inloggen` alleen met een sessie met realm-rol
                   lezer of beheerder: de pagina, de API's van de backend en (via Traefik
                   forwardAuth) /api/data en /api/geo. Een onbekende waarde telt als `inloggen`.
Soort omgeving (#245, zie omnitwin/omgeving.py):
- OMNITWIN_OMGEVING  productie (standaard) | test | demo. Alleen bij `demo` standaardaccounts
                   (admin/admin, gebruiker/gebruiker) en de demobalk; bij `productie` weigert db-init
                   een zwak ADMIN_PASSWORD of KEYCLOAK_ADMIN_PASSWORD. Onbekend telt als productie.

Gebruik `os.getenv("<NAAM>", ...)` letterlijk: tests/test_env_example.py zoekt
daarop om te controleren dat elke variabele in .env.example staat.

Uitzondering: services/embedding_model.py leest EMBEDDING_MODEL_PAD en
HF_HUB_OFFLINE zelf, omdat de Dockerfile dat bestand los (zonder pakket) draait.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # root van de repository (src/omnitwin/config.py)

# .env één keer laden; bestaande omgevingsvariabelen gaan voor (zoals voorheen)
load_dotenv(PROJECT_ROOT / ".env")

_WAAR = ("1", "true", "ja", "yes", "on")

# Vaste grenzen (geen omgevingsvariabele; aanpassen in de code met een reden)
# Inloggen (#203): na zoveel mislukte pogingen binnen het venster volgt 429.
LOGIN_MAX_PER_GEBRUIKER = 5  # per IP-adres + gebruikersnaam
LOGIN_MAX_PER_IP = 20  # per IP-adres, alle gebruikersnamen samen
LOGIN_VENSTER_SECONDEN = 15 * 60
LOGIN_VERTRAGING_SECONDEN = 1.0  # wachttijd na elke mislukte poging
# Maximale duur van één databasequery van de webapp (niet voor db-init/ETL)
STATEMENT_TIMEOUT_MS = 60_000
# CORS: headers die een andere origin mag meesturen. X-Admin-Key is de header die
# routers/auth.py leest (scripts); de beheeromgeving gebruikt het sessiecookie.
CORS_ALLOW_HEADERS = ("Content-Type", "Authorization", "X-Admin-Key")
# Vertrouwde proxy's (#264): loopback en de privé-reeksen. Traefik zit op het Docker-netwerk
# van de stack; dat subnet kiest Docker zelf (172.16.0.0/12 of 192.168.0.0/16, soms 10.0.0.0/8).
# De backend heeft in docker-compose.yml geen hostpoort, dus alleen Traefik en andere containers
# van de stack bereiken hem. Zonder Docker (run_dev.py) op een netwerk met clients: zet
# TRUSTED_PROXIES op het adres van de eigen proxy, of leeg.
STANDAARD_TRUSTED_PROXIES = "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7"


def _bool(waarde: str) -> bool:
    return waarde.strip().lower() in _WAAR


def _int(waarde: str, standaard: int) -> int:
    try:
        return int(waarde.strip())
    except (TypeError, ValueError):
        return standaard


@dataclass(frozen=True)
class Instellingen:
    # Database
    database_host: str
    database_port: str
    database_name: str
    database_user: str
    database_password: str
    database_sslmode: str
    # Web
    cors_origins: tuple[str, ...]
    cookie_secure: str  # 'auto', 'true' of 'false'
    llm_rate_limit: int  # verzoeken per minuut per IP; 0 = uit
    admin_api_key: str
    log_level: str
    # Privacy (#264)
    log_bewaar_dagen: int
    log_ip_bewaar_dagen: int
    trusted_proxies: str  # ruwe lijst; geparsed in omnitwin.grenzen
    # LLM
    ollama_host: str
    ollama_model: str
    llm_think: bool
    llm_reasoning_effort: str
    llm_api_key: str
    # Laad-API (#205)
    leveringen_dir: Path
    laden_max_bytes: int
    laden_wacht_seconden: int
    laden_bewaar_versies: int
    laden_bewaar_dagen: int
    laden_bewaar_afgekeurd_dagen: int
    # OIDC (#205)
    oidc_issuer: str  # leeg = uit
    oidc_audience: str
    oidc_jwks_url: str  # leeg = via discovery
    oidc_intern_url: str  # leeg = discovery via de issuer zelf
    oidc_client_id: str  # inloggen van mensen (#251)
    oidc_scope: str  # extra scopes naast 'openid profile' (#411)
    oidc_client_secret: str  # leeg = publieke client (#411)
    lokaal_inloggen: bool  # LOKAAL_INLOGGEN: noodtoegang naast OIDC
    viewer_toegang: str  # 'open' of 'inloggen' (#266)
    omgeving: str  # 'productie', 'test' of 'demo' (#245)

    @property
    def viewer_dicht(self) -> bool:
        """Viewer en data-API's alleen met een sessie (VIEWER_TOEGANG=inloggen)."""
        return self.viewer_toegang != "open"

    @property
    def demo(self) -> bool:
        return self.omgeving == "demo"

    @property
    def lokaal_inloggen_aan(self) -> bool:
        """Mogen lokale accounts inloggen? Zonder OIDC altijd; met OIDC alleen als noodtoegang."""
        return not self.oidc_issuer or self.lokaal_inloggen

    @property
    def noodtoegang(self) -> bool:
        """OIDC aan én lokaal inloggen aan: waarschuwen in log en UI."""
        return bool(self.oidc_issuer) and self.lokaal_inloggen

    @property
    def database_url(self) -> str:
        # Driver expliciet: SQLAlchemy 2.1+ kiest anders standaard psycopg (v3)
        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
            f"?sslmode={self.database_sslmode}"
        )


def _cookie_secure(waarde: str) -> str:
    waarde = waarde.strip().lower()
    if waarde in _WAAR:
        return "true"
    if waarde in ("0", "false", "nee", "no", "off"):
        return "false"
    return "auto"


VIEWER_TOEGANG_WAARDEN = ("open", "inloggen")
OMGEVINGEN = ("productie", "test", "demo")


def _viewer_toegang(waarde: str) -> str:
    """open of inloggen; leeg = open, al het andere (ook een tikfout) = inloggen: dicht bij twijfel."""
    waarde = waarde.strip().lower()
    return "open" if waarde in ("", "open") else "inloggen"


def _omgeving(waarde: str) -> str:
    """productie, test of demo; leeg of onbekend = productie (de strengste)."""
    waarde = waarde.strip().lower()
    return waarde if waarde in OMGEVINGEN else "productie"


def instellingen() -> Instellingen:
    """De huidige instellingen uit de omgeving."""
    cors = os.getenv("CORS_ORIGINS", "http://localhost:8000")
    return Instellingen(
        database_host=os.getenv("DATABASE_HOST", "localhost"),
        database_port=os.getenv("DATABASE_PORT", "5432"),
        database_name=os.getenv("DATABASE_NAME", "omnitwin_db"),
        database_user=os.getenv("DATABASE_USER", "omnitwin_user"),
        database_password=os.getenv("DATABASE_PASSWORD", ""),
        database_sslmode=os.getenv("DATABASE_SSLMODE", "prefer"),
        cors_origins=tuple(o.strip() for o in cors.split(",") if o.strip()),
        cookie_secure=_cookie_secure(os.getenv("COOKIE_SECURE", "auto")),
        llm_rate_limit=max(0, _int(os.getenv("LLM_RATE_LIMIT", "60"), 60)),
        admin_api_key=os.getenv("ADMIN_API_KEY", "").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_bewaar_dagen=max(1, _int(os.getenv("LOG_BEWAAR_DAGEN", "30"), 30)),
        log_ip_bewaar_dagen=max(0, _int(os.getenv("LOG_IP_BEWAAR_DAGEN", "7"), 7)),
        trusted_proxies=os.getenv("TRUSTED_PROXIES", STANDAARD_TRUSTED_PROXIES),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:30b-instruct"),
        llm_think=_bool(os.getenv("LLM_THINK", "false")),
        llm_reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "none").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        leveringen_dir=Path(os.getenv("LEVERINGEN_DIR", "") or PROJECT_ROOT / "leveringen"),
        laden_max_bytes=max(1, _int(os.getenv("LADEN_MAX_MB", "200"), 200)) * 1024 * 1024,
        laden_wacht_seconden=max(1, _int(os.getenv("LADEN_WACHT_SECONDEN", "60"), 60)),
        laden_bewaar_versies=max(1, _int(os.getenv("LADEN_BEWAAR_VERSIES", "10"), 10)),
        laden_bewaar_dagen=max(1, _int(os.getenv("LADEN_BEWAAR_DAGEN", "365"), 365)),
        laden_bewaar_afgekeurd_dagen=max(1, _int(os.getenv("LADEN_BEWAAR_AFGEKEURD_DAGEN", "30"), 30)),
        oidc_issuer=os.getenv("OIDC_ISSUER", "").strip().rstrip("/"),
        oidc_audience=os.getenv("OIDC_AUDIENCE", "omnitwin-api").strip() or "omnitwin-api",
        oidc_jwks_url=os.getenv("OIDC_JWKS_URL", "").strip(),
        oidc_intern_url=os.getenv("OIDC_INTERN_URL", "").strip().rstrip("/"),
        oidc_client_id=os.getenv("OIDC_CLIENT_ID", "omnitwin-web").strip() or "omnitwin-web",
        oidc_scope=" ".join(os.getenv("OIDC_SCOPE", "").split()),
        oidc_client_secret=os.getenv("OIDC_CLIENT_SECRET", "").strip(),
        lokaal_inloggen=_bool(os.getenv("LOKAAL_INLOGGEN", "false")),
        viewer_toegang=_viewer_toegang(os.getenv("VIEWER_TOEGANG", "open")),
        omgeving=_omgeving(os.getenv("OMNITWIN_OMGEVING", "productie")),
    )
