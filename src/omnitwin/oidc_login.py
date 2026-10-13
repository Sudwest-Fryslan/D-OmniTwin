"""
Inloggen van mensen via OIDC (Keycloak) in de beheeromgeving: backend-for-frontend (#251, ADR 0008).

De browser krijgt nooit een token. De backend doet de authorization-code-flow met PKCE namens
de beheer-UI (client OIDC_CLIENT_ID, standaard `omnitwin-web`), wisselt de code in, controleert
het access token met `oidc.controleer_token` (zelfde controle als de laad-API) en zet het
bestaande HttpOnly-cookie `session_token`. De sessie staat in tabel `oidc_sessies` (V029).

- Rollen komen uit het access token (realm-rollen van Keycloak of app-rollen in `roles` van
  Entra ID); `beheerder` geeft beheerrechten.
- Extra scopes (OIDC_SCOPE) en een clientgeheim (OIDC_CLIENT_SECRET) zijn optioneel; Entra ID heeft
  de scope van de eigen API nodig, anders is het access token voor Microsoft Graph (#411).
- Verloopt het access token (Keycloak: 5 minuten), dan ververst de backend het bij het
  volgende verzoek met het refresh token. Weigert Keycloak dat (sessie beëindigd, gebruiker
  uitgeschakeld, idle-time-out), dan is de sessie weg: 401. Zo werkt een ingetrokken rol of
  geblokkeerde gebruiker binnen enkele minuten door.
- Uitloggen: sessie weg en RP-initiated logout bij Keycloak (end_session_endpoint met
  id_token_hint).

Adressen: de browser gaat naar het publieke adres (OIDC_ISSUER), de backend praat met het
interne adres (OIDC_INTERN_URL). Bij dat interne verkeer stuurt de backend X-Forwarded-*-headers
met het publieke adres mee, zodat Keycloak de tokens met de publieke issuer uitgeeft, ook als
KC_HOSTNAME alleen een hostnaam is.

Nooit tokens, e-mail of andere claims loggen; alleen `sub` en `preferred_username`.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import logging
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin import oidc
from omnitwin.config import instellingen

logger = logging.getLogger("omnitwin.oidc_login")

SCOPE = "openid profile"          # geen email: die hoort niet in de sessie of de log
INLOG_COOKIE = "oidc_inlog"       # state, PKCE-verifier en terugadres tijdens het inloggen
INLOG_PAD = "/api/admin/auth/oidc"
INLOG_DUUR = 600                  # seconden om in te loggen bij Keycloak
SESSIE_MAX = dt.timedelta(hours=12)
VERVERS_MARGE = dt.timedelta(seconds=30)
DISCOVERY_TTL = 300
BEHEERROL = "beheerder"


class InlogFout(Exception):
    """Inloggen mislukt; `code` gaat als ?fout= terug naar de inlogpagina (geen details)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------------------
# Eindpunten
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Eindpunten:
    autorisatie: str          # browser (publiek)
    token: str                # backend (intern)
    uitloggen: str | None     # browser (publiek); None als de provider het niet kent


_disc: dict[tuple[str, str], tuple[float, Eindpunten]] = {}
_disc_lock = threading.Lock()


def _forwarded(issuer: str) -> dict[str, str]:
    """Headers waarmee Keycloak het interne verzoek behandelt alsof het via het publieke adres komt."""
    d = urlsplit(issuer)
    poort = d.port or (443 if d.scheme == "https" else 80)
    return {"X-Forwarded-Proto": d.scheme, "X-Forwarded-Host": d.netloc, "X-Forwarded-Port": str(poort)}


def _vervang(url: str, van: str, naar: str) -> str:
    return naar + url[len(van):] if url.startswith(van) else url


