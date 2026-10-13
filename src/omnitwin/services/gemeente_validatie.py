"""
Validatie van SELECTEER_GEMEENTE-acties uit de chat (#140).

Het taalmodel kiest zelf een gemeentecode en een label. Dat gaat mis bij
woonplaatsen: "📍 Gemeente: Bolsward" kwam terug met code 0080 (Leeuwarden),
terwijl Bolsward een woonplaats in Súdwest-Fryslân (1900) is. Een verkeerd
gemeentefilter maakt de kaart leeg.

Regels:
- is de naam in het label een gemeentenaam, dan geldt de code van die gemeente;
- anders moet de code in de tabel `gemeenten` staan én het label die gemeentenaam bevatten;
- anders: herleid de naam in het label via `gebieden` (gebieden waarvan de naam met die plaatsnaam begint,
  zoals "Bolsward-Zuidoost" → 1900). Alleen bij precies één gemeente;
- lukt dat niet, dan vervalt de actie.

`valideer_gemeente_actie` is zuiver (geen database) en daardoor los te testen.
"""

import re
import unicodedata
from collections.abc import Callable, Iterable

from sqlalchemy import text

ACTIE_TYPE = "SELECTEER_GEMEENTE"

# Iconen, spaties en een eventueel voorvoegsel "Gemeente:" vóór de naam in het label
_LABEL_PREFIX = re.compile(r"^[^\w]*(gemeente\s*:?\s*)?", re.IGNORECASE)


def normaliseer(tekst: str) -> str:
    """Kleine letters, zonder accenten en overbodige spaties ("Súdwest-Fryslân" → "sudwest-fryslan")."""
    tekst = unicodedata.normalize("NFKD", tekst or "")
    tekst = "".join(c for c in tekst if not unicodedata.combining(c))
    return " ".join(tekst.lower().split())


def naam_uit_label(label: str) -> str:
    """'📍 Gemeente: Bolsward' → 'Bolsward'."""
    return _LABEL_PREFIX.sub("", (label or "").strip()).strip()


def _begint_met_plaats(gebiedsnaam: str, plaats: str) -> bool:
    """'Bolsward-Zuidoost' begint met 'Bolsward'; 'Bolswardervaart' niet."""
    g, p = normaliseer(gebiedsnaam), normaliseer(plaats)
    if not p or not g.startswith(p):
        return False
    rest = g[len(p) :]
    return rest == "" or rest[0] in " -,("


def gemeente_actie(code: str, naam: str) -> dict[str, str]:
    return {"type": ACTIE_TYPE, "label": f"📍 Gemeente: {naam}", "gemeente_code": code}


def valideer_gemeente_actie(
    actie: dict,
    gemeenten: dict[str, str],
    gebieden_voor: Callable[[str], Iterable[tuple[str, str | None]]] = lambda naam: [],
) -> dict | None:
    """
    Controleer één actie van het taalmodel.

    actie:         dict met type, label, gemeente_code
    gemeenten:     {code: naam} uit de tabel `gemeenten`
    gebieden_voor: plaatsnaam → [(gebiedsnaam, gemeente_code), ...] (kandidaten uit `gebieden`)

    Retourneert de actie (eventueel gecorrigeerd) of None als die moet vervallen.
    Andere actietypes komen ongewijzigd terug.
    """
    if not isinstance(actie, dict) or actie.get("type") != ACTIE_TYPE:
        return actie

    label = actie.get("label") or ""
    code = str(actie.get("gemeente_code") or "").strip()

    naam = naam_uit_label(label)

    # 1. Het label is precies een gemeentenaam: neem de code van die gemeente
    #    (vangt ook "Midden-Groningen" met de code van Groningen af)
    for g_code, g_naam in gemeenten.items():
        if naam and normaliseer(g_naam) == normaliseer(naam):
            return actie if g_code == code else {**actie, **gemeente_actie(g_code, g_naam)}

    # 2. Code bestaat en het label noemt die gemeente: in orde
    if code in gemeenten and normaliseer(gemeenten[code]) in normaliseer(label):
        return actie

    if not naam:
        return None

    # 3. Woonplaats of buurtnaam: herleid via gebieden, alleen bij één gemeente
    codes = {
        g_code
        for g_naam, g_code in gebieden_voor(naam)
        if g_code and g_code in gemeenten and _begint_met_plaats(g_naam, naam)
    }
    if len(codes) == 1:
        g_code = codes.pop()
        return {**actie, **gemeente_actie(g_code, gemeenten[g_code])}

    return None


# ── Database ─────────────────────────────────────────────────────────────────


def laad_gemeenten(db, alleen_met_gebieden: bool = False) -> dict[str, str]:
    """{code: naam} uit `gemeenten`; optioneel alleen gemeenten waarvoor gebieden geladen zijn."""
    sql = "SELECT code, naam FROM gemeenten"
    if alleen_met_gebieden:
        sql += " g WHERE EXISTS (SELECT 1 FROM gebieden b WHERE b.gemeente_code = g.code)"
    sql += " ORDER BY naam"
    return {r[0]: r[1] for r in db.execute(text(sql)).fetchall()}


def gebieden_met_naam(db, plaats: str, limit: int = 50) -> list[tuple[str, str | None]]:
    """Gebieden waarvan de naam met `plaats` begint (fijnere check in _begint_met_plaats)."""
    patroon = plaats.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = db.execute(
        text("SELECT naam, gemeente_code FROM gebieden WHERE naam ILIKE :p AND gemeente_code IS NOT NULL LIMIT :n"),
        {"p": patroon, "n": limit},
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def valideer_gemeente_acties(acties: Iterable[dict], db) -> list[dict]:
    """Valideer alle SELECTEER_GEMEENTE-acties tegen de database; ongeldige vervallen."""
    acties = list(acties or [])
    if not any(isinstance(a, dict) and a.get("type") == ACTIE_TYPE for a in acties):
        return acties
    gemeenten = laad_gemeenten(db)
    resultaat = []
    for a in acties:
        gevalideerd = valideer_gemeente_actie(a, gemeenten, lambda naam: gebieden_met_naam(db, naam))
        if gevalideerd is not None:
            resultaat.append(gevalideerd)
    return resultaat
