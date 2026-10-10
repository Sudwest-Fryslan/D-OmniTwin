"""
AI-usecases: vrijgave (#307) en logboek (#313).

Publiek (alleen-lezen, geen logins):
- ``GET /api/ai/usecases``: per usecase open of dicht, de reden, versie en geldig tot;
- ``GET /api/ai/usecases/{code}/verklaring``: de actuele verklaring als PDF ("meer informatie").

Beheer (``vereis_admin``: sessie, bearer met rol ``beheerder`` of ``X-Admin-Key``), onder /api/admin/ai:
- usecases met wie en wanneer, verklaring uploaden (PDF + versie + geldig tot), noodstop en hervatten;
- het vrijgavelogboek, het AI-logboek (filter, CSV-export, controle van de hashketen) en de bewaartermijn.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from omnitwin import ai_logboek, ai_vrijgave
from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.routers.auth import vereis_admin
from omnitwin.services.logging_service import AppLogger

router = APIRouter(prefix="/api/ai/usecases", tags=["AI-vrijgave"])
admin_router = APIRouter(prefix="/api/admin/ai", tags=["AI-vrijgave (beheer)"],
                         dependencies=[Depends(vereis_admin)])

Code = Literal["A", "B", "C"]
Status = Literal["uitgevoerd", "geweigerd", "fout", "opgeschoond"]
LogUsecase = Literal["A", "B", "C", "X", "-"]


def _iso(w):
    return w.isoformat() if isinstance(w, (dt.date, dt.datetime)) else w


def _json(r: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (str(v) if k.endswith("_id") and v is not None else _iso(v)) for k, v in r.items()}


def _publiek(s: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "code": s["code"], "naam": s["naam"], "omschrijving": s["omschrijving"],
        "open": s["open"], "reden": s["reden"], "versie": s["versie"], "geldig_tot": _iso(s["geldig_tot"]),
        "verklaring_url": f"/api/ai/usecases/{s['code']}/verklaring" if s["verklaring_id"] else None,
    }


def _wie(gebruiker: dict) -> str:
    return str(gebruiker.get("username") or gebruiker.get("user_id") or "onbekend")[:200]


def _audit(gebruiker: dict, tekst: str) -> None:
    AppLogger.info(f"AI-vrijgave: {tekst} door '{_wie(gebruiker)}'", category="ADMIN")


# ── Publiek ──────────────────────────────────────────────────────────────────

@router.get("")
def publieke_status(db: Session = Depends(get_db)):
    """Per AI-usecase: open of dicht, reden (open, geen_verklaring, verlopen, stilgezet), versie en geldig tot."""
    return [_publiek(s) for s in ai_vrijgave.standen(db)]


@router.get("/{code}/verklaring", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}, 404: {"description": "Geen verklaring"}})
def verklaring(code: Code = Path(...), db: Session = Depends(get_db)):
    """De actuele verklaring (DPIA, IAMA of besluit) van een AI-usecase, als PDF."""
    v = ai_vrijgave.verklaring_pdf(db, code)
    if not v:
        raise HTTPException(status_code=404, detail="Voor deze AI-usecase is geen verklaring geüpload.")
    return Response(content=bytes(v["pdf"]), media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="ai-usecase-{code}-verklaring.pdf"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-cache",
        "ETag": f'"{v["sha256"]}"',
    })


# ── Beheer: vrijgave ─────────────────────────────────────────────────────────

@admin_router.get("/usecases")
def beheer_status(db: Session = Depends(get_db)):
    """Usecases met verklaring, wie hem uploadde en wanneer, en de noodstop."""
    ai_vrijgave.registreer_verlopen(db)
    return [{**_json(s), "verklaring_url": _publiek(s)["verklaring_url"]} for s in ai_vrijgave.standen(db)]


@admin_router.post("/usecases/{code}/verklaring")
def upload_verklaring(
    code: Code = Path(...),
    bestand: UploadFile = File(..., description="De verklaring als PDF (hoogstens 20 MB)"),
    versie: str = Form(..., description="Versie van de applicatie of usecase waarop de verklaring slaat"),
    geldig_tot: dt.date = Form(..., description="Laatste dag waarop de verklaring geldt (JJJJ-MM-DD)"),
    db: Session = Depends(get_db),
    gebruiker: dict = Depends(vereis_admin),
):
    """Verklaring uploaden: de usecase gaat open tot en met geldig_tot (een noodstop wordt opgeheven)."""
    inhoud = bestand.file.read(ai_vrijgave.MAX_PDF + 1)
    try:
        uit = ai_vrijgave.upload(db, code, versie, geldig_tot, bestand.filename, inhoud,
                                 bestand.content_type, _wie(gebruiker))
    except GebruikersFout as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    _audit(gebruiker, f"verklaring usecase {code} geüpload (versie {versie.strip()[:50]}, geldig tot {geldig_tot})")
    return uit


class Noodstop(BaseModel):
    toelichting: Optional[str] = Field(None, max_length=500)


@admin_router.post("/usecases/{code}/noodstop")
def noodstop(code: Code = Path(...), invoer: Optional[Noodstop] = None, db: Session = Depends(get_db),
             gebruiker: dict = Depends(vereis_admin)):
    """Usecase direct stilzetten (noodstop). De applicatie werkt dan zonder deze AI."""
    ai_vrijgave.zet_noodstop(db, code, True, _wie(gebruiker), invoer.toelichting if invoer else None)
    _audit(gebruiker, f"noodstop usecase {code}")
    return {"code": code, "stilgezet": True}


@admin_router.post("/usecases/{code}/hervatten")
def hervatten(code: Code = Path(...), invoer: Optional[Noodstop] = None, db: Session = Depends(get_db),
              gebruiker: dict = Depends(vereis_admin)):
    """Noodstop opheffen. De usecase is pas weer open met een geldige verklaring."""
    ai_vrijgave.zet_noodstop(db, code, False, _wie(gebruiker), invoer.toelichting if invoer else None)
    _audit(gebruiker, f"noodstop opgeheven usecase {code}")
    return {"code": code, "stilgezet": False}


@admin_router.get("/vrijgavelog")
def vrijgavelog(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    """Upload, noodstop, hervat, verlopen en bewaartermijn: wie (login) en wanneer."""
    return [_json(r) for r in ai_vrijgave.vrijgave_log(db, limit)]


# ── Beheer: AI-logboek ───────────────────────────────────────────────────────

@admin_router.get("/logboek")
def logboek(
    usecase: Optional[LogUsecase] = None,
    status: Optional[Status] = None,
    van: Optional[dt.date] = None,
    tot: Optional[dt.date] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Het AI-logboek, nieuwste eerst, met filter op usecase, status en datum."""
    uit = ai_logboek.lees(db, usecase, status, van, tot, limit, offset)
    return {"totaal": uit["totaal"], "regels": [_json(r) for r in uit["regels"]]}


