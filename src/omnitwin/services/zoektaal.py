"""
Zoeken naar indicatoren in gewone taal (#233): begrippen, trefwoorden en betekenis samen.

Een vraag als "hoeveel % is bejaard bij mij in de buurt?" vindt de juiste indicator via drie wegen:

1. begrippen  (db/stuurdata/synoniemen.json): 'bejaard' is een synoniem van 'ouderen' → 65+ jaar (%);
2. naam       woorden uit de vraag in de indicatornaam ('energielabels' → Gemiddeld energielabel);
3. betekenis  de gelijkenis van de vraag met de tekst van de indicator: naam, beschrijving,
              kompaspad (titel / thema / onderdeel), eenheid en de synoniemen uit 1
              (embeddings, services/embedding_model.py; tekst: indicator_tekst hieronder).

Score per indicator (0-1), uitlegbaar:
    trefwoord = max(begrip, naam)                         (0 als geen van beide)
    score     = GEWICHT_TREFWOORD * trefwoord + GEWICHT_BETEKENIS * betekenis
De betekenis is de cosinusgelijkenis, geschaald per vraag: op of onder de mediane gelijkenis
van alle indicatoren met deze vraag (plus embedding_model.GELIJKENIS_MARGE_ONDER) telt als 0, op
of boven mediaan + GELIJKENIS_MARGE_BOVEN als 1. Zo telt hoeveel een indicator eruit springt.
Alleen betekenis haalt hoogstens GEWICHT_BETEKENIS; voor 'sterk' is ook een begrip of naam nodig.

Afkap: alleen resultaten met score >= MIN_SCORE én binnen MAX_AFSTAND van de beste; zonder
sterke treffer hoogstens MAX_MATIG. Liever 2 goede dan 8 matige. Labels voor de gebruiker: 'sterk' (>= STERK) of 'matig'.

Alles hier is zonder database of model te testen (tests/test_zoektaal.py).
"""
import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SYNONIEMEN = Path(__file__).resolve().parents[3] / "db" / "stuurdata" / "synoniemen.json"

# Afgestemd op tests/data/assistent_evaluatie.json (zonder de holdout-vragen), #233
GEWICHT_TREFWOORD = 0.5
GEWICHT_BETEKENIS = 0.5
THEMA_FACTOR = 0.9      # een verzamelbegrip ('armoede') is minder precies dan een specifiek begrip
MIN_SCORE = 0.25        # daaronder nooit tonen
MAX_AFSTAND = 0.25      # alleen resultaten binnen deze afstand van de beste
STERK = 0.6             # vanaf hier 'sterk'; daaronder 'matig'
MAX_MATIG = 3           # zonder sterke treffer hoogstens zoveel resultaten

# ── Normaliseren ─────────────────────────────────────────────────────────────


