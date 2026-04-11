"""
Authentication Router for Beheerscherm
Handles local session-based authentication (HttpOnly cookies) and API keys.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db
from passlib.context import CryptContext
from pydantic import BaseModel
import secrets
import datetime
import os

router = APIRouter(prefix="/api/admin/auth", tags=["Auth"])

# Bcrypt voor passwoorden
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

def check_auth_or_key(request: Request, db: Session = Depends(get_db)):
    """
    Hybrid Auth Dependency: 
    1. Check if valid Session Cookie is present.
    2. Fallback: Check if valid X-Admin-Key header is present (voor Scripts/ETL).
    """
    
    # 1. Check Session Cookie (Web UI)
    session_token = request.cookies.get("session_token")
    if session_token:
        # SQL check
        result = db.execute(text("""
            SELECT u.id, u.username, u.is_admin 
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = :token AND s.expires_at > NOW()
            AND u.is_active = true
        """), {"token": session_token})
        user = result.fetchone()
        
        if user:
            return {"user_id": user[0], "username": user[1], "is_admin": user[2], "type": "session"}
            
    # 2. Check X-Admin-Key (Scripts/Legacy)
    api_key_header = request.headers.get("X-Admin-Key")
    admin_api_key_env = os.getenv('ADMIN_API_KEY', '')
    
    if api_key_header and admin_api_key_env and api_key_header == admin_api_key_env:
        return {"user_id": "system_admin_key", "username": "API_SCRIPT", "is_admin": True, "type": "api_key"}

    # Geen van beide geldig -> 401
    raise HTTPException(status_code=401, detail="Niet geautoriseerd.")


# ============================================================================
# Endpoints
# ============================================================================
@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible inlog actie -> Zorgt voor een HttpOnly session cookie."""
    
    # Check user in DB
    result = db.execute(text("""
        SELECT id, username, hashed_password, is_active 
        FROM users 
        WHERE username = :username
    """), {"username": form_data.username})
    user = result.fetchone()

    if not user or not user[3]: # Not active
        raise HTTPException(status_code=401, detail="Onjuiste gebruikersnaam of wachtwoord")

    if not verify_password(form_data.password, user[2]): # Check hashed pass
        raise HTTPException(status_code=401, detail="Onjuiste gebruikersnaam of wachtwoord")

    # Wachtwoord is goed! Creëer sessie token
    token = create_session_token()
    
    # Expiration: 12 uur
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)
    
    # Opslaan in database
    db.execute(text("""
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (:token, :user_id, :expires)
    """), {"token": token, "user_id": user[0], "expires": expires})
    db.commit()

    # HttpOnly Cookie zetten (voorkomt JavaScript XSS thef van token)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=12 * 3600,
        samesite="lax", # Goed voor zelfde domein protectie tegen CSRF
        secure=os.getenv("DEBUG", "false").lower() != "true" # True on prod (HTTPS)
    )

    return {"message": "Succesvol ingelogd", "user": {"id": str(user[0]), "username": user[1]}}

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Logs the user out (deletes session and cookie)."""
    session_token = request.cookies.get("session_token")
    if session_token:
        db.execute(text("DELETE FROM sessions WHERE token = :token"), {"token": session_token})
        db.commit()

    response.delete_cookie("session_token", httponly=True, samesite="lax")
    return {"message": "Succesvol uitgelogd"}

@router.get("/me", response_model=AuthStatus)
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Check of men ingelogd is (en zo ja, met welke user)."""
    try:
        user_info = check_auth_or_key(request, db)
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
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Wijzig het wachtwoord van de ingelogde gebruiker."""
    # 1. Check if user is logged in
    user_info = check_auth_or_key(request, db)
    
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
    
    # Optioneel: alle andere sessies beëindigen
    db.execute(text("""
        DELETE FROM sessions WHERE user_id = :id AND token != :token
    """), {"id": user_id, "token": request.cookies.get("session_token")})
    
    db.commit()
    return {"message": "Wachtwoord succesvol gewijzigd"}
