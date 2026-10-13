"""
OIDC: access tokens van Keycloak (of een andere OpenID Connect-provider) controleren (#205).

Voor de nieuwe API's (laad-API en volgende). Gebruik als FastAPI-dependency:

    @router.post("/datasets/{dataset_id}/leveringen")
    def lever(dataset_id: str,
              principal: Principal = Depends(vereis_rol("dataset:{dataset_id}:laden", "datasets:laden"))):
        ...

- `vereis_rol(*rollen)`: geldig token met minstens één van de rollen. `{dataset_id}` in een rol
  wordt ingevuld uit de path-parameter `dataset_id`. 401 zonder of met ongeldig token (met
  `WWW-Authenticate: Bearer`), 403 als de rol ontbreekt, 503 als OIDC niet is ingesteld of de
  sleutels van de provider niet op te halen zijn. Alle fouten als Problem Details (RFC 9457).
- `vereis_principal`: alleen een geldig token, geen rol.
- `principal_optioneel`: de Principal, of None zonder token. Een ongeldig token blijft 401.

Controle: handtekening met een sleutel uit de JWKS van de issuer (gecachet; bij een onbekende
`kid` opnieuw opgehaald, hooguit eens per `JWKS_MIN_VERVERSING` seconden), `iss` gelijk aan
OIDC_ISSUER, `aud` bevat OIDC_AUDIENCE, `exp`/`nbf` met `KLOKRUIMTE` seconden speling. Alleen
asymmetrische algoritmes; `none` en HS* worden geweigerd. Rollen: realm-rollen
(`realm_access.roles`) plus de client-rollen van de audience (`resource_access.<aud>.roles`)
(Keycloak), plus de standaard-claim `roles` (app-rollen van Microsoft Entra ID, #411).

Achter Traefik bereikt de backend Keycloak intern (`http://keycloak:8080/auth/...`), terwijl de
issuer in de tokens de publieke URL is. OIDC_INTERN_URL is dan het interne adres van de issuer:
discovery en JWKS komen daarvandaan, de `iss`-controle blijft tegen OIDC_ISSUER.

Er worden geen tokens of claims met persoonsgegevens gelogd; bij een weigering alleen de reden,
`client_id` (azp) en `jti`.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
import jwt
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from omnitwin.config import instellingen

logger = logging.getLogger("omnitwin.oidc")

# Alleen asymmetrisch: de backend heeft geen gedeeld geheim met de provider
TOEGESTANE_ALGORITMES = ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512")
KLOKRUIMTE = 30              # seconden speling op exp/nbf/iat
JWKS_TTL = 300               # seconden dat een opgehaalde JWKS geldig blijft
JWKS_MIN_VERVERSING = 10     # minimaal aantal seconden tussen twee keer ophalen bij een onbekende kid
HTTP_TIMEOUT = 5.0

PROBLEEM_BASIS = "https://github.com/Sudwest-Fryslan/D-OmniTwin/blob/main/docs/api/laden/README.md#"


@dataclass(frozen=True)
class Principal:
    onderwerp: str            # sub
    client_id: str | None     # azp / client_id
    rollen: frozenset[str]    # realm-rollen + client-rollen van de audience (Keycloak) + `roles` (Entra)
    token_id: str | None      # jti
    gebruikersnaam: str | None = None  # preferred_username (mensen); voor de auditlog, nooit e-mail


# ---------------------------------------------------------------------------
# Problem Details
# ---------------------------------------------------------------------------
class AuthProbleem(Exception):
    """Weigering als Problem Details (RFC 9457); de handler staat in `registreer`."""

    def __init__(self, status: int, code: str, titel: str, detail: str,
                 www_authenticate: str | None = None):
        super().__init__(detail)
        self.status = status
        self.code = code
        self.titel = titel
        self.detail = detail
        self.www_authenticate = www_authenticate


def probleem_antwoord(request: Request, exc: AuthProbleem) -> JSONResponse:
    headers = {"WWW-Authenticate": exc.www_authenticate} if exc.www_authenticate else {}
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        headers=headers,
        content={
            "type": PROBLEEM_BASIS + exc.code,
            "title": exc.titel,
            "status": exc.status,
            "detail": exc.detail,
            "code": exc.code,
            "instance": request.url.path,
        },
    )


async def _probleem_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AuthProbleem)
    return probleem_antwoord(request, exc)


def registreer(app: FastAPI) -> None:
    """Koppel de handler voor AuthProbleem aan de app (gebeurt in fouten.registreer_foutafhandeling)."""
    app.add_exception_handler(AuthProbleem, _probleem_handler)


def _niet_geauthenticeerd(detail: str, met_token: bool) -> AuthProbleem:
    www = 'Bearer error="invalid_token"' if met_token else "Bearer"
    return AuthProbleem(401, "niet-geauthenticeerd", "Niet geauthenticeerd", detail, www)


NIET_GECONFIGUREERD = "OIDC niet geconfigureerd (OIDC_ISSUER is leeg)."


def _niet_beschikbaar(code: str, detail: str) -> AuthProbleem:
    return AuthProbleem(503, code, "Authenticatie niet beschikbaar", detail)


# ---------------------------------------------------------------------------
# Configuratie en sleutels
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Config:
    issuer: str
    audience: str
    jwks_url: str
    intern_url: str


def _config() -> _Config | None:
    i = instellingen()
    if not i.oidc_issuer:
        return None
    return _Config(i.oidc_issuer, i.oidc_audience, i.oidc_jwks_url, i.oidc_intern_url)


def _haal_json(url: str) -> dict[str, Any]:
    """GET met korte timeout; in unittests vervangen door een nep-functie."""
    r = httpx.get(url, timeout=HTTP_TIMEOUT, headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def _intern(url: str, publiek_prefix: str, intern: str) -> str:
    """Herschrijf een URL uit de discovery naar het interne adres van de provider."""
    if url.startswith(publiek_prefix):
        return intern + url[len(publiek_prefix):]
    # Anders alleen schema en host vervangen; het pad is binnen en buiten gelijk
    d, i = urlsplit(url), urlsplit(intern)
    return urlunsplit((i.scheme, i.netloc, d.path, d.query, ""))


class _Sleutelbos:
    """JWKS van één issuer, gecachet, met verversing bij een onbekende kid."""

    def __init__(self, cfg: _Config):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._jwks_url: str | None = cfg.jwks_url or None
        # kid -> (sleutel, alg uit de JWK of None); sleutels zonder kid onder ""
        self._sleutels: dict[str, tuple[jwt.PyJWK, str | None]] = {}
        self._opgehaald = 0.0

    def _bepaal_jwks_url(self) -> str:
        if self._jwks_url:
            return self._jwks_url
        basis = self.cfg.intern_url or self.cfg.issuer
        disc = _haal_json(f"{basis}/.well-known/openid-configuration")
        url = disc.get("jwks_uri")
        if not isinstance(url, str) or not url:
            raise ValueError("discovery zonder jwks_uri")
        if self.cfg.intern_url:
            url = _intern(url, str(disc.get("issuer") or self.cfg.issuer).rstrip("/"), self.cfg.intern_url)
        self._jwks_url = url
        return url

    def _ververs(self) -> None:
        jwks = _haal_json(self._bepaal_jwks_url())
        sleutels: dict[str, tuple[jwt.PyJWK, str | None]] = {}
        for jwk in jwks.get("keys", []):
            if not isinstance(jwk, dict) or jwk.get("use", "sig") != "sig" or jwk.get("kty") not in ("RSA", "EC"):
                continue
            try:
                sleutel = jwt.PyJWK(jwk)
            except (jwt.PyJWKError, jwt.InvalidKeyError):
                continue
            kid = str(jwk.get("kid") or "")
            if kid in sleutels:  # dubbele kid (of meerdere zonder kid): niet eenduidig
                sleutels[kid] = (sleutels[kid][0], "dubbel")
            else:
                sleutels[kid] = (sleutel, jwk.get("alg"))
        self._sleutels = sleutels
        self._opgehaald = time.monotonic()

    def sleutel(self, kid: str | None) -> tuple[jwt.PyJWK, str | None] | None:
        kid = kid or ""
        with self._lock:
            nu = time.monotonic()
            verlopen = not self._opgehaald or nu - self._opgehaald > JWKS_TTL
            onbekend = kid not in self._sleutels and nu - self._opgehaald >= JWKS_MIN_VERVERSING
            if verlopen or onbekend:
                try:
                    self._ververs()
                except (httpx.HTTPError, ValueError):
                    if not self._sleutels:
                        raise
                    # Provider even weg: met de bekende sleutels verder, over JWKS_MIN_VERVERSING opnieuw
                    logger.warning("JWKS niet te verversen; bekende sleutels blijven in gebruik")
                    self._opgehaald = nu - JWKS_TTL + JWKS_MIN_VERVERSING
            gevonden = self._sleutels.get(kid)
            if gevonden is None or gevonden[1] == "dubbel":
                return None
            return gevonden


_bossen: dict[_Config, _Sleutelbos] = {}
_bossen_lock = threading.Lock()


def _sleutelbos(cfg: _Config) -> _Sleutelbos:
    with _bossen_lock:
        if cfg not in _bossen:
            _bossen[cfg] = _Sleutelbos(cfg)
        return _bossen[cfg]


def wis_cache() -> None:
    """Vergeet opgehaalde discovery en sleutels (tests, of na een configuratiewijziging)."""
    with _bossen_lock:
        _bossen.clear()


# ---------------------------------------------------------------------------
# Token controleren
# ---------------------------------------------------------------------------
def _herkenning(token: str) -> str:
    """client_id en jti uit het (nog niet gecontroleerde) token, alleen voor de log."""
    try:
        c = jwt.decode(token, options={"verify_signature": False})
        return f"client_id={c.get('azp') or c.get('client_id')} jti={c.get('jti')}"
    except (jwt.PyJWTError, ValueError, AttributeError):
        return "client_id=? jti=?"


def _weiger(token: str, reden: str, detail: str) -> AuthProbleem:
    logger.warning("Token geweigerd (%s): %s", reden, _herkenning(token))
    return _niet_geauthenticeerd(detail, met_token=True)


def _rollen(claims: dict[str, Any], audience: str) -> frozenset[str]:
    rollen: set[str] = set()
    # Entra ID (en andere providers): app-rollen in de top-level claim `roles` (#411)
    if isinstance(claims.get("roles"), list):
        rollen.update(r for r in claims["roles"] if isinstance(r, str))
    realm = claims.get("realm_access")
    if isinstance(realm, dict) and isinstance(realm.get("roles"), list):
        rollen.update(r for r in realm["roles"] if isinstance(r, str))
    resource = claims.get("resource_access")
    client = resource.get(audience) if isinstance(resource, dict) else None
    if isinstance(client, dict) and isinstance(client.get("roles"), list):
        rollen.update(r for r in client["roles"] if isinstance(r, str))
    return frozenset(rollen)


def controleer_token(token: str, cfg: _Config | None = None) -> Principal:
    """Controleer een access token en geef de Principal; anders AuthProbleem (401/503)."""
    cfg = cfg or _config()
    if cfg is None:
        raise _niet_beschikbaar("oidc-niet-geconfigureerd", NIET_GECONFIGUREERD)

    try:
        kop = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise _weiger(token, "geen JWT", "Token is geen geldig JWT.")
    alg = kop.get("alg")
    if alg not in TOEGESTANE_ALGORITMES:
        raise _weiger(token, f"algoritme {alg!r}", "Algoritme van het token niet toegestaan.")

    try:
        gevonden = _sleutelbos(cfg).sleutel(kop.get("kid"))
    except (httpx.HTTPError, ValueError) as e:
        logger.error("Sleutels van de OIDC-provider niet op te halen: %s", type(e).__name__)
        raise _niet_beschikbaar("oidc-niet-bereikbaar", "Sleutels van de identity provider niet bereikbaar.")
    if gevonden is None:
        raise _weiger(token, "onbekende kid", "Token is getekend met een onbekende sleutel.")
    sleutel, sleutel_alg = gevonden
    if sleutel_alg and sleutel_alg != alg:
        raise _weiger(token, "alg past niet bij sleutel", "Algoritme van het token past niet bij de sleutel.")

    try:
        claims = jwt.decode(
            token,
            key=sleutel.key,
            algorithms=[alg],
            audience=cfg.audience,
            issuer=cfg.issuer,
            leeway=KLOKRUIMTE,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise _weiger(token, "verlopen", "Token is verlopen.")
    except jwt.ImmatureSignatureError:
        raise _weiger(token, "nog niet geldig", "Token is nog niet geldig (nbf/iat).")
    except jwt.InvalidAudienceError:
        raise _weiger(token, "audience", f"Token is niet bestemd voor {cfg.audience} (aud).")
    except jwt.InvalidIssuerError:
        raise _weiger(token, "issuer", "Token komt van een andere issuer (iss).")
    except jwt.InvalidSignatureError:
        raise _weiger(token, "handtekening", "Handtekening van het token klopt niet.")
    except jwt.PyJWTError as e:
        raise _weiger(token, type(e).__name__, "Token is ongeldig.")

    client_id = claims.get("azp") or claims.get("client_id")
    return Principal(
        onderwerp=str(claims.get("sub") or ""),
        client_id=str(client_id) if client_id else None,
        rollen=_rollen(claims, cfg.audience),
        token_id=str(claims["jti"]) if claims.get("jti") else None,
        gebruikersnaam=str(claims["preferred_username"]) if claims.get("preferred_username") else None,
    )


# ---------------------------------------------------------------------------
# FastAPI-dependencies
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=False, scheme_name="oidc",
                     description="Access token van Keycloak (realm omnitwin), aud omnitwin-api.")


def _principal(request: Request, cred: HTTPAuthorizationCredentials | None, verplicht: bool) -> Principal | None:
    heeft_kop = bool(request.headers.get("authorization"))
    if cred is None or not cred.credentials:
        if heeft_kop:
            raise _niet_geauthenticeerd("Authorization-header moet 'Bearer <token>' zijn.", met_token=True)
        cfg = _config()
        if verplicht:
            if cfg is None:
                raise _niet_beschikbaar("oidc-niet-geconfigureerd", NIET_GECONFIGUREERD)
            raise _niet_geauthenticeerd("Bearer-token ontbreekt.", met_token=False)
        return None
    return controleer_token(cred.credentials)


def principal_optioneel(request: Request,
                        cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Principal | None:
    """Dependency: de Principal, of None als er geen token is meegestuurd. Ongeldig token: 401."""
    return _principal(request, cred, verplicht=False)


def vereis_principal(request: Request,
                     cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Principal:
    """Dependency: een geldig token, ongeacht de rollen."""
    p = _principal(request, cred, verplicht=True)
    assert p is not None
    return p


def vereis_rol(*rollen: str) -> Callable[..., Principal]:
    """FastAPI-dependency. Rollen mogen `{dataset_id}` bevatten; die wordt ingevuld uit de path-parameter `dataset_id`.
    Toegang als de Principal minstens één van de (ingevulde) rollen heeft. 401 zonder/ongeldig token
    (met WWW-Authenticate: Bearer), 403 bij ontbrekende rol (Problem Details)."""
    if not rollen:
        raise ValueError("vereis_rol zonder rollen; gebruik vereis_principal")

    def afhankelijkheid(request: Request,
                        cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Principal:
        principal = _principal(request, cred, verplicht=True)
        assert principal is not None
        nodig = set()
        for rol in rollen:
            if "{dataset_id}" in rol:
                dataset_id = request.path_params.get("dataset_id")
                if not dataset_id:
                    raise RuntimeError(f"rol {rol!r} vereist de path-parameter dataset_id")
                rol = rol.replace("{dataset_id}", str(dataset_id))
            nodig.add(rol)
        if principal.rollen & nodig:
            return principal
        logger.warning("Rol ontbreekt (nodig een van %s): client_id=%s jti=%s",
                       sorted(nodig), principal.client_id, principal.token_id)
        raise AuthProbleem(
            403, "geen-toegang", "Geen toegang",
            "Het token heeft geen van de benodigde rollen: " + ", ".join(sorted(nodig)) + ".",
            'Bearer error="insufficient_scope"',
        )

    afhankelijkheid.__name__ = "vereis_rol_" + "_".join(rollen)
    return afhankelijkheid
