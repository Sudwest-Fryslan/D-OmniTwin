"""
Toegang tot de viewer (#266, ADR 0009): open voor iedereen, of alleen na inloggen.

`VIEWER_TOEGANG=open` (standaard): zoals altijd, inloggen is optioneel.
`VIEWER_TOEGANG=inloggen`: de kaart (`/`) en alle data-API's alleen met een sessie (of bearer-token)
met realm-rol `lezer` of `beheerder`. Een lokale beheerder (sessie met `is_admin`) of een script met
`X-Admin-Key` telt als beheerder.

Waar het gecontroleerd wordt:
- de backend zelf (FastAPI): `ViewerToegangMiddleware` voor alles wat via de backend loopt;
- PostgREST (`/api/data`) en pg_featureserv (`/api/geo`): Traefik forwardAuth (middleware
  `viewer-toegang@file`, deploy/traefik/dynamic.yml) naar `GET /api/viewer/toegang` van de backend.
  Die middleware staat altijd aan; bij `open` antwoordt de backend direct 204.

Uitzonderingen (altijd open): health, de inlogroutes van de backend, de beheeromgeving zelf (de
SPA-schil; de beheer-API's controleren zelf), de laad-API en `/api/oidc/ik` (eigen tokens),
`/api/organisatie` (naam en thema voor de inlogpagina), statische bestanden (code, stijl en
afbeeldingen; geen data) en `/.well-known/`.

Zonder sessie: een pagina (GET, Accept text/html) gaat naar het inloggen bij Keycloak (zonder
Keycloak naar de inlogpagina van de beheeromgeving); een API-verzoek krijgt 401 (Problem Details).
Ingelogd zonder rol: 403.

Toegang per laag en bron (#254, ADR 0010, `omnitwin.toegang`): ook bij `open` bepaalt de middleware per
verzoek of het interne data mag zien (zelfde rol lezer of beheerder), en zet het forwardAuth-antwoord de
header `X-Omnitwin-Toegang` voor PostgREST; een interne collectie van pg_featureserv geeft anoniem 401.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from omnitwin import oidc, oidc_login, toegang
from omnitwin.config import instellingen

ROLLEN = frozenset({"lezer", oidc_login.BEHEERROL})
CONTROLE_PAD = "/api/viewer/toegang"     # forwardAuth van Traefik
LOGIN_PAD = oidc_login.INLOG_PAD + "/login"

# Altijd open, ook bij VIEWER_TOEGANG=inloggen. Prefixen; "/" alleen exact.
OPEN_EXACT = frozenset({"/health", "/favicon.ico", CONTROLE_PAD, "/api/organisatie",
                        "/api/organisatie/beeldmerk.svg"})
OPEN_PREFIX = (
    "/static/",              # code, stijl, afbeeldingen (geen data)
    "/.well-known/",
    "/admin",                # SPA van de beheeromgeving; de beheer-API's hebben vereis_admin
    "/api/admin/auth/",      # inloggen, callback, uitloggen, me, config
    "/api/laden/",           # laad-API: eigen tokens (vereis_rol)
    "/api/oidc/ik",          # testendpoint, eigen token
)


def is_open_pad(pad: str) -> bool:
    return pad in OPEN_EXACT or any(pad.startswith(p) for p in OPEN_PREFIX)


@dataclass(frozen=True)
class Besluit:
    toegang: bool
    gebruiker: dict | None          # wie (sessie, bearer of key), of None
    status: int = 200               # 200, 401 (niet ingelogd), 403 (geen rol), 503 (provider weg)
    probleem: oidc.AuthProbleem | None = None


def heeft_rol(gebruiker: dict | None) -> bool:
    """Mag deze gebruiker de viewer zien? Rol lezer of beheerder; lokaal of met key: beheerder."""
    if not gebruiker:
        return False
    if gebruiker.get("is_admin"):
        return True
    return bool(ROLLEN & set(gebruiker.get("rollen") or ()))


def gebruiker_van(request: Request) -> dict | None:
    """Wie doet dit verzoek? None als niemand (geen of verlopen sessie). Een ongeldig bearer-token
    (401) of een storing bij de provider (503) gaat als AuthProbleem door."""
    from omnitwin.database import SessionLocal
    from omnitwin.routers.auth import huidige_gebruiker
    db = SessionLocal()
    try:
        return huidige_gebruiker(request, db)
    except HTTPException:
        return None
    finally:
        db.close()


def beoordeel(request: Request) -> Besluit:
    """Toegang tot de viewer en data-API's voor dit verzoek (synchroon: database)."""
    try:
        gebruiker = gebruiker_van(request)
    except oidc.AuthProbleem as e:     # ongeldig token (401, met WWW-Authenticate) of provider weg (503)
        return Besluit(False, None, e.status, e)
    if gebruiker is None:
        return Besluit(False, None, 401)
    if not heeft_rol(gebruiker):
        return Besluit(False, gebruiker, 403)
    return Besluit(True, gebruiker)