def normaliseer(tekst: str) -> str:
    """Kleine letters, zonder accenten; alles behalve letters en cijfers wordt een spatie."""
    tekst = unicodedata.normalize("NFKD", tekst or "")
    tekst = "".join(c for c in tekst if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", tekst).split())


# Woorden die in indicatornamen niets onderscheiden
STOPWOORDEN = {
    "de", "het", "een", "van", "tot", "met", "per", "en", "in", "op", "voor", "naar", "uit",
    "aantal", "totaal", "gemiddeld", "gemiddelde", "percentage", "index", "bag", "cbs", "exc",
    "t", "o", "v", "nu", "jaar", "wat", "hoe", "waar", "welke", "is", "zijn", "er", "ik", "mijn",
    "wil", "weten", "staat", "ligt", "wonen", "buurt", "buurten", "wijk", "wijken", "meeste",
    "minste", "hoogste", "laagste", "relatief",
}


def tokens(tekst: str) -> List[str]:
    return [t for t in normaliseer(tekst).split() if t not in STOPWOORDEN and not t.isdigit()]


def token_past(vraagwoord: str, naamwoord: str) -> bool:
    """'vrijwilligerswerk' past bij 'vrijwilliger', 'energielabels' bij 'energielabel'."""
    if vraagwoord == naamwoord:
        return True
    kort, lang = sorted((vraagwoord, naamwoord), key=len)
    return len(kort) >= 5 and lang.startswith(kort)


# ── Begrippen ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Begrip:
    label: str                    # prefLabel
    soort: str                    # specifiek | thema
    labels: Tuple[str, ...]       # genormaliseerd: prefLabel + altLabel
    indicatoren: Tuple[str, ...]  # indicatornamen, de beste eerst


def lees_begrippen(data: Dict[str, Any]) -> List[Begrip]:
    uit = []
    for b in data.get("begrippen", []):
        labels = [normaliseer(b["prefLabel"])] + [normaliseer(a) for a in b.get("altLabel", [])]
        uit.append(Begrip(b["prefLabel"], b.get("soort", "specifiek"),
                          tuple(dict.fromkeys(l for l in labels if l)), tuple(b.get("indicatoren", []))))
    return uit


@lru_cache(maxsize=4)
def _laad(pad: str, mtime: float) -> Tuple[Begrip, ...]:
    return tuple(lees_begrippen(json.loads(Path(pad).read_text(encoding="utf-8"))))


def laad_begrippen(pad: Optional[Path] = None) -> List[Begrip]:
    """De begrippen uit db/stuurdata/synoniemen.json (opnieuw gelezen als het bestand wijzigt)."""
    p = Path(pad or SYNONIEMEN)
    if not p.is_file():
        return []
    return list(_laad(str(p), p.stat().st_mtime))


@dataclass
class BegripTreffer:
    begrip: Begrip
    label: str          # het label dat paste
    woorden: List[str]  # de woorden uit de vraag die het label dekt
    positie: int        # plek in de vraag (voor de volgorde)


def _label_past(woorden: List[str], i: int, label: List[str]) -> bool:
    """Past het label op de vraagwoorden vanaf i? Het laatste labelwoord mag het begin van een
    langer vraagwoord zijn ('bejaard' → 'bejaarden'), als het label 5 of meer letters heeft."""
    if i + len(label) > len(woorden):
        return False
    for j, lw in enumerate(label):
        w = woorden[i + j]
        if w == lw:
            continue
        if j == len(label) - 1 and len(lw) >= 5 and w.startswith(lw):
            continue
        return False
    return True


def herken_begrippen(vraag: str, begrippen: Sequence[Begrip]) -> List[BegripTreffer]:
    """
    Begrippen in de vraag. Langere labels eerst; hun woorden zijn daarna 'op'
    ('lage inkomens' → lage inkomens, en niet ook nog 'inkomens' → inkomen).
    """
    woorden = normaliseer(vraag).split()
    bezet = [False] * len(woorden)
    kandidaten = sorted(((len(l.split()), len(l), l, b) for b in begrippen for l in b.labels),
                        key=lambda t: (-t[0], -t[1]))
    treffers: List[BegripTreffer] = []
    for _, _, label, b in kandidaten:
        lw = label.split()
        for i in range(len(woorden)):
            if any(bezet[i:i + len(lw)]) or not _label_past(woorden, i, lw):
                continue
            for j in range(i, i + len(lw)):
                bezet[j] = True
            treffers.append(BegripTreffer(b, label, woorden[i:i + len(lw)], i))
    return sorted(treffers, key=lambda t: t.positie)


def naam_sleutel(naam: str) -> str:
    """Indicatornamen vergelijken: hoofdletterongevoelig, maar '65+ jaar' blijft anders dan '65+ jaar (%)'."""
    return " ".join((naam or "").lower().split())


def synoniemen_van(naam: str, begrippen: Sequence[Begrip]) -> List[str]:
    """Labels van de begrippen waar deze indicator bij hoort (voor de embeddingtekst)."""
    n = naam_sleutel(naam)
    uit: List[str] = []
    for b in begrippen:
        if any(naam_sleutel(x) == n for x in b.indicatoren):
            uit.extend(l for l in b.labels if l not in uit)
    return uit


def indicator_tekst(naam: str, beschrijving: Optional[str] = None, kompaspad: Sequence[Optional[str]] = (),
                    eenheid: Optional[str] = None, synoniemen: Sequence[str] = ()) -> str:
    """
    De tekst die per indicator geëmbed wordt (zonder voorvoegsel van het model):
    'Inwoners. Thema: Meedoen / Netwerk. Eenheid: aantal. Ook: bevolking, inwonertal. <beschrijving>'
    """
    delen = [naam.strip()]
    pad = " / ".join(x.strip() for x in kompaspad if x and x.strip())
    if pad:
        delen.append(f"Thema: {pad}")
    if eenheid and eenheid.strip():
        delen.append(f"Eenheid: {eenheid.strip()}")
    if synoniemen:
        delen.append("Ook: " + ", ".join(synoniemen))
    if beschrijving and beschrijving.strip():
        delen.append(beschrijving.strip())
    return ". ".join(delen)


# ── Rangschikken ─────────────────────────────────────────────────────────────

def relatieve_grenzen(gelijkenis: Dict[str, float], marge_onder: float, marge_boven: float) -> Tuple[float, float]:
    """Onder- en bovengrens voor deze vraag: mediane gelijkenis plus de marges van het model."""
    waarden = sorted(gelijkenis.values())
    if not waarden:
        return 0.0, 1.0
    m = len(waarden) // 2
    mediaan = waarden[m] if len(waarden) % 2 else (waarden[m - 1] + waarden[m]) / 2
    return mediaan + marge_onder, mediaan + marge_boven


def schaal_gelijkenis(cos: Optional[float], onder: float, boven: float) -> float:
    """Cosinusgelijkenis naar 0-1 tussen de grenzen van het model."""
    if cos is None or boven <= onder:
        return 0.0
    return max(0.0, min(1.0, (float(cos) - onder) / (boven - onder)))


def naam_score(vraagwoorden: Sequence[str], naam: str) -> Tuple[float, List[str]]:
    """Deel van de naamwoorden dat in de vraag staat (minstens de helft en één woord van 5+ letters)."""
    naamwoorden = tokens(naam)
    if not naamwoorden:
        return 0.0, []
    geraakt = [w for w in naamwoorden if any(token_past(v, w) for v in vraagwoorden)]
    score = len(geraakt) / len(naamwoorden)
    if score >= 0.5 and any(len(w) >= 5 for w in geraakt):
        return score, geraakt
    return 0.0, []


@dataclass
class Rang:
    uuid: str
    naam: str
    score: float
    begrip: float = 0.0
    naam_deel: float = 0.0
    betekenis: float = 0.0
    redenen: List[str] = field(default_factory=list)

    @property
    def relevantie(self) -> str:
        return "sterk" if self.score >= STERK else "matig"


def rangschik(
    vraag: str,
    indicatoren: Sequence[Dict[str, Any]],
    gelijkenis: Dict[str, float],
    begrippen: Sequence[Begrip],
    onder: float,
    boven: float,
    limit: int = 5,
    afkappen: bool = True,
) -> List[Rang]:
    """
    indicatoren: [{uuid, naam}] (actief)
    gelijkenis:  {uuid: cosinusgelijkenis met de vraag} (kan leeg zijn: dan alleen trefwoorden)
    """
    per_naam: Dict[str, List[Dict[str, Any]]] = {}
    for i in indicatoren:
        per_naam.setdefault(naam_sleutel(i["naam"]), []).append(i)

    # 1. Begrippen: de eerste indicator van een begrip 1,0, daarna steeds 0,05 minder
    begrip_score: Dict[str, Tuple[float, str]] = {}
    treffers = herken_begrippen(vraag, begrippen)
    gedekt = set()
    for t in treffers:
        gedekt |= set(t.woorden)
        factor = THEMA_FACTOR if t.begrip.soort == "thema" else 1.0
        for pos, naam in enumerate(t.begrip.indicatoren):
            for ind in per_naam.get(naam_sleutel(naam), []):
                s = factor * max(0.75, 1.0 - 0.05 * pos)
                u = str(ind["uuid"])
                if s > begrip_score.get(u, (0.0, ""))[0]:
                    begrip_score[u] = (s, t.begrip.label)

    # 2. Woorden uit de naam; vraagwoorden die al een begrip vormen tellen niet nog eens
    vraagwoorden = [w for w in tokens(vraag) if w not in gedekt] if treffers else tokens(vraag)

    uit = []
    for ind in indicatoren:
        u = str(ind["uuid"])
        b, begrip_label = begrip_score.get(u, (0.0, ""))
        n, geraakt = naam_score(vraagwoorden, ind["naam"])
        g = schaal_gelijkenis(gelijkenis.get(u), onder, boven)
        trefwoord = max(b, n)
        score = GEWICHT_TREFWOORD * trefwoord + GEWICHT_BETEKENIS * g
        if b >= 1.0:
            # Eerste indicator van een specifiek begrip (zelf vastgelegd in synoniemen.json): altijd
            # 'sterk', ook als de embedding net minder uitspringt (bijv. na een andere Kompas-inrichting)
            score = max(score, STERK)
        redenen = []
        if b:
            redenen.append(f"begrip: {begrip_label}")
        if n:
            redenen.append(f"naam: {', '.join(geraakt)}")
        if g >= 0.5:
            redenen.append("betekenis")
        uit.append(Rang(u, ind["naam"], round(score, 4), b, n, round(g, 4), redenen))

    uit.sort(key=lambda r: (-r.score, -r.begrip, len(r.naam)))
    if not afkappen:
        return uit[:limit]
    if not uit or uit[0].score < MIN_SCORE:
        return []
    if uit[0].score < STERK:
        limit = min(limit, MAX_MATIG)
    return [r for r in uit if r.score >= MIN_SCORE and r.score > uit[0].score - MAX_AFSTAND][:limit]
