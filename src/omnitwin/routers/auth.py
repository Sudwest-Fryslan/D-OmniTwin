"""
Authentication Router for Beheerscherm
Handles local session-based authentication (HttpOnly cookies) and API keys.

Autorisatie (#65):
- `huidige_gebruiker`: ingelogde gebruiker (sessie-cookie) of script met een
  geldige `X-Admin-Key`; anders 401.
- `vereis_admin`: als hierboven, en de gebruiker moet `is_admin` hebben;
  anders 403. Hangt op routerniveau aan alle beheer-routers.

Sessietokens staan gehasht (sha256) in `sessions.token_hash`; het cookie
bevat het ruwe token.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from omnitwin.database import get_db
from passlib.context import CryptContext
from pydantic import BaseModel
import hashlib
import secrets
import asyncio
import datetime
import math

from fastapi.concurrency import run_in_threadpool

from omnitwin.config import (
    LOGIN_MAX_PER_GEBRUIKER, LOGIN_MAX_PER_IP, LOGIN_VENSTER_SECONDEN, LOGIN_VERTRAGING_SECONDEN,
    instellingen,
)
from omnitwin.grenzen import Limiet, client_ip, te_veel
from omnitwin.services.logging_service import AppLogger

router = APIRouter(prefix="/api/admin/auth", tags=["Auth"])

# Bcrypt voor passwoorden
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSIE_DUUR = datetime.timedelta(hours=12)

# Minimale lengte van ADMIN_API_KEY; `openssl rand -hex 32` geeft 64 tekens
MIN_ADMIN_KEY_LENGTE = 32
# Woorden uit voorbeeldwaarden (.env.example, BUILD.md, handleidingen)
_PLACEHOLDER_WOORDEN = (
    "genereer", "jouw_", "your_", "_here", "changeme", "change_me", "change-me",
    "voorbeeld", "placeholder",
)

# ============================================================================
# Auth Models
# ============================================================================
class UserResponse(BaseModel):
    id: str
    username: str
    is_admin: bool

class AuthStatus(BaseModel):
    authenticated: bool
    user: UserResponse | None = None

# ============================================================================
# Helper Functies
# ============================================================================
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_session_token():
    return secrets.token_urlsafe(64)

def hash_token(token: str) -> str:
    """Sleutel waaronder een sessie in de database staat (sha256, hex)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def is_placeholder_key(key: str | None) -> bool:
    """True voor een lege, te korte of voorbeeld-key; die geeft nooit toegang."""
    if not key or not key.strip():
        return True
    key = key.strip()
    if len(key) < MIN_ADMIN_KEY_LENGTE or key.startswith("<"):
        return True
    laag = key.lower()
    return any(woord in laag for woord in _PLACEHOLDER_WOORDEN)

def geldige_admin_api_key() -> str | None:
    """ADMIN_API_KEY uit de omgeving, of None als die leeg of een placeholder is."""
    key = instellingen().admin_api_key
    return None if is_placeholder_key(key) else key

def cookie_secure(request: Request) -> bool:
    """Krijgt het sessiecookie `Secure`? COOKIE_SECURE=true/false, of auto (standaard):
    alleen als het verzoek via HTTPS binnenkomt, direct of via de proxy (X-Forwarded-Proto)."""
    instelling = instellingen().cookie_secure
    if instelling != "auto":
        return instelling == "true"
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return (proto or request.url.scheme) == "https"

def ruim_verlopen_sessies_op(db: Session) -> None:
    db.execute(text("DELETE FROM sessions WHERE expires_at <= NOW()"))