def _probleem(request: Request, besluit: Besluit) -> JSONResponse:
    if besluit.probleem is not None:
        return oidc.probleem_antwoord(request, besluit.probleem)
    if besluit.status == 401:
        p = oidc.AuthProbleem(401, "niet-ingelogd", "Niet ingelogd",
                              "Deze installatie is alleen toegankelijk na inloggen (VIEWER_TOEGANG=inloggen).",
                              www_authenticate="Bearer")
    else:
        p = oidc.AuthProbleem(403, "geen-toegang", "Geen toegang",
                              "Ingelogd, maar zonder de rol lezer of beheerder.")
    return oidc.probleem_antwoord(request, p)


def login_adres(terug: str = "/") -> str:
    """Waar een anonieme bezoeker van de viewer heen gaat: Keycloak, of zonder Keycloak de
    inlogpagina van de beheeromgeving (alleen een lokale beheerder heeft dan toegang)."""
    if instellingen().oidc_issuer:
        return f"{LOGIN_PAD}?terug={quote(terug, safe='/')}"
    return "/admin/login"


GEEN_TOEGANG_HTML = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Geen toegang - D-OmniTwin</title>
<style>body{font-family:system-ui,sans-serif;max-width:36rem;margin:4rem auto;padding:0 1rem;line-height:1.5}
button{font:inherit;padding:.5rem 1rem;cursor:pointer}</style></head>
<body><main><h1>Geen toegang</h1>
<p>Je bent ingelogd als <strong>{naam}</strong>, maar je hebt niet de rol <em>lezer</em> of <em>beheerder</em>.
Vraag een gebruikersbeheerder om je die rol te geven.</p>
<p><button type="button" id="uitloggen">Uitloggen</button></p></main>
<script src="/static/js/viewer-account.js"></script></body></html>"""


def geen_toegang_pagina(gebruiker: dict | None) -> HTMLResponse:
    from html import escape
    naam = escape(str((gebruiker or {}).get("username") or "onbekend"))
    return HTMLResponse(GEEN_TOEGANG_HTML.replace("{naam}", naam), status_code=403)


def wil_html(request: Request) -> bool:
    return request.method == "GET" and "text/html" in request.headers.get("accept", "") \
        and not request.url.path.startswith("/api")


class ViewerToegangMiddleware(BaseHTTPMiddleware):
    """Bij VIEWER_TOEGANG=inloggen: alles via de backend behalve de open paden alleen met rol.
    Altijd (#254): de stand voor toegang per laag (anoniem, zonder rol, met rol) in de contextvar van
    `omnitwin.toegang`, vóór de eerste databaseverbinding van het verzoek."""

    async def dispatch(self, request: Request, call_next) -> Response:
        pad = request.url.path
        if request.method == "OPTIONS" or pad == CONTROLE_PAD or pad.startswith(("/static/", "/api/laden/")):
            # statisch: geen data; forwardAuth: eigen beslissing; laad-API: eigen tokens en rollen
            return await call_next(request)
        token = toegang.zet(toegang.ANONIEM)
        try:
            if instellingen().viewer_dicht and not is_open_pad(pad):
                besluit = await run_in_threadpool(beoordeel, request)
                if besluit.toegang:
                    request.state.viewer_gebruiker = besluit.gebruiker
                    toegang.zet(toegang.MET_ROL)
                    return await call_next(request)
                if wil_html(request):
                    if besluit.status == 401 and besluit.probleem is None:
                        return RedirectResponse(login_adres("/"), status_code=302)
                    if besluit.status == 403:
                        return geen_toegang_pagina(besluit.gebruiker)
                return _probleem(request, besluit)
            if toegang.heeft_inloggegevens(request):
                toegang.zet(await run_in_threadpool(_stand, request))
            return await call_next(request)
        finally:
            toegang.herstel(token)


def _stand(request: Request) -> str:
    """anoniem, zonder-rol of met-rol; een ongeldig token of storing telt als anoniem."""
    try:
        gebruiker = gebruiker_van(request)
    except oidc.AuthProbleem:
        return toegang.ANONIEM
    if gebruiker is None:
        return toegang.ANONIEM
    return toegang.MET_ROL if heeft_rol(gebruiker) else toegang.ZONDER_ROL


async def controleer(request: Request) -> Response:
    """forwardAuth van Traefik voor /api/data en /api/geo: 204 = door, anders 401/403/503.

    Bij 204 de header X-Omnitwin-Toegang (intern of openbaar) voor PostgREST (#254); Traefik zet hem op
    het doorgestuurde verzoek en vervangt een meegestuurde (authResponseHeaders). Een interne collectie
    van pg_featureserv (X-Forwarded-Uri) zonder rol: 401 of 403."""
    if instellingen().viewer_dicht:
        besluit = await run_in_threadpool(beoordeel, request)
        if not besluit.toegang:
            return _probleem(request, besluit)
        stand = toegang.MET_ROL
    elif toegang.heeft_inloggegevens(request):
        stand = await run_in_threadpool(_stand, request)
    else:
        stand = toegang.ANONIEM
    if stand != toegang.MET_ROL:
        uri = request.headers.get("x-forwarded-uri", "")
        if toegang.collectie_uit_uri(uri) and await run_in_threadpool(toegang.collectie_is_intern, uri):
            return oidc.probleem_antwoord(request, toegang.weigering("kaartlaag", stand))
    waarde = toegang.INTERN if stand == toegang.MET_ROL else toegang.OPENBAAR
    return Response(status_code=204, headers={toegang.HEADER: waarde})