def eindpunten() -> Eindpunten:
    """Uit de discovery van de provider (gecachet); publieke en interne adressen apart."""
    i = instellingen()
    if not i.oidc_issuer:
        raise InlogFout("oidc-uit")
    sleutel = (i.oidc_issuer, i.oidc_intern_url)
    with _disc_lock:
        gevonden = _disc.get(sleutel)
        if gevonden and time.monotonic() - gevonden[0] < DISCOVERY_TTL:
            return gevonden[1]
    basis = i.oidc_intern_url or i.oidc_issuer
    r = httpx.get(f"{basis}/.well-known/openid-configuration", timeout=oidc.HTTP_TIMEOUT,
                  headers={"Accept": "application/json", **(_forwarded(i.oidc_issuer) if i.oidc_intern_url else {})})
    r.raise_for_status()
    disc = r.json()
    disc_issuer = str(disc.get("issuer") or i.oidc_issuer).rstrip("/")
    try:
        autorisatie, token = disc["authorization_endpoint"], disc["token_endpoint"]
    except KeyError:
        raise ValueError("discovery zonder authorization_endpoint of token_endpoint")
    uitloggen = disc.get("end_session_endpoint")
    e = Eindpunten(
        autorisatie=_vervang(autorisatie, disc_issuer, i.oidc_issuer),
        token=oidc._intern(token, disc_issuer, i.oidc_intern_url) if i.oidc_intern_url else token,
        uitloggen=_vervang(uitloggen, disc_issuer, i.oidc_issuer) if uitloggen else None,
    )
    with _disc_lock:
        _disc[sleutel] = (time.monotonic(), e)
    return e


def wis_cache() -> None:
    with _disc_lock:
        _disc.clear()


def _token_verzoek(data: dict[str, str]) -> httpx.Response:
    """POST naar het token-endpoint (intern), met de publieke adressering."""
    i = instellingen()
    headers = {"Accept": "application/json"}
    if i.oidc_intern_url:
        headers.update(_forwarded(i.oidc_issuer))
    if i.oidc_client_secret:
        data = {**data, "client_secret": i.oidc_client_secret}
    return httpx.post(eindpunten().token, data={"client_id": i.oidc_client_id, **data},
                      headers=headers, timeout=oidc.HTTP_TIMEOUT)


# ---------------------------------------------------------------------------
# Adressen in de browser
# ---------------------------------------------------------------------------
def publieke_basis(request: Request) -> str:
    """Schema en host zoals de browser ze ziet (achter Traefik via X-Forwarded-*)."""
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip() or request.url.scheme
    host = request.headers.get("x-forwarded-host", "").split(",")[0].strip() or request.headers.get("host", "")
    return f"{proto}://{host or request.url.netloc}"


def veilig_terug(terug: str | None) -> str:
    """Alleen de viewer (`/`) of een pad binnen de beheeromgeving (geen open redirect)."""
    if terug == "/":
        return terug
    if terug and re.fullmatch(r"/admin(/[A-Za-z0-9._~\-/]*)?", terug) and "//" not in terug:
        return terug
    return "/admin/dashboard"


def is_viewer(terug: str) -> bool:
    """Terug naar de viewer (#266) in plaats van naar de beheeromgeving?"""
    return terug == "/"


def gebruikersbeheer_url() -> str | None:
    """Admin-console van Keycloak voor de realm, of None bij een andere provider."""
    m = re.fullmatch(r"(.+)/realms/([^/]+)", instellingen().oidc_issuer)
    return f"{m.group(1)}/admin/{m.group(2)}/console/" if m else None


def account_url() -> str | None:
    """Accountconsole van Keycloak (eigen wachtwoord, sessies), of None."""
    i = instellingen().oidc_issuer
    return f"{i}/account" if re.fullmatch(r".+/realms/[^/]+", i) else None


# ---------------------------------------------------------------------------
# Inloggen
# ---------------------------------------------------------------------------
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def start(request: Request, terug: str | None) -> tuple[str, str]:
    """(adres bij de provider, waarde van het inlogcookie)."""
    i = instellingen()
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    redirect_uri = f"{publieke_basis(request)}{INLOG_PAD}/callback"
    params = {
        "client_id": i.oidc_client_id,
        "response_type": "code",
        "scope": f"{SCOPE} {i.oidc_scope}".strip(),
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": _b64(hashlib.sha256(verifier.encode("ascii")).digest()),
        "code_challenge_method": "S256",
    }
    cookie = _b64(json.dumps({"s": state, "v": verifier, "r": redirect_uri, "t": veilig_terug(terug)}).encode())
    return f"{eindpunten().autorisatie}?{urlencode(params)}", cookie


