"""
Centrale foutafhandeling (#203): geen interne fouten naar buiten.

- Een onverwachte fout wordt met traceback gelogd onder een correlatie-id. De
  client krijgt alleen een generieke melding met die id (status 500), zodat een
  beheerder de fout in de log terugvindt zonder dat SQL, paden of
  exceptieteksten de server verlaten.
- Ongeldige invoer die pas in de database opvalt (bijv. geen geldige UUID):
  422. Een conflict met bestaande gegevens (unieke naam, verwijzing): 409.
- `GebruikersFout` is voor meldingen die wél naar buiten mogen ("Gebied X niet
  gevonden"). Een router vangt die en geeft de tekst als `detail` terug; elke
  andere exceptie gaat naar de centrale handler.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from typing import TYPE_CHECKING

# fastapi en sqlalchemy pas bij gebruik importeren: services (en scripts/tests die ze
# zonder webstack gebruiken) importeren alleen GebruikersFout
if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

logger = logging.getLogger("omnitwin.fouten")

HEADER = "X-Correlatie-Id"


class GebruikersFout(ValueError):
    """Fout met een melding die naar de gebruiker mag (geen interne details)."""


def nieuwe_correlatie_id() -> str:
    return uuid.uuid4().hex[:12]


def _antwoord(status: int, melding: str, correlatie_id: str) -> JSONResponse:
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status,
        content={"detail": melding, "correlatie_id": correlatie_id},
        headers={HEADER: correlatie_id},
    )


def _log(request: Request, exc: Exception, correlatie_id: str, status: int) -> None:
    from omnitwin.services.logging_service import AppLogger  # laat: services importeren GebruikersFout

    pad = request.url.path
    samenvatting = f"{request.method} {pad} → {status} [{correlatie_id}] {type(exc).__name__}"
    # Met traceback naar de server-log (console + logs/server.log)
    logger.error(samenvatting, exc_info=(type(exc), exc, exc.__traceback__))
    # Kort naar app_logs (beheer → logs), met de traceback in extra
    AppLogger.error(
        samenvatting,
        category="API",
        endpoint=pad,
        extra={"correlatie_id": correlatie_id,
               "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-8000:]},
    )


async def _ongeldige_waarde(request: Request, exc: Exception) -> JSONResponse:
    cid = nieuwe_correlatie_id()
    _log(request, exc, cid, 422)
    return _antwoord(422, "Ongeldige invoer: een of meer waarden hebben niet het juiste formaat.", cid)


async def _conflict(request: Request, exc: Exception) -> JSONResponse:
    cid = nieuwe_correlatie_id()
    _log(request, exc, cid, 409)
    return _antwoord(409, "Conflict met bestaande gegevens (bijvoorbeeld een naam die al bestaat "
                          "of een verwijzing die niet klopt).", cid)


async def _interne_fout(request: Request, exc: Exception) -> JSONResponse:
    cid = nieuwe_correlatie_id()
    _log(request, exc, cid, 500)
    return _antwoord(500, f"Er ging iets mis op de server. Meld deze code aan de beheerder: {cid}", cid)


def registreer_foutafhandeling(app: FastAPI) -> None:
    """Koppel de centrale handlers aan de app. HTTPException en validatiefouten
    (422 van FastAPI) blijven de standaardafhandeling houden."""
    from sqlalchemy.exc import DataError, IntegrityError

    app.add_exception_handler(DataError, _ongeldige_waarde)
    app.add_exception_handler(IntegrityError, _conflict)
    app.add_exception_handler(Exception, _interne_fout)
