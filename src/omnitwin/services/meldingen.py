"""
Service voor de terugmeldvoorziening (#311).

Centraal regielogboek voor meldingen van gebruikers over data, AI, techniek en suggesties.
Conform het principe "bron blijft bron" fungeert D-OmniTwin als de regiekamer waar fouten
worden geregistreerd en eventueel doorgestuurd naar de respectievelijke bronhouders.

Privacy & AVG:
- Meldingen zijn standaard anoniem; optioneel e-mailadres voor melders die terugkoppeling wensen.
- Zodra een melding de status 'afgehandeld' of 'afgewezen' krijgt, wordt het e-mailadres gewist (NULL).
- Oudere meldingen worden na BEWAAR_DAGEN (standaard 365 dagen) verwijderd door de opruimtaak.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin.fouten import GebruikersFout
from omnitwin.services.logging_service import AppLogger

BEWAAR_DAGEN: int = 365

TOEGESTANE_TYPES = {"data", "ai", "systeem", "overig"}
TOEGESTANE_STATUSSEN = {"nieuw", "doorgestuurd_naar_bron", "in_behandeling", "afgehandeld", "afgewezen"}
TOEGESTANE_CONTEXT_SLEUTELS = {
    "pagina",
    "versie",
    "gebied_ids",
    "indicator_id",
    "peiljaar",
    "ai_usecase",
    "vraag",
    "resultaat",
    "bron",
}
MAX_CONTEXT_BYTES = 10_240


def valideer_context(ruwe_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Filtert en begrenst context-invoer op vaste sleutels en maximale payload-grootte."""
    if not ruwe_context or not isinstance(ruwe_context, dict):
        return {}

    opgeschoond: Dict[str, Any] = {}
    for sleutel, waarde in ruwe_context.items():
        if sleutel not in TOEGESTANE_CONTEXT_SLEUTELS:
            continue
        if waarde is None:
            continue

        if sleutel == "vraag" and isinstance(waarde, str):
            opgeschoond[sleutel] = waarde.strip()[:300]
        elif sleutel == "resultaat" and isinstance(waarde, str):
            opgeschoond[sleutel] = waarde.strip()[:600]
        elif sleutel == "gebied_ids" and isinstance(waarde, list):
            opgeschoond[sleutel] = [str(x)[:50] for x in waarde[:50]]
        elif isinstance(waarde, (str, int, float, bool)):
            if isinstance(waarde, str):
                opgeschoond[sleutel] = waarde.strip()[:200]
            else:
                opgeschoond[sleutel] = waarde

    gecodeerd = json.dumps(opgeschoond).encode("utf-8")
    if len(gecodeerd) > MAX_CONTEXT_BYTES:
        raise GebruikersFout("Context-gegevens overschrijden de maximale limiet van 10 KB.")

    return opgeschoond


def _naar_dict(rij: Any) -> Dict[str, Any]:
    """Zet een database-rij om naar een veilige dictionary voor API-weergave."""
    context_data = rij.context
    if isinstance(context_data, str):
        try:
            context_data = json.loads(context_data)
        except Exception:
            context_data = {}

    return {
        "id": str(rij.id),
        "type": rij.type,
        "onderwerp": rij.onderwerp,
        "toelichting": rij.toelichting,
        "context": context_data or {},
        "melder_email": rij.melder_email,
        "status": rij.status,
        "notitie_beheer": rij.notitie_beheer,
        "aangemaakt_op": rij.aangemaakt_op.isoformat() if rij.aangemaakt_op else None,
        "bijgewerkt_op": rij.bijgewerkt_op.isoformat() if rij.bijgewerkt_op else None,
    }