@admin_router.get("/logboek/export", response_class=Response,
                  responses={200: {"content": {"text/csv": {}}}})
def logboek_csv(
    usecase: Optional[LogUsecase] = None,
    status: Optional[Status] = None,
    van: Optional[dt.date] = None,
    tot: Optional[dt.date] = None,
    db: Session = Depends(get_db),
):
    """Het AI-logboek als CSV (puntkomma, UTF-8), met dezelfde filters; hoogstens 100.000 regels."""
    regels = ai_logboek.lees(db, usecase, status, van, tot, limit=100_000, offset=0)["regels"]
    naam = f"ai-logboek-{dt.date.today().isoformat()}.csv"
    return Response(content="﻿" + ai_logboek.als_csv(regels), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{naam}"', "Cache-Control": "no-store"})


@admin_router.get("/logboek/controle")
def logboek_controle(db: Session = Depends(get_db)):
    """Rekent de hashketen na: ok, aantal regels, eerste en laatste id, en de eerste afwijkingen."""
    return ai_logboek.controleer(db)


class Bewaartermijn(BaseModel):
    bewaartermijn_dagen: int = Field(..., ge=ai_logboek.MIN_BEWAARTERMIJN, le=ai_logboek.MAX_BEWAARTERMIJN)


@admin_router.get("/bewaartermijn")
def lees_bewaartermijn(db: Session = Depends(get_db)):
    return _json(ai_logboek.lees_bewaartermijn(db))


@admin_router.put("/bewaartermijn")
def zet_bewaartermijn(invoer: Bewaartermijn, db: Session = Depends(get_db),
                      gebruiker: dict = Depends(vereis_admin)):
    """Bewaartermijn van het AI-logboek (dagen, 30 tot 3650). Opschonen gebeurt dagelijks."""
    ai_logboek.zet_bewaartermijn(db, invoer.bewaartermijn_dagen, _wie(gebruiker))
    _audit(gebruiker, f"bewaartermijn AI-logboek op {invoer.bewaartermijn_dagen} dagen gezet")
    return _json(ai_logboek.lees_bewaartermijn(db))
