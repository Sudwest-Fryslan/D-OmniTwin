"""
Indicatorpaneel en CSV-export (#258)
====================================
GET /api/gebiedsmonitor/indicatorpaneel       JSON voor het paneel in de viewer
GET /api/gebiedsmonitor/indicatorpaneel.csv   dezelfde rijen als CSV (UTF-8 met BOM, `;`, decimale komma)

Zelfde rechten als de rest van /api/gebiedsmonitor: open, of bij VIEWER_TOEGANG=inloggen alleen met
rol lezer of beheerder (middleware, ADR 0009). Waarden met n onder de drempel gaan niet naar buiten
(leeg, status `onderdrukt`); zie omnitwin.services.indicatorpaneel_service.
"""

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from omnitwin import toegang
from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.services.indicatorpaneel_service import (
    IndicatorpaneelService,
    csv_bestandsnaam,
    lees_gebied_ids,
    maak_csv,
)

router = APIRouter(prefix="/api/gebiedsmonitor", tags=["Gebiedsmonitor"])


def _paneel(db, indicator_uuid, gebied_ids, jaar, gebiedstype_id, gemeente_code, met_gebieden=True):
    toegang.vereis_indicator(db, indicator_uuid)  # interne indicator zonder rol: 401/403 (#254)
    try:
        return IndicatorpaneelService(db).paneel(
            str(indicator_uuid),
            lees_gebied_ids(gebied_ids),
            jaar=jaar,
            gebiedstype_id=str(gebiedstype_id) if gebiedstype_id else None,
            gemeente_code=gemeente_code or None,
            met_gebieden=met_gebieden,
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


_GEBIED_IDS = Query(
    None,
    description="Kommagescheiden gebied-id's (de selectie). Leeg: alle gebieden "
    "van gebiedstype_id (in gemeente_code), zoals op de kaart.",
)
_JAAR = Query(None, description="Jaar; leeg = per gebied de recentste waarde")
_GEMEENTE = Query(None, pattern=r"^[0-9]{4}$", description="Gemeentecode (CBS, 4 cijfers)")


@router.get("/indicatorpaneel")
def indicatorpaneel(
    indicator_uuid: UUID,
    gebied_ids: str | None = _GEBIED_IDS,
    jaar: int | None = _JAAR,
    gebiedstype_id: UUID | None = None,
    gemeente_code: str | None = _GEMEENTE,
    gebieden: bool = Query(
        True,
        description="false: zonder gebied_ids geen waarden per gebied, alleen indicator, bronnen en gemeentegemiddelde",
    ),
    db: Session = Depends(get_db),
):
    """Indicator (beschrijving, eenheid), bronnen (titel, uitgever, licentie, jaargangen), de waarde per
    gebied (onderdrukt = leeg met status) en het gemeentegemiddelde (ongewogen, referentiegroep)."""
    return _paneel(db, indicator_uuid, gebied_ids, jaar, gebiedstype_id, gemeente_code, met_gebieden=gebieden)


@router.get("/indicatorpaneel.csv", response_class=Response)
def indicatorpaneel_csv(
    indicator_uuid: UUID,
    gebied_ids: str | None = _GEBIED_IDS,
    jaar: int | None = _JAAR,
    gebiedstype_id: UUID | None = None,
    gemeente_code: str | None = _GEMEENTE,
    db: Session = Depends(get_db),
):
    """CSV van het paneel: UTF-8 met BOM, puntkomma, decimale komma. Kolommen: gebied-code, gebied-naam,
    indicator, jaar, waarde, eenheid, bron, status (gemeten | onderdrukt | geen-data | gemeentegemiddelde)."""
    paneel = _paneel(db, indicator_uuid, gebied_ids, jaar, gebiedstype_id, gemeente_code)
    naam = csv_bestandsnaam(paneel, dt.date.today().isoformat())
    return Response(
        content=maak_csv(paneel).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{naam}"', "Cache-Control": "no-store"},
    )