def _lees_cookie(waarde: str | None) -> dict[str, str]:
    try:
        d = json.loads(base64.urlsafe_b64decode((waarde or "") + "=" * (-len(waarde or "") % 4)))
        if all(isinstance(d.get(k), str) for k in ("s", "v", "r", "t")):
            return d
    except (ValueError, TypeError):
        pass
    raise InlogFout("sessie-verlopen")


def _verwerk_tokens(db: Session, tokens: dict[str, Any], token_hash: str, nieuw: bool,
                    oud: Any = None) -> oidc.Principal:
    """Controleer het access token en schrijf de sessie (nieuw of ververst)."""
    principal = oidc.controleer_token(str(tokens.get("access_token") or ""))
    nu = dt.datetime.now(dt.timezone.utc)
    token_verloopt = nu + dt.timedelta(seconds=max(int(tokens.get("expires_in") or 60), 10))
    refresh_duur = int(tokens.get("refresh_expires_in") or 0)
    if nieuw:
        verloopt = nu + (min(dt.timedelta(seconds=refresh_duur), SESSIE_MAX) if refresh_duur else SESSIE_MAX)
    else:
        verloopt = min(oud.aangemaakt + SESSIE_MAX,
                       nu + dt.timedelta(seconds=refresh_duur) if refresh_duur else oud.aangemaakt + SESSIE_MAX)
    waarden = {
        "h": token_hash, "sub": principal.onderwerp, "naam": principal.gebruikersnaam,
        "rollen": sorted(principal.rollen), "rt": tokens.get("refresh_token"),
        "idt": tokens.get("id_token"), "tv": token_verloopt, "v": verloopt,
    }
    if nieuw:
        db.execute(text("""
            INSERT INTO oidc_sessies (token_hash, onderwerp, gebruikersnaam, rollen, refresh_token, id_token,
                                      token_verloopt, verloopt)
            VALUES (:h, :sub, :naam, :rollen, :rt, :idt, :tv, :v)
        """), waarden)
    else:
        db.execute(text("""
            UPDATE oidc_sessies SET gebruikersnaam = :naam, rollen = :rollen,
                   refresh_token = COALESCE(:rt, refresh_token), id_token = COALESCE(:idt, id_token),
                   token_verloopt = :tv, verloopt = :v
            WHERE token_hash = :h
        """), waarden)
    return principal


def rond_af(db: Session, code: str, state: str, cookie: str | None, sessie_hash: str) -> tuple[oidc.Principal, str]:
    """Callback: code inwisselen, sessie maken. Geeft (principal, terugadres)."""
    inlog = _lees_cookie(cookie)
    if not secrets.compare_digest(state.encode(), inlog["s"].encode()):
        raise InlogFout("state")
    try:
        r = _token_verzoek({"grant_type": "authorization_code", "code": code,
                            "redirect_uri": inlog["r"], "code_verifier": inlog["v"]})
    except httpx.HTTPError as e:
        logger.error("Token-endpoint niet bereikbaar: %s", type(e).__name__)
        raise InlogFout("provider-onbereikbaar")
    if r.status_code != 200:
        logger.warning("Code inwisselen geweigerd door de provider (HTTP %s)", r.status_code)
        raise InlogFout("code-geweigerd")
    try:
        principal = _verwerk_tokens(db, r.json(), sessie_hash, nieuw=True)
    except oidc.AuthProbleem:
        raise InlogFout("token-ongeldig")
    db.execute(text("DELETE FROM oidc_sessies WHERE verloopt <= NOW()"))
    db.commit()
    return principal, inlog["t"]


# ---------------------------------------------------------------------------
# Sessie gebruiken
# ---------------------------------------------------------------------------
def _als_gebruiker(onderwerp: str, gebruikersnaam: str | None, rollen) -> dict:
    return {"user_id": onderwerp, "username": gebruikersnaam or onderwerp,
            "is_admin": BEHEERROL in set(rollen or ()), "type": "oidc", "onderwerp": onderwerp,
            "rollen": sorted(rollen or ())}


