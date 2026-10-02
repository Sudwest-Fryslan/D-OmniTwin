"""
De eigen organisatie van deze instantie, als data (#231, ADR 0007).

Eén D-OmniTwin-instantie hoort bij één organisatie. Naam, gemeentecode(s) van het
eigen gebied, standaard-benchmarkgebied, contactpunt en logo's staan in de tabel
``organisatie`` (vulling: ``db/stuurdata/organisatie.sql``), niet in de code.

Regel: code die "de eigen gemeente" nodig heeft, vraagt die hier op
(``eigen_gemeente_code``) en neemt nooit een vaste code aan.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from omnitwin.services.logging_service import AppLogger

STANDAARD_THEMA = "d-omnitwin"
_THEMA = re.compile(r"^[a-z0-9-]+$")
THEMA_MAP = Path(__file__).resolve().parents[3] / "static" / "css" / "themes"


def veilig_thema(thema: Optional[str]) -> str:
    """Themanaam alleen met [a-z0-9-]; anders het standaardthema."""
    return thema if isinstance(thema, str) and _THEMA.fullmatch(thema) else STANDAARD_THEMA


def thema_css(org: Optional[Dict[str, Any]], themamap: Path = THEMA_MAP) -> Optional[str]:
    """URL van static/css/themes/<thema>.css als dat bestand bestaat, anders None."""
    thema = veilig_thema(org.get("thema") if org else None)
    return f"/static/css/themes/{thema}.css" if (themamap / f"{thema}.css").is_file() else None


_SQL = text("""
    SELECT code, naam, korte_naam, oin, gemeente_codes, benchmark_provincie,
           contact_email, logos, thema
    FROM public.organisatie
    LIMIT 1
""")


def _als_dict(rij) -> Dict[str, Any]:
    m = dict(rij._mapping)
    codes: List[str] = [str(c) for c in (m.get("gemeente_codes") or [])]
    logos = m.get("logos") or []
    return {
        "code": m["code"],
        "naam": m["naam"],
        "korte_naam": m.get("korte_naam"),
        "oin": m.get("oin"),
        "gemeente_codes": codes,
        "standaard_gemeente_code": codes[0] if codes else None,
        "benchmark_provincie": m.get("benchmark_provincie"),
        "contact_email": m.get("contact_email"),
        "thema": veilig_thema(m.get("thema")),
        "logos": [
            {"pad": l.get("pad"), "naam": l.get("naam"), "rol": l.get("rol", "partner")}
            for l in logos
            if isinstance(l, dict) and l.get("pad")
        ],
    }


def lees_organisatie(db: Session) -> Optional[Dict[str, Any]]:
    """De organisatie van deze instantie, of None als die (nog) niet is ingericht.

    Een database zonder de tabel (migratie V030 nog niet toegepast) geeft ook None.
    """
    try:
        rij = db.execute(_SQL).fetchone()
    except SQLAlchemyError as e:
        db.rollback()
        AppLogger.warning(f"Organisatie niet te lezen: {e.__class__.__name__}", category="SERVER")
        return None
    return _als_dict(rij) if rij else None


def eigen_gemeente_code(db: Session) -> Optional[str]:
    """De standaard-gemeentecode van de eigen organisatie (de eerste uit gemeente_codes)."""
    org = lees_organisatie(db)
    return org["standaard_gemeente_code"] if org else None