def huidige_gebruiker(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Wie doet dit verzoek?
    1. Een geldige sessie-cookie (Web UI).
    2. Anders een geldige X-Admin-Key header (scripts/ETL). Een lege of
       placeholder-key in .env schakelt deze route uit.
    Geen van beide -> 401.
    """
    session_token = request.cookies.get("session_token")
    if session_token:
        user = db.execute(text("""
            SELECT u.id, u.username, u.is_admin
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token_hash = :token_hash AND s.expires_at > NOW()
            AND u.is_active = true
        """), {"token_hash": hash_token(session_token)}).fetchone()
        if user:
            return {"user_id": user[0], "username": user[1], "is_admin": bool(user[2]), "type": "session"}

    api_key_header = request.headers.get("X-Admin-Key")
    admin_api_key = geldige_admin_api_key()
    if (api_key_header and admin_api_key
            and secrets.compare_digest(api_key_header.encode("utf-8"), admin_api_key.encode("utf-8"))):
        return {"user_id": "system_admin_key", "username": "API_SCRIPT", "is_admin": True, "type": "api_key"}

    raise HTTPException(status_code=401, detail="Niet geautoriseerd.")

def vereis_admin(request: Request, db: Session = Depends(get_db)) -> dict:
    """Dependency voor alle beheer-routes: ingelogd (401) én beheerder (403)."""
    gebruiker = huidige_gebruiker(request, db)
    if not gebruiker.get("is_admin"):
        raise HTTPException(status_code=403, detail="Alleen voor beheerders.")
    return gebruiker

# Oude naam; levert alleen de identiteit, géén admin-check. Gebruik vereis_admin.
check_auth_or_key = huidige_gebruiker


# ============================================================================
# Endpoints
# ============================================================================
def _dummy_hash() -> str:
    """Hash om ook bij een onbekende gebruiker bcrypt te draaien: gelijke responstijd,
    zodat gebruikersnamen niet via de timing te achterhalen zijn (#203)."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = get_password_hash(secrets.token_urlsafe(16))
    return _DUMMY_HASH

_DUMMY_HASH: str | None = None

# Inlogpogingen (#203): mislukte pogingen per IP + gebruikersnaam en per IP
_mislukt_per_gebruiker = Limiet(LOGIN_MAX_PER_GEBRUIKER, LOGIN_VENSTER_SECONDEN)
_mislukt_per_ip = Limiet(LOGIN_MAX_PER_IP, LOGIN_VENSTER_SECONDEN)


def _inloggen(db: Session, username: str, password: str):
    """Controleer de inloggegevens en maak een sessie (synchroon: database en bcrypt).
    Geeft (user, token) bij succes, anders None."""
    result = db.execute(text("""
        SELECT id, username, hashed_password, is_active
        FROM users
        WHERE username = :username
    """), {"username": username})
    user = result.fetchone()

    if not user or not user[3]: # Not active
        verify_password(password, _dummy_hash())
        AppLogger.warning(f"Login mislukt: gebruiker '{username}' niet gevonden of niet actief", category="AUTH")
        return None

    if not verify_password(password, user[2]): # Check hashed pass
        AppLogger.warning(f"Login mislukt: onjuist wachtwoord voor '{username}'", category="AUTH")
        return None

    # Wachtwoord is goed: verlopen sessies opruimen en een nieuwe sessie maken
    ruim_verlopen_sessies_op(db)
    token = create_session_token()
    expires = datetime.datetime.now(datetime.timezone.utc) + SESSIE_DUUR

    # Alleen de hash in de database; het ruwe token gaat in het cookie
    db.execute(text("""
        INSERT INTO sessions (token_hash, user_id, expires_at)
        VALUES (:token_hash, :user_id, :expires)
    """), {"token_hash": hash_token(token), "user_id": user[0], "expires": expires})
    db.commit()
    return user, token


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible inlog actie -> Zorgt voor een HttpOnly session cookie.

    Na LOGIN_MAX_PER_GEBRUIKER mislukte pogingen (per IP + gebruikersnaam) of
    LOGIN_MAX_PER_IP (per IP) binnen het venster: 429 met Retry-After. Elke
    mislukte poging wacht eerst even. De database en bcrypt draaien in de
    threadpool; het wachten blokkeert de server niet (#203, #68).
    """
    ip = client_ip(request)
    sleutel = f"{ip}|{form_data.username.strip().lower()}"
    wacht = max(_mislukt_per_gebruiker.wachttijd(sleutel), _mislukt_per_ip.wachttijd(ip))
    if wacht:
        # IP in het veld ip_address (wordt na LOG_IP_BEWAAR_DAGEN ingekort), niet in de tekst (#264)
        AppLogger.warning(f"Login geblokkeerd voor '{form_data.username}' ({wacht}s)", category="AUTH",
                          ip_address=ip)
        raise te_veel(wacht, f"Te veel mislukte inlogpogingen. Probeer het over {math.ceil(wacht / 60)} minuten opnieuw.")

    resultaat = await run_in_threadpool(_inloggen, db, form_data.username, form_data.password)
    if resultaat is None:
        _mislukt_per_gebruiker.registreer(sleutel)
        _mislukt_per_ip.registreer(ip)
        await asyncio.sleep(LOGIN_VERTRAGING_SECONDEN)
        raise HTTPException(status_code=401, detail="Onjuiste gebruikersnaam of wachtwoord")

    user, token = resultaat
    _mislukt_per_gebruiker.reset(sleutel)

    # HttpOnly Cookie zetten (voorkomt JavaScript XSS thef van token)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=int(SESSIE_DUUR.total_seconds()),
        samesite="lax", # Goed voor zelfde domein protectie tegen CSRF
        secure=cookie_secure(request),  # COOKIE_SECURE (auto: alleen via HTTPS)
    )

    AppLogger.info(f"Login geslaagd: gebruiker '{user[1]}'", category="AUTH", user_id=str(user[0]))

    return {"message": "Succesvol ingelogd", "user": {"id": str(user[0]), "username": user[1]}}

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Logs the user out (deletes session and cookie)."""
    session_token = request.cookies.get("session_token")
    if session_token:
        db.execute(text("DELETE FROM sessions WHERE token_hash = :token_hash"),
                   {"token_hash": hash_token(session_token)})
        db.commit()

    response.delete_cookie("session_token", httponly=True, samesite="lax")
    AppLogger.info("Gebruiker uitgelogd", category="AUTH")
    return {"message": "Succesvol uitgelogd"}

@router.get("/me", response_model=AuthStatus)
def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Check of men ingelogd is (en zo ja, met welke user)."""
    try:
        user_info = huidige_gebruiker(request, db)
        return AuthStatus(
            authenticated=True,
            user=UserResponse(id=str(user_info["user_id"]), username=user_info["username"], is_admin=user_info["is_admin"])
        )
    except HTTPException:
        return AuthStatus(authenticated=False, user=None)

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Wijzig het wachtwoord van de ingelogde gebruiker."""
    # 1. Check if user is logged in
    user_info = huidige_gebruiker(request, db)

    # Scripts using API key header cannot change passwords via this route
    if user_info.get("type") == "api_key":
        raise HTTPException(status_code=403, detail="API Keys kunnen geen wachtwoorden wijzigen. Log in via de UI.")

    user_id = user_info["user_id"]

    # 2. Verify old password
    result = db.execute(text("SELECT hashed_password FROM users WHERE id = :id"), {"id": user_id})
    user_record = result.fetchone()

    if not user_record or not verify_password(data.old_password, user_record[0]):
        raise HTTPException(status_code=400, detail="Huidig wachtwoord is onjuist.")

    # 3. Validation
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Nieuw wachtwoord moet minimaal 6 tekens bevatten.")

    # 4. Hash new password and save
    new_hashed_password = get_password_hash(data.new_password)
    db.execute(text("""
        UPDATE users
        SET hashed_password = :hashed_password
        WHERE id = :id
    """), {"hashed_password": new_hashed_password, "id": user_id})

    # Alle andere sessies van deze gebruiker beëindigen
    db.execute(text("""
        DELETE FROM sessions WHERE user_id = :id AND token_hash != :token_hash
    """), {"id": user_id, "token_hash": hash_token(request.cookies.get("session_token", ""))})

    db.commit()
    AppLogger.info(f"Wachtwoord gewijzigd voor user_id={user_id}", category="AUTH", user_id=str(user_id))
    return {"message": "Wachtwoord succesvol gewijzigd"}
