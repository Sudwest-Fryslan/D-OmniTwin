"""
Vrijgave van AI-usecases (#307): de enige poort voor AI in de applicatie.

Usecases (afgesproken met de AI Officer):
    A  Assistent              chat: intentie, toelichting, formulering van een datavraag (taalmodel)
    B  Samenvatting/rapport   domein-, totaal- en benchmarksamenvattingen in rapporten (taalmodel)
    C  Zoeken (semantisch)    zoeken op betekenis met het embeddingmodel (Kompas-zoeken, chatrelevantie,
                              kandidaten bij deduplicatie)
Al het andere (LLM-oordeel bij deduplicatie, ontologie genereren) valt onder BUITEN en staat altijd dicht.

Open = er is een verklaring (PDF, geüpload in de beheerinterface) met `geldig_tot` op of na vandaag,
en functioneel beheer heeft de usecase niet stilgezet (noodstop). Standaard dicht: zonder verklaring,
na de einddatum, bij een noodstop, en ook als de status niet te lezen is (database weg).
Geen omgevingsvariabele als schakelaar.

Gebruik: `poort(usecase, functie, taak)` vóór elke AI-aanroep met gebruikersinvoer; die logt een
weigering in het AI-logboek (#313). `LLMService._call_llm` roept hem zelf ook aan (verplichte
parameter `usecase`), zodat een nieuw pad naar het taalmodel er niet omheen kan.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date
from typing import Any

from sqlalchemy import text

from omnitwin import ai_logboek

logger = logging.getLogger(__name__)

A, B, C = "A", "B", "C"
BUITEN = "X"  # geen vrijgegeven usecase: altijd dicht
SYSTEEM = "systeem"  # 'door' bij een automatische noodstop
USECASES = {A: "Assistent", B: "Samenvatting/rapport", C: "Zoeken (semantisch)"}

OPEN, GEEN_VERKLARING, VERLOPEN, STILGEZET = "open", "geen_verklaring", "verlopen", "stilgezet"

MELDINGEN = {
    A: "De AI-assistent staat uit; dit antwoord is samengesteld zonder taalmodel.",
    B: "De AI-samenvatting staat uit: AI-usecase B (Samenvatting/rapport) is niet vrijgegeven.",
    C: "Zoeken op betekenis staat uit; er is gezocht op trefwoorden en synoniemen.",
    BUITEN: "Deze AI-functie valt niet onder een vrijgegeven AI-usecase (A, B of C) en staat daarom uit.",
}

MAX_PDF = 20 * 1024 * 1024
PDF_TYPES = ("application/pdf",)
_STUURTEKENS = re.compile(r"[\x00-\x1f\x7f]")


def melding(usecase: str) -> str:
    return MELDINGEN.get(usecase, MELDINGEN[BUITEN])


def beoordeel(geldig_tot: date | None, stilgezet: bool, vandaag: date) -> tuple[bool, str]:
    """(open, reden) voor een usecase. Zonder verklaring dicht; geldig tot en met geldig_tot."""
    if geldig_tot is None:
        return False, GEEN_VERKLARING
    if stilgezet:
        return False, STILGEZET
    if geldig_tot < vandaag:
        return False, VERLOPEN
    return True, OPEN


_STAND_SQL = """
    SELECT u.code, u.naam, u.omschrijving, u.stilgezet, u.status_door, u.status_op, u.stilgezet_reden,
           v.id AS verklaring_id, v.versie, v.geldig_tot, v.bestandsnaam, v.grootte, v.sha256,
           v.geupload_door, v.geupload_op
    FROM app.ai_usecases u
    LEFT JOIN LATERAL (
        SELECT id, versie, geldig_tot, bestandsnaam, grootte, sha256, geupload_door, geupload_op
        FROM app.ai_verklaringen WHERE usecase = u.code
        ORDER BY geupload_op DESC, id DESC LIMIT 1
    ) v ON true