def gebruiker(db: Session, token_hash: str) -> dict | None:
    """De gebruiker van een OIDC-sessie, of None (geen of verlopen sessie). Ververst zo nodig."""
    rij = db.execute(text("""
        SELECT onderwerp, gebruikersnaam, rollen, token_verloopt FROM oidc_sessies
        WHERE token_hash = :h AND verloopt > NOW()
    """), {"h": token_hash}).fetchone()
    if rij is None:
        return None
    if rij.token_verloopt - VERVERS_MARGE > dt.datetime.now(dt.timezone.utc):
        return _als_gebruiker(rij.onderwerp, rij.gebruikersnaam, rij.rollen)
    return _ververs(db, token_hash)


def _ververs_data(refresh_token: str) -> dict[str, str]:
    """Refresh-verzoek; met OIDC_SCOPE dezelfde scopes als bij het inloggen (Entra ID vraagt daarom)."""
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    if instellingen().oidc_scope:
        data["scope"] = f"{SCOPE} {instellingen().oidc_scope}"
    return data


def _ververs(db: Session, token_hash: str) -> dict | None:
    # Rij vergrendelen: Keycloak roteert refresh tokens (één keer bruikbaar), dus maar één
    # verzoek tegelijk mag verversen; de rest wacht en leest daarna het nieuwe resultaat.
    rij = db.execute(text("""
        SELECT onderwerp, gebruikersnaam, rollen, refresh_token, token_verloopt, aangemaakt
        FROM oidc_sessies WHERE token_hash = :h AND verloopt > NOW() FOR UPDATE
    """), {"h": token_hash}).fetchone()
    if rij is None:
        db.rollback()
        return None
    if rij.token_verloopt - VERVERS_MARGE > dt.datetime.now(dt.timezone.utc):
        db.commit()  # een ander verzoek was ons voor
        return _als_gebruiker(rij.onderwerp, rij.gebruikersnaam, rij.rollen)
    try:
        r = _token_verzoek(_ververs_data(rij.refresh_token)) if rij.refresh_token else None
    except (httpx.HTTPError, ValueError, InlogFout) as e:
        db.rollback()
        logger.error("Sessie niet te verversen, provider onbereikbaar: %s", type(e).__name__)
        raise oidc.AuthProbleem(503, "oidc-niet-bereikbaar", "Authenticatie niet beschikbaar",
                                "De identity provider is niet bereikbaar.")
    principal = None
    if r is not None and r.status_code == 200:
        try:
            principal = _verwerk_tokens(db, r.json(), token_hash, nieuw=False, oud=rij)
        except oidc.AuthProbleem:
            principal = None
    if principal is None:
        db.execute(text("DELETE FROM oidc_sessies WHERE token_hash = :h"), {"h": token_hash})
        db.commit()
        logger.info("OIDC-sessie beëindigd (verversen geweigerd): sub=%s", rij.onderwerp)
        return None
    db.commit()
    return _als_gebruiker(principal.onderwerp, principal.gebruikersnaam, principal.rollen)


def uitloggen(db: Session, token_hash: str, terug: str) -> str | None:
    """Sessie weg; geeft het adres voor RP-initiated logout bij de provider (of None)."""
    rij = db.execute(text("DELETE FROM oidc_sessies WHERE token_hash = :h RETURNING onderwerp, gebruikersnaam, id_token"),
                     {"h": token_hash}).fetchone()
    db.commit()
    if rij is None:
        return None
    logger.info("Uitgelogd (OIDC): %s sub=%s", rij.gebruikersnaam, rij.onderwerp)
    try:
        eind = eindpunten().uitloggen
    except (httpx.HTTPError, ValueError, InlogFout) as e:
        logger.warning("Uitloggen bij de provider niet mogelijk: %s", type(e).__name__)
        return None
    if not eind:
        return None
    params = {"client_id": instellingen().oidc_client_id, "post_logout_redirect_uri": terug}
    if rij.id_token:
        params["id_token_hint"] = rij.id_token
    return f"{eind}?{urlencode(params)}"
