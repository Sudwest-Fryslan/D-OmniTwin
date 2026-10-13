"""
De eigen buurt vinden via postcode/adres of locatie (#336), met de PDOK Locatieserver.

"Hoeveel ouderen wonen er bij mij in de buurt?" zonder selectie op de kaart: de assistent vraagt
welke buurt. De gebruiker kan dan een postcode of adres invullen, of (na toestemming in de browser)
zijn locatie gebruiken. Dit zet dat om naar een CBS-buurtcode (BU...):

- adres of postcode: vrij zoeken (free) op type adres; het eerste adres geeft de buurtcode;
- locatie: omgekeerd zoeken (reverse) op type buurt; de identificatie is de buurtcode.

Privacy: adres en coördinaten worden nergens gelogd of bewaard; alleen de buurtcode komt terug.
De Locatieserver is open (geen sleutel), bron BAG en CBS.
"""

import re
from typing import Any, Callable, Dict, Optional

import requests

PDOK_LOCATIESERVER = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"
TIMEOUT = 10

# Ruim om Nederland (WGS84); daarbuiten zoeken heeft geen zin
_NL = {"lat": (50.6, 53.7), "lon": (3.2, 7.3)}
_BUURTCODE = re.compile(r"^BU[0-9A-Z]{8}$")  # CBS: soms met letters, bijv. BU0363AE02


class LocatieFout(Exception):
    """De Locatieserver is niet bereikbaar of gaf een fout."""


def _vraag(pad: str, params: Dict[str, Any], get: Callable[..., Any]) -> Dict[str, Any]:
    try:
        r = get(f"{PDOK_LOCATIESERVER}/{pad}", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        docs = (r.json().get("response") or {}).get("docs") or []
    except (requests.RequestException, ValueError) as e:
        raise LocatieFout(type(e).__name__) from None  # geen adres of coördinaten in de fout
    return docs[0] if docs else {}


def geldig_adres(adres: str) -> bool:
    """Minstens een postcode ('8701 AA') of straat met nummer; geen losse letters."""
    tekst = (adres or "").strip()
    return 4 <= len(tekst) <= 200 and bool(re.search(r"\d", tekst))


def in_nederland(lat: float, lon: float) -> bool:
    return _NL["lat"][0] <= lat <= _NL["lat"][1] and _NL["lon"][0] <= lon <= _NL["lon"][1]


def buurt_bij_adres(adres: str, get: Callable[..., Any] = requests.get) -> Optional[Dict[str, str]]:
    """'8601 CR' of 'Marktstraat 15 Sneek' → {'buurtcode': 'BU19000101', 'buurtnaam': ...} of None."""
    doc = _vraag("free", {"q": adres.strip(), "fq": "type:adres", "fl": "buurtcode,buurtnaam", "rows": 1}, get)
    code = doc.get("buurtcode")
    return {"buurtcode": code, "buurtnaam": doc.get("buurtnaam") or code} if code and _BUURTCODE.match(code) else None


def buurt_bij_punt(lat: float, lon: float, get: Callable[..., Any] = requests.get) -> Optional[Dict[str, str]]:
    """Locatie (WGS84) → de CBS-buurt waarin het punt ligt, of None."""
    doc = _vraag(
        "reverse",
        {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "type": "buurt", "rows": 1, "fl": "identificatie,buurtnaam"},
        get,
    )
    code = doc.get("identificatie")
    return {"buurtcode": code, "buurtnaam": doc.get("buurtnaam") or code} if code and _BUURTCODE.match(code) else None
