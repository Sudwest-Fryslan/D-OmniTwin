"""
Grounding-controle voor AI-teksten (#88): komt elk getal in de tekst uit de brondata?

Gebruikt door tests/integration/test_llm.py (echt model) en getest in
tests/unit/test_grounding.py (zonder model).

Een getal in de tekst is 'gegrond' als het, eventueel na afronden, overeenkomt met een
getal in de bron (de data waarmee de prompt is gebouwd):
- gelijk na afronden van de bron op 0 of 1 decimaal, of
- binnen 1% van een brongetal,
- vergeleken op absolute waarde ("daling van 5" bij bron -5 telt als gegrond),
- een percentage ("12%") mag ook als fractie in de bron staan (0,12).

Nederlandse notatie: "53,95" = 53.95, "1.132" = 1132. Omdat een model ook Engelse notatie
kan gebruiken, telt voor dubbelzinnige getallen ("1.132", "1,132") elke lezing mee.

Triviaal (nooit een overtreding): 0-3 (rangtelwoorden/opsommingen), jaartallen
2000-2030 en getallen direct gevolgd door 'woorden' (lengte-instructie uit de prompt).
"""

import json
import re

# Getal: optioneel minteken, cijfers met optionele duizendtal-groepen en decimalen,
# niet vast aan letters/cijfers (dus geen '19000002' uit 'BU19000002', geen '2e').
_GETAL = re.compile(
    r"(?<![\w.,])"
    r"(?P<teken>[-−])?"
    r"(?P<getal>\d+(?:[.,]\d+)*)"
    r"(?![\w])"
    r"(?P<pct>\s?(?:%|procent\b))?"
)
_WOORDEN_ACHTER = re.compile(r"\s*woorden\b", re.IGNORECASE)

TRIVIAAL_MAX = 3
JAARTAL_MIN, JAARTAL_MAX = 2000, 2030


def lezingen(getal: str) -> set:
    """Alle plausibele numerieke lezingen van een getal-string (NL en EN notatie)."""
    kandidaten = set()
    # Nederlands: '.' duizendtallen, ',' decimaal
    nl = getal
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", nl) or "." not in nl:
        try:
            kandidaten.add(float(nl.replace(".", "").replace(",", ".")))
        except ValueError:
            pass
    # Engels: ',' duizendtallen, '.' decimaal
    en = getal
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", en) or "," not in en:
        try:
            kandidaten.add(float(en.replace(",", "")))
        except ValueError:
            pass
    # Eén scheidingsteken zonder duizendtal-patroon ('53,95', '53.95'): decimaal
    if re.fullmatch(r"\d+[.,]\d+", getal):
        kandidaten.add(float(getal.replace(",", ".")))
    return kandidaten


def getallen_in_tekst(tekst: str) -> list:
    """Lijst van (origineel, lezingen, is_percentage, is_triviaal) voor elk getal in de tekst."""
    resultaat = []
    for m in _GETAL.finditer(tekst):
        raw = m.group(0).strip()
        waarden = lezingen(m.group("getal"))
        if not waarden:
            continue
        if m.group("teken"):
            waarden = {-w for w in waarden}
        is_pct = bool(m.group("pct"))
        triviaal = _WOORDEN_ACHTER.match(tekst, m.end()) or (
            not is_pct
            and any(w == int(w) and (abs(w) <= TRIVIAAL_MAX or JAARTAL_MIN <= w <= JAARTAL_MAX) for w in waarden)
        )
        resultaat.append((raw, waarden, is_pct, bool(triviaal)))
    return resultaat


def getallen_in_bron(bron) -> list:
    """Alle getallen in een (geneste) bron: numerieke waarden én getallen in strings."""
    uit = []

    def loop(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            uit.append(float(x))
        elif isinstance(x, str):
            for _, waarden, _, _ in getallen_in_tekst(x):
                uit.extend(waarden)
        elif isinstance(x, dict):
            for v in x.values():
                loop(v)
        elif isinstance(x, (list, tuple, set)):
            for v in x:
                loop(v)

    loop(bron)
    return uit


def _past(t: float, s: float) -> bool:
    t, s = abs(t), abs(s)
    if t == s or round(s) == t or round(s, 1) == t:
        return True
    return s != 0 and abs(t - s) <= 0.01 * s


def is_gegrond(waarden: set, is_pct: bool, bron_getallen: list) -> bool:
    for t in waarden:
        kandidaten = [t, t / 100] if is_pct else [t]
        if any(_past(k, s) for k in kandidaten for s in bron_getallen):
            return True
    return False


def ongegronde_getallen(tekst: str, bron) -> list:
    """Getallen (zoals in de tekst geschreven) die niet in de bron voorkomen."""
    bron_getallen = getallen_in_bron(bron)
    return [
        raw
        for raw, waarden, is_pct, triviaal in getallen_in_tekst(tekst)
        if not triviaal and not is_gegrond(waarden, is_pct, bron_getallen)
    ]


def grounding_melding(label: str, tekst: str, bron, ongegrond: list) -> str:
    """Leesbare assertion-melding: welke getallen, in welke zin, en wat de bron bevatte."""
    zinnen = []
    for raw in ongegrond:
        i = tekst.find(raw)
        zinnen.append(f"  - '{raw}' in: …{tekst[max(0, i - 80) : i + len(raw) + 40]}…")
    bron_getallen = sorted({round(s, 2) for s in getallen_in_bron(bron)})
    return (
        f"{label}: {len(ongegrond)} getal(len) niet in de brondata:\n"
        + "\n".join(zinnen)
        + f"\n  brongetallen ({len(bron_getallen)}): {bron_getallen[:60]}"
        + ("…" if len(bron_getallen) > 60 else "")
        + f"\n  bron: {json.dumps(bron, ensure_ascii=False)[:600]}"
    )