"""


def _lees_standen(code: str | None = None, db=None) -> list[dict[str, Any]]:
    sql = text(_STAND_SQL + (" WHERE u.code = :code" if code else "") + " ORDER BY u.code")
    params = {"code": code} if code else {}
    if db is not None:
        return [dict(r) for r in db.execute(sql, params).mappings()]
    from omnitwin.database import engine

    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).mappings()]


def standen(db=None, vandaag: date | None = None) -> list[dict[str, Any]]:
    """Alle usecases met verklaring, open/dicht en de reden (voor beheer; bevat logins)."""
    vandaag = vandaag or date.today()
    uit = []
    for r in _lees_standen(db=db):
        r["open"], r["reden"] = beoordeel(r["geldig_tot"], r["stilgezet"], vandaag)
        uit.append(r)
    return uit


def is_open(usecase: str) -> bool:
    """Mag AI-usecase `usecase` nu draaien? Bij twijfel (onbekend, database weg): nee."""
    if usecase not in USECASES:
        return False
    try:
        rijen = _lees_standen(usecase)
    except Exception as e:  # noqa: BLE001 - dicht bij twijfel
        logger.warning("AI-vrijgave: status van usecase %s niet te lezen (%s): dicht", usecase, type(e).__name__)
        return False
    if not rijen:
        return False
    return beoordeel(rijen[0]["geldig_tot"], rijen[0]["stilgezet"], date.today())[0]


def poort(usecase: str, functie: str, taak: str | None = None) -> bool:
    """True als de usecase open is; anders False en een regel 'geweigerd' in het AI-logboek."""
    if is_open(usecase):
        return True
    ai_logboek.schrijf(
        usecase if usecase in USECASES else BUITEN, functie, ai_logboek.GEWEIGERD, taak=taak, resultaat=melding(usecase)
    )
    return False


# ── Beheer: verklaring, noodstop, logboek ────────────────────────────────────


def _code(usecase: str) -> str:
    if usecase not in USECASES:
        from omnitwin.fouten import GebruikersFout

        raise GebruikersFout(f"Onbekende AI-usecase: {usecase}")
    return usecase


def valideer_pdf(inhoud: bytes, content_type: str | None) -> None:
    """Alleen een PDF (content-type en de eerste bytes %PDF), niet leeg en hoogstens MAX_PDF."""
    from omnitwin.fouten import GebruikersFout

    if (content_type or "").split(";")[0].strip().lower() not in PDF_TYPES:
        raise GebruikersFout("De verklaring moet een PDF zijn (application/pdf).")
    if not inhoud:
        raise GebruikersFout("Het bestand is leeg.")
    if len(inhoud) > MAX_PDF:
        raise GebruikersFout(f"Het bestand is groter dan {MAX_PDF // (1024 * 1024)} MB.")
    if not inhoud.startswith(b"%PDF"):
        raise GebruikersFout("Het bestand is geen PDF.")


def valideer_versie(versie: str) -> str:
    from omnitwin.fouten import GebruikersFout

    versie = (versie or "").strip()
    if not 1 <= len(versie) <= 100 or _STUURTEKENS.search(versie):
        raise GebruikersFout("Versie is verplicht (hoogstens 100 tekens, zonder stuurtekens).")
    return versie


def nette_bestandsnaam(naam: str | None) -> str:
    naam = re.split(r"[\\/]", naam or "")[-1]
    naam = re.sub(r"[^A-Za-z0-9._ -]+", "_", naam).strip(" .")[:200]
    return naam or "verklaring.pdf"


def upload(
    db,
    usecase: str,
    versie: str,
    geldig_tot: date,
    bestandsnaam: str | None,
    inhoud: bytes,
    content_type: str | None,
    door: str,
    vandaag: date | None = None,
) -> dict[str, Any]:
    """Nieuwe verklaring: de usecase gaat open (een noodstop wordt opgeheven). Vastgelegd met login en tijd."""
    from omnitwin.fouten import GebruikersFout

    code = _code(usecase)
    versie = valideer_versie(versie)
    valideer_pdf(inhoud, content_type)
    if geldig_tot < (vandaag or date.today()):
        raise GebruikersFout("'Geldig tot' ligt in het verleden.")
    sha = hashlib.sha256(inhoud).hexdigest()
    vid = db.execute(
        text("""
        INSERT INTO app.ai_verklaringen (usecase, versie, geldig_tot, bestandsnaam, pdf, grootte, sha256, geupload_door)
        VALUES (:code, :versie, :tot, :naam, :pdf, :grootte, :sha, :door) RETURNING id
    """),
        {
            "code": code,
            "versie": versie,
            "tot": geldig_tot,
            "naam": nette_bestandsnaam(bestandsnaam),
            "pdf": inhoud,
            "grootte": len(inhoud),
            "sha": sha,
            "door": door,
        },
    ).scalar()
    db.execute(
        text(
            "UPDATE app.ai_usecases SET stilgezet = false, status_door = :door, status_op = now(), "
            "stilgezet_reden = NULL WHERE code = :code"
        ),
        {"door": door, "code": code},
    )
    db.execute(
        text("""
        INSERT INTO app.ai_vrijgave_log (usecase, actie, door, verklaring_id, versie, geldig_tot, toelichting)
        VALUES (:code, 'verklaring_geupload', :door, :vid, :versie, :tot, :t)
    """),
        {
            "code": code,
            "door": door,
            "vid": vid,
            "versie": versie,
            "tot": geldig_tot,
            "t": f"Verklaring geüpload en usecase actief gemaakt (sha256 {sha[:12]}…)",
        },
    )
    db.commit()
    return {"verklaring_id": str(vid), "sha256": sha}


def zet_noodstop(db, usecase: str, aan: bool, door: str, toelichting: str | None = None) -> None:
    """Noodstop aan (stilzetten) of uit (hervatten); hervatten opent alleen met een geldige verklaring."""
    code = _code(usecase)
    toelichting = ai_logboek.afkappen(toelichting, 500)
    db.execute(
        text(
            "UPDATE app.ai_usecases SET stilgezet = :aan, status_door = :door, status_op = now(), "
            "stilgezet_reden = :reden WHERE code = :code"
        ),
        {"aan": aan, "door": door, "code": code, "reden": toelichting if aan else None},
    )
    db.execute(
        text("INSERT INTO app.ai_vrijgave_log (usecase, actie, door, toelichting) VALUES (:code, :actie, :door, :t)"),
        {"code": code, "actie": "noodstop" if aan else "hervat", "door": door, "t": toelichting},
    )
    db.commit()


def automatische_noodstop(reden: str) -> None:
    """
    Fail-closed (#307, #313): zet A, B en C stil met door = 'systeem' en de reden, in een eigen
    transactie. Vastgelegd in ai_vrijgave_log (alleen voor usecases die nog niet stil stonden); lukt
    dat niet (database onbereikbaar), dan in de applicatielog. Gaat niet vanzelf weer open.
    """
    reden = ai_logboek.afkappen(reden, 500) or "onbekend"
    try:
        from omnitwin.database import engine

        with engine.begin() as conn:
            codes = [
                r[0]
                for r in conn.execute(
                    text("""
                UPDATE app.ai_usecases
                SET stilgezet = true, status_door = :door, status_op = now(), stilgezet_reden = :reden
                WHERE NOT stilgezet RETURNING code
            """),
                    {"door": SYSTEEM, "reden": reden},
                )
            ]
            for code in codes:
                conn.execute(
                    text(
                        "INSERT INTO app.ai_vrijgave_log (usecase, actie, door, toelichting) "
                        "VALUES (:code, 'noodstop', :door, :t)"
                    ),
                    {"code": code, "door": SYSTEEM, "t": f"Automatische noodstop: {reden}"},
                )
        if codes:
            _applicatielog(f"AI: automatische noodstop op {', '.join(codes)}: {reden}")
    except Exception as e:  # noqa: BLE001 - de database is weg: dan staat AI al dicht (is_open faalt)
        _applicatielog(f"AI: automatische noodstop kon niet worden vastgelegd ({type(e).__name__}); reden: {reden}")


def _applicatielog(tekst: str) -> None:
    logger.critical(tekst)
    try:
        from omnitwin.services.logging_service import AppLogger

        AppLogger.critical(tekst, category="SERVER")
    except Exception:  # noqa: BLE001
        pass


def registreer_verlopen(db, vandaag: date | None = None) -> int:
    """Een verlopen verklaring één keer als 'verlopen' in het vrijgavelogboek (automatisch, zonder login)."""
    n = 0
    for s in standen(db, vandaag):
        if s["reden"] != VERLOPEN:
            continue
        al = db.execute(
            text("SELECT 1 FROM app.ai_vrijgave_log WHERE actie = 'verlopen' AND verklaring_id = :v"),
            {"v": s["verklaring_id"]},
        ).fetchone()
        if al:
            continue
        db.execute(
            text("""
            INSERT INTO app.ai_vrijgave_log (usecase, actie, verklaring_id, versie, geldig_tot, toelichting)
            VALUES (:code, 'verlopen', :v, :versie, :tot, 'Automatisch dicht: geldig tot is verstreken')
        """),
            {"code": s["code"], "v": s["verklaring_id"], "versie": s["versie"], "tot": s["geldig_tot"]},
        )
        n += 1
    if n:
        db.commit()
    return n


def vrijgave_log(db, limit: int = 200) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in db.execute(
            text("""
        SELECT id, tijdstip, usecase, actie, door, verklaring_id, versie, geldig_tot, toelichting
        FROM app.ai_vrijgave_log ORDER BY id DESC LIMIT :limit
    """),
            {"limit": limit},
        ).mappings()
    ]


def verklaring_pdf(db, usecase: str) -> dict[str, Any] | None:
    """De actuele verklaring (de nieuwste) van een usecase, of None."""
    r = (
        db.execute(
            text("""
        SELECT pdf, versie, sha256 FROM app.ai_verklaringen WHERE usecase = :code
        ORDER BY geupload_op DESC, id DESC LIMIT 1
    """),
            {"code": _code(usecase)},
        )
        .mappings()
        .fetchone()
    )
    return dict(r) if r else None
