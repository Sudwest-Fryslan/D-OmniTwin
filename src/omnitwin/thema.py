"""Thema per organisatie (#89): welk NL Design System-themabestand de frontend laadt.

Een thema is een CSS-bestand `static/css/themes/<naam>.css` met NLDS-basistokens (`--basis-*`).
De naam komt uit de organisatiegegevens van de instantie (inrichting = data, ADR 0007) en belandt
in een URL in de template. Daarom alleen kleine letters, cijfers en koppeltekens; elke andere
waarde, of een naam zonder bestand, valt terug op het standaardthema.

Uitleg: docs/9-beheer/thema-s.md.
"""

from __future__ import annotations

import re
from pathlib import Path

STANDAARD_THEMA = "d-omnitwin"
THEMA_MAP = Path("static") / "css" / "themes"
_GELDIGE_NAAM = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def is_geldige_themanaam(naam: object) -> bool:
    """True als `naam` alleen uit [a-z0-9-] bestaat (geen leeg, geen begin/eind- of dubbel koppelteken)."""
    return isinstance(naam, str) and len(naam) <= 64 and _GELDIGE_NAAM.fullmatch(naam) is not None


def beschikbare_themas(map_: Path = THEMA_MAP) -> list[str]:
    """Namen van de themabestanden die er staan, gesorteerd."""
    return sorted(p.stem for p in Path(map_).glob("*.css") if is_geldige_themanaam(p.stem))


def kies_thema(naam: object, map_: Path = THEMA_MAP) -> str:
    """De themanaam om te laden: `naam` als die geldig is en het bestand bestaat, anders het standaardthema."""
    if is_geldige_themanaam(naam) and (Path(map_) / f"{naam}.css").is_file():
        return naam  # type: ignore[return-value]
    return STANDAARD_THEMA
