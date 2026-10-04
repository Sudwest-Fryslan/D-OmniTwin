"""
Toegang per laag en bron (#254, ADR 0010): openbaar of intern.

Wat intern is, staat als data in de database (kolom `toegang` op indicatoren, gebied_data en
externe_kaartlagen; afgeleid van `dct:accessRights` van de dataset in de laad-API, migratie V032).
Wie intern mag zien: een sessie of bearer-token met realm-rol `lezer` of `beheerder` (of een lokale
beheerder, of `X-Admin-Key`), dezelfde regel als de viewer (`viewer_toegang.heeft_rol`).

Hoe het wordt afgedwongen:
- **Backend (FastAPI).** De middleware (`viewer_toegang.ViewerToegangMiddleware`) bepaalt per verzoek de
  `stand` (anoniem, ingelogd zonder rol, met rol) en zet die in een contextvar. Bij elke verbinding die
  de backend uit de pool haalt, schakelt `registreer` naar de databaserol `omnitwin_openbaar`
  (`SET ROLE`) als het verzoek geen interne data mag zien; anders terug naar de eigen rol. Row level
  security (V032) laat die rol alleen `openbaar` zien, ook in joins, views (security_invoker) en
  SQL-functies. Zo hoeft geen query in de services iets te weten van toegang.
  Een directe aanroep van een interne indicator of kaartlaag geeft 401 (anoniem) of 403 (ingelogd
  zonder rol) via `vereis_indicator`/`vereis_kaartlaag`, in plaats van 404.
- **PostgREST (`/api/data`).** De forwardAuth (`GET /api/viewer/toegang`) zet de header
  `X-Omnitwin-Toegang: intern|openbaar`; de views in schema `api` filteren daarop (R__api_rollen.sql).
- **pg_featureserv (`/api/geo`).** Een collectie van een interne kaartlaag (`laag.<featureTabel>`)
  geeft anoniem 401 in de forwardAuth (`collectie_is_intern`).

Zonder verzoek (achtergrondtaken, laadstraat, db-init) is de stand `None`: geen filter.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token

from fastapi import Request

ROL_OPENBAAR = "omnitwin_openbaar"          # databaserol voor anonieme verzoeken (V032)
HEADER = "X-Omnitwin-Toegang"               # forwardAuth → PostgREST (authResponseHeaders)
OPENBAAR, INTERN = "openbaar", "intern"

ANONIEM, ZONDER_ROL, MET_ROL = "anoniem", "zonder-rol", "met-rol"
_stand: ContextVar[str | None] = ContextVar("omnitwin_toegang", default=None)


def zet(stand: str | None) -> Token:
    return _stand.set(stand)


def herstel(token: Token) -> None:
    _stand.reset(token)


def stand() -> str | None:
    """anoniem, zonder-rol, met-rol, of None (geen verzoek: achtergrond, scripts)."""
    return _stand.get()


def mag_intern() -> bool:
    return _stand.get() in (None, MET_ROL)


def heeft_inloggegevens(request: Request) -> bool:
    """Is er iets om op te zoeken? Zonder cookie, token of key is het verzoek anoniem (geen database)."""
    h = request.headers
    return bool(request.cookies.get("session_token") or h.get("authorization") or h.get("x-admin-key"))


# ------------------------------------------------------------------ database

def registreer(engine) -> None:
    """Pool-event: elke verbinding uit de pool krijgt de rol die bij het verzoek hoort.

    Na de SET een commit: anders draait een rollback (ook die bij teruggave aan de pool) hem terug.
    """
    from sqlalchemy import event

    @event.listens_for(engine, "checkout")
    def _rol_per_verzoek(dbapi_connection, _record, _proxy):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("RESET ROLE" if mag_intern() else f"SET ROLE {ROL_OPENBAAR}")
        dbapi_connection.commit()


def weigering(soort: str, stand_: str | None = None):
    """AuthProbleem voor iets interns: 403 als ingelogd zonder rol, anders 401 (Problem Details)."""
    from omnitwin.oidc import AuthProbleem
    if (stand_ or stand()) == ZONDER_ROL:
        return AuthProbleem(403, "geen-toegang", "Geen toegang",
                            f"Deze {soort} is intern: alleen met de rol lezer of beheerder.")
    return AuthProbleem(401, "niet-ingelogd", "Niet ingelogd",
                        f"Deze {soort} is intern: log in met de rol lezer of beheerder.", www_authenticate="Bearer")


def _toegang_van(db, functie: str, sleutel) -> str | None:
    from sqlalchemy import text
    return db.execute(text(f"SELECT public.{functie}(:s)"), {"s": sleutel}).scalar()


def vereis_indicator(db, indicator_uuid) -> None:
    """401/403 als de indicator intern is en dit verzoek dat niet mag zien; anders niets."""
    if mag_intern() or not indicator_uuid:
        return
    try:
        sleutel = str(uuid.UUID(str(indicator_uuid)))
    except ValueError:
        return  # geen UUID: de route geeft zelf 404 of 422
    if _toegang_van(db, "toegang_indicator", sleutel) == INTERN:
        raise weigering("indicator")


def vereis_kaartlaag(db, laag_id: int) -> None:
    """401/403 als de kaartlaag intern is en dit verzoek dat niet mag zien."""
    if mag_intern():
        return
    if _toegang_van(db, "toegang_kaartlaag", int(laag_id)) == INTERN:
        raise weigering("kaartlaag")


_COLLECTIE = re.compile(r"/collections/([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)(?:[/?]|$)")


def collectie_uit_uri(uri: str) -> tuple[str, str] | None:
    """(schema, tabel) van een OGC API Features-collectie in het pad, of None."""
    m = _COLLECTIE.search(uri or "")
    return (m.group(1), m.group(2)) if m else None


def collectie_is_intern(uri: str) -> bool:
    """Is de collectie in dit pad een interne kaartlaag (laag.<featureTabel> van een interne dataset)?"""
    c = collectie_uit_uri(uri)
    if not c or c[0] != "laag":
        return False
    from sqlalchemy import text

    from omnitwin.database import SessionLocal
    db = SessionLocal()
    try:
        return bool(db.execute(text("""
            SELECT 1 FROM laden.datasets
            WHERE profiel = 'kaartlaag' AND toegang = 'intern' AND laadprofiel->'doel'->>'featureTabel' = :t"""),
            {"t": c[1]}).first())
    finally:
        db.close()