def maak_melding(
    db: Session,
    type_: str,
    onderwerp: str,
    toelichting: str,
    context_data: Optional[Dict[str, Any]] = None,
    melder_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Maakt een nieuwe melding aan in het regielogboek."""
    if type_ not in TOEGESTANE_TYPES:
        raise GebruikersFout(f"Ongeldig type melding: {type_}")

    onderwerp_schoon = onderwerp.strip()
    if not (1 <= len(onderwerp_schoon) <= 120):
        raise GebruikersFout("Onderwerp moet tussen 1 en 120 tekens lang zijn.")

    toelichting_schoon = toelichting.strip()
    if not (1 <= len(toelichting_schoon) <= 4000):
        raise GebruikersFout("Toelichting moet tussen 1 en 4000 tekens lang zijn.")

    veilige_context = valideer_context(context_data)
    email_schoon = melder_email.strip() if melder_email and melder_email.strip() else None

    stmt = text("""
        INSERT INTO app.gebruiker_meldingen (
            type, onderwerp, toelichting, context, melder_email
        ) VALUES (
            :type, :onderwerp, :toelichting, CAST(:context AS jsonb), :email
        )
        RETURNING id, type, onderwerp, toelichting, context, melder_email, status, notitie_beheer, aangemaakt_op, bijgewerkt_op
    """)

    rij = db.execute(stmt, {
        "type": type_,
        "onderwerp": onderwerp_schoon,
        "toelichting": toelichting_schoon,
        "context": json.dumps(veilige_context),
        "email": email_schoon,
    }).mappings().first()
    db.commit()

    return _naar_dict(rij)


def haal_tellingen_per_status(db: Session) -> Dict[str, int]:
    """Geeft de aantallen meldingen per status terug voor statusfilters en tellers."""
    tellingen = {s: 0 for s in TOEGESTANE_STATUSSEN}
    stmt = text("""
        SELECT status, count(*) AS aantal
        FROM app.gebruiker_meldingen
        GROUP BY status
    """)
    for r in db.execute(stmt).mappings().all():
        if r.status in tellingen:
            tellingen[r.status] = r.aantal
    return tellingen


def zoek_meldingen(
    db: Session,
    status: Optional[str] = None,
    type_: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Haalt een gepagineerde lijst meldingen op met tellingen en filtering."""
    if status and status not in TOEGESTANE_STATUSSEN:
        raise GebruikersFout(f"Ongeldige status-filter: {status}")
    if type_ and type_ not in TOEGESTANE_TYPES:
        raise GebruikersFout(f"Ongeldig type-filter: {type_}")

    limit_veilig = max(1, min(limit, 100))
    offset_veilig = max(0, offset)

    voorwaarden = []
    params: Dict[str, Any] = {"limit": limit_veilig, "offset": offset_veilig}

    if status:
        voorwaarden.append("status = :status")
        params["status"] = status
    if type_:
        voorwaarden.append("type = :type")
        params["type"] = type_

    where_clause = f"WHERE {' AND '.join(voorwaarden)}" if voorwaarden else ""

    tellingen = haal_tellingen_per_status(db)

    count_stmt = text(f"SELECT count(*) AS totaal FROM app.gebruiker_meldingen {where_clause}")
    totaal = db.execute(count_stmt, params).scalar() or 0

    select_stmt = text(f"""
        SELECT id, type, onderwerp, toelichting, context, melder_email, status, notitie_beheer, aangemaakt_op, bijgewerkt_op
        FROM app.gebruiker_meldingen
        {where_clause}
        ORDER BY aangemaakt_op DESC
        LIMIT :limit OFFSET :offset
    """)

    rijen = db.execute(select_stmt, params).mappings().all()
    items = [_naar_dict(r) for r in rijen]

    return {
        "items": items,
        "tellingen": tellingen,
        "totaal": totaal,
        "limit": limit_veilig,
        "offset": offset_veilig,
    }


def haal_melding(db: Session, melding_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Haalt één melding op inclusief volledige details."""
    stmt = text("""
        SELECT id, type, onderwerp, toelichting, context, melder_email, status, notitie_beheer, aangemaakt_op, bijgewerkt_op
        FROM app.gebruiker_meldingen
        WHERE id = :id
    """)
    rij = db.execute(stmt, {"id": melding_id}).mappings().first()
    return _naar_dict(rij) if rij else None


def werk_melding_bij(
    db: Session,
    melding_id: uuid.UUID,
    status: Optional[str] = None,
    notitie_beheer: Optional[str] = None,
    beheerder: str = "onbekend",
) -> Dict[str, Any]:
    """
    Werkt de status of interne notitie van een melding bij.
    Conform AVG: Zodra status 'afgehandeld' of 'afgewezen' wordt, wordt melder_email gewist.
    """
    bestaand = haal_melding(db, melding_id)
    if not bestaand:
        raise GebruikersFout("Melding niet gevonden.")

    updates = ["bijgewerkt_op = now()"]
    params: Dict[str, Any] = {"id": melding_id}

    nieuwe_status = status or bestaand["status"]
    if status is not None:
        if status not in TOEGESTANE_STATUSSEN:
            raise GebruikersFout(f"Ongeldige status: {status}")
        updates.append("status = :status")
        params["status"] = status

        # AVG bewaartermijn e-mail: wissen bij afhandeling of afwijzing
        if status in ("afgehandeld", "afgewezen"):
            updates.append("melder_email = NULL")

    if notitie_beheer is not None:
        notitie_schoon = notitie_beheer.strip()[:4000] if notitie_beheer.strip() else None
        updates.append("notitie_beheer = :notitie")
        params["notitie"] = notitie_schoon

    stmt = text(f"""
        UPDATE app.gebruiker_meldingen
        SET {', '.join(updates)}
        WHERE id = :id
        RETURNING id, type, onderwerp, toelichting, context, melder_email, status, notitie_beheer, aangemaakt_op, bijgewerkt_op
    """)

    rij = db.execute(stmt, params).mappings().first()
    db.commit()

    # Audit logging in categorie ADMIN (alleen ID en nieuwe status, geen persoonsgegevens)
    AppLogger.info(
        f"Melding {melding_id} bijgewerkt naar status '{nieuwe_status}' door '{beheerder}'",
        category="ADMIN",
    )

    return _naar_dict(rij)


def ruim_op(db_or_conn: Any, dagen: int = BEWAAR_DAGEN) -> int:
    """Verwijdert meldingen die langer dan `dagen` geleden voor het laatst zijn gewijzigd."""
    stmt = text("""
        DELETE FROM app.gebruiker_meldingen
        WHERE bijgewerkt_op < now() - make_interval(days => :dagen)
    """)
    res = db_or_conn.execute(stmt, {"dagen": int(dagen)})
    db_or_conn.commit()
    return res.rowcount
