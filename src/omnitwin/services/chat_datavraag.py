"""
Datavragen in de chat beantwoorden met cijfers uit de database (#149).

"Welke buurt in Bolsward ligt het verst van een koele plek?" is een datavraag:
de gebruiker wil een getal of een rangorde, geen knop. De route:

1. herkennen: patroon in de vraag ("welke buurt", "hoe staat het met", "vergelijk", "top 3", ...);
2. gebieden: namen uit de vraag (buurt, woonplaats → buurten, gemeente) of de kaartcontext;
   één gebied krijgt zijn buren (zelfde woonplaats of gemeente) als referentie erbij;
3. indicatoren: woorden uit de indicatornamen, de begrippen en synoniemen uit
   db/stuurdata/synoniemen.json ("energiearmoede", "bejaard" → 65+ jaar (%)) en AI-zoeken
   per deelvraag, alleen bij een sterke treffer (services/zoektaal.py, #233);
   "mijn buurt" / "bij mij" / "hier" zonder geselecteerde buurt: eerst vragen welke buurt
   (de viewer biedt dan postcode/adres of locatie aan, #336);
4. cijfers: de meest recente waarde per gebied en indicator, met eenheid, bron, jaar,
   richting (hoger/lager is beter) en rangorde binnen de groep;
5. antwoord: het taalmodel krijgt alleen die cijfers. Staat er in het antwoord een getal dat
   niet in de cijfers staat, dan valt de route terug op een vaste tekst uit dezelfde cijfers.

De herkenning (stap 1-3, behalve AI-zoeken) en de opbouw van de feiten zijn zuiver en
zonder database of model te testen (tests/test_chat_datavraag.py).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import text

from omnitwin import polariteit
from omnitwin.services import kleine_aantallen as ka
from omnitwin.services import zoektaal
from omnitwin.services.grounding import ongegronde_getallen

MAX_INDICATOREN = 4
MAX_GEBIEDEN_IN_FEITEN = 12  # langere lijsten: top en staart
MAX_ALLE_GEBIEDEN = 30  # zonder plaats in de vraag: alle gebieden, als het er niet meer zijn
MAX_REFERENTIE = 25
MAX_SELECTIE = 50  # zoveel gebieden uit een multi-selectie op de kaart (#233)
AI_DREMPEL = 0.7  # score van AI-zoeken (services/zoektaal.py); 'sterk' begint bij 0,6

# ── Normaliseren ─────────────────────────────────────────────────────────────

normaliseer = zoektaal.normaliseer


# ── 1. Datavraag herkennen ───────────────────────────────────────────────────

_DATAVRAAG_PATRONEN = [
    r"\bwelke (buurt|buurten|wijk|wijken|kern|kernen|dorp|dorpen|gebied|gebieden|plaats|plaatsen)\b",
    r"\bwaar\b.*\b(meest|meeste|minst|minste|hoogst|hoogste|laagst|laagste|grootst|grootste|"
    r"kleinst|kleinste|verst|verste|dichtst|dichtste|slechtst|slechtste|best|beste)\b",
    r"\bhoe staat het\b",
    r"\bhoe staan\b",
    r"\bhoe scoort\b",
    r"\bhoe scoren\b",
    r"\bhoe (hoog|laag|groot|veel)\b",
    r"\bhoeveel\b",
    r"\bvergelijk",
    r"\bvergeleken\b",
    r"\bten opzichte van\b",
    r"\bt o v\b",
    r"\btop \d+\b",
    r"\b(\d+|twee|drie|vier|vijf|tien) (buurten|wijken|gebieden|kernen)\b",
    r"\b(hoogste|laagste|meeste|minste|verst|verste|dichtst|dichtste|grootste|kleinste)\b",
    r"\bwat is (de|het)\b.*\b(in|van|voor)\b",
    r"\bhoe staat\b.*\bervoor\b",
    r"\bhoe [a-z]+ (is|zijn|ligt|liggen|woont|wonen)\b",  # 'hoe groen/veilig/oud/gezond is X'
]

# Expliciete navigatie of uitleg: nooit een datavraag
_NAVIGATIE = (
    r"^(toon|open|ga naar|selecteer|kleur|zoom)\b|^laat\b.*\bzien\b|\bop de kaart\b|"
    r"\bwelke indicatoren\b|\bwat kan\b|\bwat kun\b|\brapport\b|\bhandleiding\b|^help\b"
)


_EIGEN_BUURT = (
    r"\bmijn (buurt|wijk|dorp|straat|omgeving|woonplaats)\b|\bbij mij\b|\bbij ons\b|"
    r"\bonze (buurt|wijk|straat|omgeving|woonplaats)\b|\b(deze|dit|die) (buurt|wijk|dorp|gebied)\b|"
    r"\bwaar ik woon\b|\bwaar wij wonen\b|\bhier\b"
)


def vraagt_eigen_buurt(vraag: str) -> bool:
    """'bij mij in de buurt', 'in mijn wijk', 'hier': de gebruiker bedoelt zijn eigen buurt."""
    return bool(re.search(_EIGEN_BUURT, normaliseer(vraag)))


def is_navigatie(vraag: str) -> bool:
    """'Toon eenzaamheid op de kaart', 'open het Kompas', 'maak een rapport': navigatie."""
    return bool(re.search(_NAVIGATIE, normaliseer(vraag)))


def is_datavraag(vraag: str) -> bool:
    """
    Vraagt de gebruiker zichtbaar om cijfers of een rangorde?

    Ook zonder zo'n patroon wordt het een datavraag als er een gebied herkend wordt (vraag of
    kaart) en een indicator past; zie beantwoord_datavraag.
    """
    if is_navigatie(vraag):
        return False
    v = normaliseer(vraag)
    return any(re.search(p, v) for p in _DATAVRAAG_PATRONEN)


_GETALWOORDEN = {"twee": 2, "drie": 3, "vier": 4, "vijf": 5, "tien": 10}


def gevraagd_aantal(vraag: str) -> Optional[int]:
    """'top 3 buurten', 'de 5 wijken met ...' → 3 / 5; anders None."""
    v = normaliseer(vraag)
    m = re.search(r"\btop (\d+)\b", v) or re.search(
        r"\b(\d+|twee|drie|vier|vijf|tien) (buurten|wijken|gebieden|kernen)\b", v
    )
    if not m:
        return None
    n = m.group(1)
    return int(n) if n.isdigit() else _GETALWOORDEN[n]


_LAAG_WOORDEN = r"\b(laagste|minste|kleinste|dichtst|dichtste|kortste|onderste)\b"
_HOOG_WOORDEN = r"\b(hoogste|meeste|grootste|verst|verste|langste|bovenste|top)\b"


def gevraagde_volgorde(vraag: str) -> str:
    """'laag' als de vraag naar de laagste waarden vraagt, anders 'hoog'."""
    v = normaliseer(vraag)
    if re.search(_LAAG_WOORDEN, v) and not re.search(_HOOG_WOORDEN, v):
        return "laag"
    return "hoog"


# ── 2. Gebieden herkennen ────────────────────────────────────────────────────

# Namen die ook gewone woorden zijn: niet als gebied herkennen
_GEEN_GEBIEDSNAAM = {
    "centrum",
    "buitengebied",
    "noord",
    "zuid",
    "oost",
    "west",
    "dorp",
    "wijk",
    "buurt",
    "verspreide huizen",
    "bedrijventerrein",
    "haven",
    "stad",
    "kern",
    "de",
    "het",
}


def plaats_van(naam: str) -> str:
    """Woonplaats-deel van een gebiedsnaam: 'Bolsward-Zuidoost' → 'Bolsward', 'Workum' → 'Workum'."""
    return re.split(r"\s*-\s*|\s*,\s*|\s+\(", (naam or "").strip())[0]


@dataclass
class GebiedHerkenning:
    gevraagd: List[str] = field(default_factory=list)  # gebied-ids uit de vraag of de kaart
    referentie: List[str] = field(default_factory=list)  # buren, voor de rangorde
    herkend: List[str] = field(default_factory=list)  # leesbaar: welke namen herkend zijn
    bron: str = "geen"  # vraag | kaart | alle | geen


def herken_gebieden(
    vraag: str,
    gebieden: Sequence[Dict[str, Any]],
    gemeenten: Optional[Dict[str, str]] = None,
    huidig_gebied_id: Optional[str] = None,
    voorkeur_type: Optional[str] = None,
    geselecteerd: Sequence[str] = (),
) -> GebiedHerkenning:
    """
    Herken gebieden in de vraag.

    gebieden: [{id, naam, gemeente_code, gebiedstype_id}] (actieve gebieden)
    gemeenten: {code: naam}
    voorkeur_type: gebiedstype voor woonplaats/gemeente → gebieden (meestal buurten)

    Volgorde: volledige gebiedsnamen (langste eerst), dan woonplaatsen
    ('Bolsward' → alle buurten die met 'Bolsward-' beginnen), dan gemeenten.
    Zonder treffer: de selectie op de kaart (geselecteerd: alle geselecteerde gebieden, #233;
    anders huidig_gebied_id).
    """
    gemeenten = gemeenten or {}
    per_id = {g["id"]: g for g in gebieden}
    if not voorkeur_type and huidig_gebied_id in per_id:
        voorkeur_type = per_id[huidig_gebied_id].get("gebiedstype_id")
    van_type = [g for g in gebieden if not voorkeur_type or g.get("gebiedstype_id") == voorkeur_type]

    origineel = rest = f" {normaliseer(vraag)} "
    res = GebiedHerkenning()
    treffers: List[Tuple[int, List[str], str]] = []  # (plek in de vraag, ids, naam)

    def voeg_toe(frase: str, ids: Iterable[str], naam: str):
        treffers.append((origineel.find(f" {frase} "), list(ids), naam))

    # Woonplaatsen van het voorkeurstype: 'bolsward' → [Bolsward-Noord, Bolsward-Zuidoost, ...]
    plaatsen: Dict[str, List[str]] = {}
    for g in van_type:
        p = normaliseer(plaats_van(g["naam"]))
        if len(p) >= 4 and p not in _GEEN_GEBIEDSNAAM:
            plaatsen.setdefault(p, []).append(g["id"])

    # a. Volledige gebiedsnamen, langste eerst; de tekst wordt 'opgebruikt'
    namen: Dict[str, List[Dict[str, Any]]] = {}
    for g in gebieden:
        n = normaliseer(g["naam"])
        if len(n) >= 4 and n not in _GEEN_GEBIEDSNAAM:
            namen.setdefault(n, []).append(g)
    for n in sorted(namen, key=len, reverse=True):
        if f" {n} " in rest:
            kandidaten = namen[n]
            voorkeur = [g for g in kandidaten if g.get("gebiedstype_id") == voorkeur_type]
            if not voorkeur and n in plaatsen:
                continue  # wijk 'Bolsward' → liever de buurten van Bolsward (stap b)
            voeg_toe(n, [g["id"] for g in (voorkeur or kandidaten[:1])], kandidaten[0]["naam"])
            rest = rest.replace(f" {n} ", " | ")

    # b. Woonplaatsen: 'Bolsward' → Bolsward-Noord, Bolsward-Zuidoost, ...
    for p in sorted(plaatsen, key=len, reverse=True):
        if f" {p} " in rest:
            voeg_toe(p, plaatsen[p], plaats_van(per_id[plaatsen[p][0]]["naam"]))
            rest = rest.replace(f" {p} ", " | ")

    # c. Gemeenten: alle gebieden van het voorkeurstype in die gemeente
    for code, gnaam in gemeenten.items():
        n = normaliseer(gnaam)
        if n and f" {n} " in rest:
            ids = [g["id"] for g in van_type if g.get("gemeente_code") == code]
            if ids:
                voeg_toe(n, ids, gnaam)
                rest = rest.replace(f" {n} ", " | ")

    # In de volgorde van de vraag
    for _, ids, naam in sorted(treffers, key=lambda t: t[0]):
        res.herkend.append(naam)
        res.gevraagd.extend(i for i in ids if i not in res.gevraagd)

    selectie = [i for i in dict.fromkeys(list(geselecteerd or [])[:MAX_SELECTIE]) if i in per_id]
    if not selectie and huidig_gebied_id and huidig_gebied_id in per_id:
        selectie = [huidig_gebied_id]
    if res.gevraagd:
        res.bron = "vraag"
    elif selectie:
        res.gevraagd = selectie
        res.herkend.extend(per_id[i]["naam"] for i in selectie)
        res.bron = "kaart"

    # Eén gebied: buren als referentie (zelfde woonplaats, anders zelfde gemeente)
    if len(res.gevraagd) == 1:
        g = per_id[res.gevraagd[0]]
        type_id = g.get("gebiedstype_id")
        p = normaliseer(plaats_van(g["naam"]))
        buren = [
            b["id"]
            for b in gebieden
            if b["id"] != g["id"]
            and b.get("gebiedstype_id") == type_id
            and normaliseer(plaats_van(b["naam"])) == p
            and p != normaliseer(g["naam"])
        ]
        if not buren and g.get("gemeente_code"):
            buren = [
                b["id"]
                for b in gebieden
                if b["id"] != g["id"]
                and b.get("gebiedstype_id") == type_id
                and b.get("gemeente_code") == g["gemeente_code"]
            ]
        res.referentie = buren[:MAX_REFERENTIE]
    return res


def resterende_tekst(vraag: str, gebiedsnamen: Iterable[str]) -> str:
    """De vraag zonder gebiedsnamen (voor AI-zoeken naar het onderwerp)."""
    rest = f" {normaliseer(vraag)} "
    for n in sorted({normaliseer(x) for x in gebiedsnamen if x}, key=len, reverse=True):
        rest = rest.replace(f" {n} ", " ")
    return " ".join(rest.split())


# ── 3. Indicatoren herkennen ─────────────────────────────────────────────────

# Woorden, begrippen en synoniemen: services/zoektaal.py en db/stuurdata/synoniemen.json (#233)
_STOPWOORDEN = zoektaal.STOPWOORDEN
_PRIORITEIT = {"specifiek": 0, "lexicaal": 1, "ai": 2, "thema": 3}
_tokens = zoektaal.tokens
_token_past = zoektaal.token_past


@dataclass
class IndicatorTreffer:
    uuid: str
    naam: str
    soort: str  # specifiek | lexicaal | ai | thema
    score: float
    woorden: set = field(default_factory=set)  # vraagwoorden die deze treffer 'dekt'
    begrip: bool = False  # ook genoemd in de begrippenlijst


def herken_indicatoren(
    vraag: str,
    indicatoren: Sequence[Dict[str, Any]],
    ai_treffers: Sequence[Dict[str, Any]] = (),
    max_aantal: int = MAX_INDICATOREN,
    begrippen: Optional[Sequence[zoektaal.Begrip]] = None,
) -> List[IndicatorTreffer]:
    """
    Kies de indicatoren bij de vraag.

    indicatoren: [{uuid, naam}] (actief, met data)
    ai_treffers: resultaten van AI-zoeken [{uuid, naam, score}]; alleen score >= AI_DREMPEL telt.
    begrippen:   uit db/stuurdata/synoniemen.json (standaard); 'specifiek' gaat voor 'thema'
                 als het maximum aantal indicatoren bereikt is.

    Een treffer waarvan alle vraagwoorden al gedekt zijn door een eerdere treffer valt af
    (dus niet zowel 'Gemiddeld energielabel' als 'Aantal energielabels' bij 'energielabels').
    Bestaat zowel 'X' als 'X (%)', dan blijft alleen het percentage.
    """
    per_naam = {zoektaal.naam_sleutel(i["naam"]): i for i in indicatoren}
    per_uuid = {str(i["uuid"]): i for i in indicatoren}
    v_norm = normaliseer(vraag)
    vraagwoorden = _tokens(vraag)
    treffers: Dict[str, IndicatorTreffer] = {}

    def voeg_toe(ind, soort, score, woorden):
        u = str(ind["uuid"])
        oud = treffers.get(u)
        begrip = soort in ("specifiek", "thema") or bool(oud and oud.begrip)
        if oud is None or _PRIORITEIT[soort] < _PRIORITEIT[oud.soort]:
            treffers[u] = IndicatorTreffer(
                u, ind["naam"], soort, score, set(woorden) | (oud.woorden if oud else set()), begrip
            )
        else:
            oud.woorden |= set(woorden)
            oud.begrip = begrip

    # Begrippen en synoniemen (langere labels eerst; hun woorden zijn daarna op)
    begrippen = zoektaal.laad_begrippen() if begrippen is None else begrippen
    for t in zoektaal.herken_begrippen(vraag, begrippen):
        for n in t.begrip.indicatoren:
            if zoektaal.naam_sleutel(n) in per_naam:
                voeg_toe(per_naam[zoektaal.naam_sleutel(n)], t.begrip.soort, 1.0, set(t.woorden))

    # Woorden uit de indicatornaam
    for ind in indicatoren:
        naamwoorden = _tokens(ind["naam"])
        if not naamwoorden:
            continue
        gedekt = {v for v in vraagwoorden for w in naamwoorden if _token_past(v, w)}
        geraakt = [w for w in naamwoorden if any(_token_past(v, w) for v in vraagwoorden)]
        score = len(geraakt) / len(naamwoorden)
        if score >= 0.5 and any(len(w) >= 5 for w in geraakt):
            voeg_toe(ind, "lexicaal", score, gedekt)

    # AI-zoeken: alleen sterke treffers
    for r in ai_treffers:
        u = str(r.get("uuid"))
        if u in per_uuid and float(r.get("score", 0)) >= AI_DREMPEL:
            voeg_toe(per_uuid[u], "ai", float(r["score"]), set(_tokens(r.get("naam", ""))))

    def positie(t: IndicatorTreffer) -> int:
        # Eerder genoemd in de vraag = eerder in het antwoord
        plekken = [f" {v_norm} ".find(f" {w}") for w in t.woorden]
        plekken = [p for p in plekken if p >= 0]
        return min(plekken) if plekken else 10_000

    volgorde = sorted(
        treffers.values(),
        key=lambda t: (_PRIORITEIT[t.soort], not t.begrip, -round(t.score, 2), positie(t), len(t.naam)),
    )
    # 'X' valt weg als 'X (%)' ook gekozen is
    namen_gekozen = {t.naam for t in volgorde}
    volgorde = [t for t in volgorde if f"{t.naam} (%)" not in namen_gekozen]

    gekozen: List[IndicatorTreffer] = []
    gedekt: set = set()
    for t in volgorde:
        if t.soort == "lexicaal" and t.woorden and t.woorden <= gedekt:
            continue
        gekozen.append(t)
        gedekt |= t.woorden
        if len(gekozen) >= max_aantal:
            break
    # Volgorde van de vraag; thema-aanvullingen achteraan
    gekozen.sort(key=lambda t: (t.soort == "thema", positie(t)))
    return gekozen


# ── 4. Richting, rangorde en feiten ──────────────────────────────────────────


def richting(score_type: Optional[str], interpretatie_logica: Optional[str]) -> str:
    """
    'hoger_is_beter' | 'lager_is_beter' | 'neutraal'.

    Eén regel voor alle plekken (omnitwin.polariteit, #120): interpretatie_logica
    'neutraal' of 'N/A' gaat voor, dan '+/+' hoger-is-beter, de andere score_types
    lager-is-beter.
    """
    return polariteit.uit_oud(score_type or "+/+", interpretatie_logica)


RICHTING_TEKST = {
    "hoger_is_beter": "hoger is beter",
    "lager_is_beter": "lager is beter",
    "neutraal": "geen oordeel (neutraal)",
}

# Voor het taalmodel: de richting uitgeschreven, zodat een klein model de duiding niet omdraait
RICHTING_UITLEG = {
    "hoger_is_beter": "hoger is beter: een hoge waarde is gunstig, een lage waarde ongunstig",
    "lager_is_beter": "lager is beter: een hoge waarde is ongunstig, een lage waarde gunstig",
    "neutraal": "geen oordeel: zeg niet of een waarde goed of slecht is",
}


def formatteer_getal(w: float) -> str:
    """Nederlandse notatie zonder duizendtalpunt: 48.3 → '48,3', 246.0 → '246', 0.734 → '0,73'."""
    w = float(w)
    if abs(w) >= 1 or w == 0:
        s = f"{round(w, 1):.1f}"
    else:
        s = f"{w:.2f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s.replace(".", ",")


_UUIDACHTIG = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.IGNORECASE)
_BESTAND = re.compile(r"\.(json|geojson|csv|xlsx?|parquet|gpkg|shp|zip)$|[\\/]", re.IGNORECASE)


def nette_bron(bron: Optional[str]) -> str:
    """Bron leesbaar maken; een importbestand met uuid-naam zegt de gebruiker niets."""
    b = (bron or "").strip()
    if not b:
        return "bron onbekend"
    if _UUIDACHTIG.match(b) or _BESTAND.search(b):
        return "onbekende bron (import)"
    return b


def is_demo(bron: Optional[str]) -> bool:
    return (bron or "").strip().upper().startswith("DEMO")


def bouw_feiten(
    indicatoren: Sequence[Dict[str, Any]],
    waarden: Sequence[Dict[str, Any]],
    gebiedsnamen: Dict[str, str],
    gevraagd: Sequence[str],
    volgorde: str = "hoog",
    aantal: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Per indicator: waarden van de gebieden, gesorteerd, met rang en richting.

    indicatoren: [{uuid, naam, eenheid, bron, score_type, interpretatie_logica}]
    waarden:     [{gebied_id, indicator_uuid, waarde, jaar, bron}] (meest recente jaar)
    gevraagd:    gebied-ids die de gebruiker noemde (de rest is referentie)
    volgorde:    'hoog' (hoogste eerst) of 'laag'
    aantal:      top-N uit de vraag; dan alleen de eerste N (rang blijft binnen de hele groep)
    """
    feiten = []
    for ind in indicatoren:
        u = str(ind["uuid"])
        rijen = [w for w in waarden if str(w["indicator_uuid"]) == u and w.get("waarde") is not None]
        if not rijen:
            continue
        r = richting(ind.get("score_type"), ind.get("interpretatie_logica"))
        rijen = sorted(rijen, key=lambda w: float(w["waarde"]), reverse=True)
        n = len(rijen)
        hoogste = float(rijen[0]["waarde"])
        laagste = float(rijen[-1]["waarde"])
        verschil = n > 1 and hoogste != laagste
        lijst = []
        for w in rijen:
            waarde = float(w["waarde"])
            item = {
                "gebied_id": w["gebied_id"],
                "gebied": gebiedsnamen.get(w["gebied_id"], w["gebied_id"]),
                "waarde": waarde,
                "jaar": w.get("jaar"),
                # 1 = hoogste waarde; gelijke waarden delen de rang
                "rang_hoog": 1 + sum(1 for x in rijen if float(x["waarde"]) > waarde),
                "gevraagd": w["gebied_id"] in gevraagd,
                "demo": is_demo(w.get("bron")),
            }
            labels = []
            if verschil and waarde == hoogste:
                labels.append("hoogste waarde")
            if verschil and waarde == laagste:
                labels.append("laagste waarde")
            if verschil and r != "neutraal":
                gunstig = hoogste if r == "hoger_is_beter" else laagste
                ongunstig = laagste if r == "hoger_is_beter" else hoogste
                if waarde == gunstig:
                    labels.append("gunstigst")
                if waarde == ongunstig:
                    labels.append("ongunstigst")
            item["labels"] = labels
            lijst.append(item)
        if volgorde == "laag":
            lijst = list(reversed(lijst))
        if aantal:
            lijst = lijst[:aantal]
        elif len(lijst) > MAX_GEBIEDEN_IN_FEITEN:
            # gevraagde gebieden altijd houden, verder top en staart
            kop = lijst[: MAX_GEBIEDEN_IN_FEITEN // 2]
            staart = lijst[-MAX_GEBIEDEN_IN_FEITEN // 2 :]
            midden = [x for x in lijst if x["gevraagd"] and x not in kop and x not in staart]
            lijst = kop + midden + staart
        jaren = sorted({w.get("jaar") for w in rijen if w.get("jaar")})
        feiten.append(
            {
                "indicator_uuid": u,
                "indicator": ind["naam"],
                "eenheid": (ind.get("eenheid") or "").strip(),
                "bron": nette_bron(ind.get("bron")),
                "jaren": jaren,
                "richting": r,
                "aantal_gebieden": n,
                "waarden": lijst,
            }
        )
    return feiten


def _waarde_tekst(item: Dict[str, Any], eenheid: str) -> str:
    """Waarde met eenheid: '48,3%', '246 m', '30,9 duizend euro'."""
    e = (eenheid or "").strip()
    getal = formatteer_getal(item["waarde"])
    if e in ("%", "percentage"):
        return f"{getal}%"
    if re.fullmatch(r"x\s*1[ .]?000\s*euro", e.lower()):
        return f"{getal} duizend euro"
    if e and e.lower() not in ("aantal", "score", "index") and len(e) <= 12:
        return f"{getal} {e}"
    return getal


def _namen(items: Sequence[Dict[str, Any]], eenheid: str) -> str:
    return " en ".join(f"{w['gebied']} ({_waarde_tekst(w, eenheid)})" for w in items)


def samenvatting(f: Dict[str, Any]) -> str:
    """
    Vaste duiding per indicator, uit de cijfers: hoogste, laagste, de gevraagde gebieden
    daartussen en wat gunstig is volgens de richting. Voor het taalmodel (houvast) en de terugvaltekst.
    """
    w, e = f["waarden"], f["eenheid"]
    if len(w) == 1:
        return f"{w[0]['gebied']}: {_waarde_tekst(w[0], e)}."
    hoog = [x for x in w if "hoogste waarde" in x["labels"]]
    laag = [x for x in w if "laagste waarde" in x["labels"]]
    if not hoog:  # alle waarden gelijk
        return f"Alle {len(w)} gebieden hebben dezelfde waarde ({_waarde_tekst(w[0], e)})."
    zinnen = [f"Hoogste waarde: {_namen(hoog, e)}; laagste: {_namen(laag, e)}."]
    midden = [x for x in w if x not in hoog and x not in laag]
    gevraagd_midden = [x for x in midden if x["gevraagd"]] or (midden if len(midden) == 1 else [])
    if gevraagd_midden:
        zinnen.append(f"Daartussen: {_namen(gevraagd_midden, e)}.")
    if f["richting"] == "hoger_is_beter":
        zinnen.append(
            f"Hoger is beter: {' en '.join(x['gebied'] for x in hoog)} {'scoren' if len(hoog) > 1 else 'scoort'} het gunstigst."
        )
    elif f["richting"] == "lager_is_beter":
        zinnen.append(
            f"Lager is beter: {' en '.join(x['gebied'] for x in laag)} {'scoren' if len(laag) > 1 else 'scoort'} het gunstigst, "
            f"{' en '.join(x['gebied'] for x in hoog)} het ongunstigst."
        )
    return " ".join(zinnen)


def eigen_waarde(f: Dict[str, Any]) -> Optional[str]:
    """Bij precies één gevraagd gebied (met buren als referentie): 'Bolsward-Zuidoost: 29,5% (2026).'"""
    gevraagd = [w for w in f["waarden"] if w.get("gevraagd")]
    if len(gevraagd) != 1 or len(f["waarden"]) < 2:
        return None
    w = gevraagd[0]
    jaar = f" ({w['jaar']})" if w.get("jaar") else ""
    return f"{w['gebied']}: {_waarde_tekst(w, f['eenheid'])}{jaar}."


def vaste_tekst(feiten: Sequence[Dict[str, Any]]) -> str:
    """Antwoord zonder taalmodel, alleen uit de feiten (terugval, of zonder LLM-koppeling).
    Eén gevraagd gebied: eerst de waarde van dat gebied, dan ter vergelijking de buren."""
    zinnen = []
    for f in feiten:
        jaren = ", ".join(str(j) for j in f["jaren"])
        kop = f"{f['indicator']} ({f['bron']}" + (f", {jaren}" if jaren else "") + "): "
        eigen = eigen_waarde(f)
        zinnen.append(kop + (f"{eigen} Ter vergelijking: {samenvatting(f)}" if eigen else samenvatting(f)))
    if any(w["demo"] for f in feiten for w in f["waarden"]):
        demo = sorted({w["gebied"] for f in feiten for w in f["waarden"] if w["demo"]})
        zinnen.append(f"Let op: de waarden van {', '.join(demo)} zijn demodata.")
    return " ".join(zinnen)


def bron_getallen(feiten: Sequence[Dict[str, Any]], vraag: str = "") -> Dict[str, Any]:
    """De brondata voor de grounding-check: alle getallen die het model mocht gebruiken."""
    return {
        "vraag": vraag,
        "feiten": [
            {
                "indicator": f["indicator"],
                "eenheid": f["eenheid"],
                "bron": f["bron"],
                "jaren": f["jaren"],
                "aantal": f["aantal_gebieden"],
                "waarden": [[w["waarde"], w["jaar"], w["rang_hoog"]] for w in f["waarden"]],
            }
            for f in feiten
        ],
    }


def controleer_getallen(antwoord: str, feiten: Sequence[Dict[str, Any]], vraag: str = "") -> List[str]:
    """Getallen in het antwoord die niet in de feiten (of de vraag) staan."""
    return ongegronde_getallen(antwoord, bron_getallen(feiten, vraag))


# ── 5. Prompt ────────────────────────────────────────────────────────────────

SYSTEEMPROMPT = """Je bent de D-Omni Assistent. Je beantwoordt een vraag over buurten met UITSLUITEND de cijfers uit het JSON-blok in het bericht.

Regels:
1. Gebruik alleen getallen die in het JSON-blok staan. Reken niet, schat niet, verzin niets.
2. Noem de buurten bij naam. Noem per indicator één keer de bron en het jaar.
3. Neem de duiding over uit 'samenvatting': die zegt wat het hoogst, het laagst en het gunstigst is. Draai dat nooit om. Een waarde zonder 'gunstigst' of 'ongunstigst' zit daartussen; noem die niet gunstig of ongunstig. Bij 'geen oordeel' zeg je niet of iets goed of slecht is.
4. Schrijf waarden met hun eenheid, zoals in het JSON-blok ('246 m', '48,3%').
5. Vraagt iemand naar de hoogste of laagste, noem dan ook het andere uiterste.
6. Staat het gevraagde niet in de cijfers, zeg dat eerlijk.
7. Is een waarde een demowaarde, zeg kort dat het demodata is.
8. Antwoord in het Nederlands, in maximaal 4 zinnen. Gewone tekst: geen kopjes, geen opsomming, geen begroeting, geen JSON."""


def feiten_als_json(feiten: Sequence[Dict[str, Any]]) -> str:
    """De cijfers voor het taalmodel als JSON: per indicator de bron, jaar, richting en waarden."""
    blok = []
    for f in feiten:
        blok.append(
            {
                "indicator": f["indicator"],
                "bron": f["bron"],
                "jaar": f["jaren"],
                "eenheid": f["eenheid"] or None,
                "richting": RICHTING_UITLEG[f["richting"]],
                "aantal_gebieden": f["aantal_gebieden"],
                "samenvatting": samenvatting(f),
                "waarden": [
                    {
                        "gebied": w["gebied"],
                        "waarde": _waarde_tekst(w, f["eenheid"]),
                        **({"jaar": w["jaar"]} if len(f["jaren"]) > 1 and w.get("jaar") else {}),
                        **({"kenmerk": ", ".join(w["labels"])} if w["labels"] else {}),
                        **({"demowaarde": True} if w["demo"] else {}),
                    }
                    for w in f["waarden"]
                ],
            }
        )
    return json.dumps(blok, ensure_ascii=False, indent=1)


def gebruikersprompt(vraag: str, feiten: Sequence[Dict[str, Any]], herkend: Sequence[str]) -> str:
    gebieden = ", ".join(herkend) if herkend else "geen specifiek gebied genoemd"
    return (
        f"Vraag: {vraag}\n"
        f"Herkende gebieden: {gebieden}\n\n"
        f"Cijfers (meest recente jaar per gebied):\n{feiten_als_json(feiten)}\n\n"
        "Beantwoord de vraag in maximaal 4 zinnen. Gebruik alleen deze getallen en noem de buurten bij naam."
    )


def strip_denken(tekst: str) -> str:
    """<think>...</think> van denkende modellen weghalen."""
    tekst = re.sub(r"<think>.*?</think>", "", tekst or "", flags=re.DOTALL)
    return tekst.replace("<think>", "").replace("</think>", "").strip()


# ── Database ─────────────────────────────────────────────────────────────────


def laad_gebieden(db) -> List[Dict[str, Any]]:
    rows = db.execute(
        text(
            "SELECT g.id, g.naam, g.gemeente_code, CAST(g.gebiedstype_id AS text), t.naam "
            "FROM gebieden g LEFT JOIN gebiedstypes t ON t.id = g.gebiedstype_id "
            "WHERE COALESCE(g.actief, true)"
        )
    ).fetchall()
    return [
        {"id": r[0], "naam": r[1], "gemeente_code": r[2], "gebiedstype_id": r[3], "gebiedstype": r[4]} for r in rows
    ]


def voorkeur_gebiedstype(gebieden: Sequence[Dict[str, Any]]) -> Optional[str]:
    """Buurten als die er zijn, anders het type met de meeste gebieden."""
    tellingen: Dict[str, int] = {}
    buurttypes = set()
    for g in gebieden:
        tellingen[g["gebiedstype_id"]] = tellingen.get(g["gebiedstype_id"], 0) + 1
        if "buurt" in (g.get("gebiedstype") or "").lower():
            buurttypes.add(g["gebiedstype_id"])
    kandidaten = buurttypes or set(tellingen)
    return max(kandidaten, key=tellingen.get) if kandidaten else None


def laad_indicatoren(db) -> List[Dict[str, Any]]:
    """Actieve indicatoren met minstens één waarde."""
    rows = db.execute(
        text(
            "SELECT CAST(i.uuid AS text), i.naam, i.eenheid, i.bron, i.score_type, i.interpretatie_logica "
            "FROM indicatoren i WHERE i.is_actief = true "
            "AND EXISTS (SELECT 1 FROM gebied_data d WHERE d.indicator_uuid = i.uuid)"
        )
    ).fetchall()
    return [
        {"uuid": r[0], "naam": r[1], "eenheid": r[2], "bron": r[3], "score_type": r[4], "interpretatie_logica": r[5]}
        for r in rows
    ]


def laad_waarden(db, indicator_uuids: Sequence[str], gebied_ids: Sequence[str]) -> List[Dict[str, Any]]:
    """Meest recente waarde per gebied en indicator (scenario 'current').

    Rust die waarde op te weinig waarnemingen (kleine aantallen, #325), dan valt hij weg."""
    if not indicator_uuids or not gebied_ids:
        return []
    rows = db.execute(
        text(
            "SELECT r.gebied_id, r.indicator_uuid, r.waarde, r.jaar, r.bron FROM ("
            "SELECT DISTINCT ON (d.gebied_id, d.indicator_uuid) d.gebied_id, "
            "CAST(d.indicator_uuid AS text) AS indicator_uuid, d.waarde, "
            "COALESCE(d.jaar, CAST(EXTRACT(YEAR FROM d.datum) AS integer)) AS jaar, d.bron, d.n "
            "FROM gebied_data d "
            "WHERE CAST(d.indicator_uuid AS text) = ANY(:uuids) AND d.gebied_id = ANY(:ids) "
            "AND COALESCE(d.scenario_id, 'current') = 'current' "
            "ORDER BY d.gebied_id, d.indicator_uuid, d.jaar DESC NULLS LAST, d.datum DESC NULLS LAST"
            ") r WHERE " + ka.niet_onderdrukt_sql("r")
        ),
        {"uuids": list(indicator_uuids), "ids": list(gebied_ids)},
    ).fetchall()
    return [
        {"gebied_id": r[0], "indicator_uuid": r[1], "waarde": float(r[2]), "jaar": r[3], "bron": r[4]} for r in rows
    ]


# ── Route ────────────────────────────────────────────────────────────────────


def deelvragen(vraag: str) -> List[str]:
    """'Welke buurt ligt het verst van een koele plek, en waar wonen de meeste 65-plussers?' → 2 delen."""
    delen = re.split(r"[.?!;,]|\s+en\s+(?=waar|welke|hoe|wat)", vraag or "")
    return [d.strip() for d in delen if d and len(d.strip()) > 3]


# Foutteksten die LLMService als 'text' teruggeeft (Ollama en, na #88, OpenAI/gateway)
_MODELFOUTEN = (
    "Error contacting",
    "Generatie mislukt",
    "LLM-server",
    "Fout bij",
    "AI-samenvatting is nu niet beschikbaar",
)


# Waar de buurt vandaan kwam als die niet in de vraag stond (context.buurt_herkomst, #336)
_HERKOMST = {"adres": "gevonden bij je postcode of adres", "locatie": "gevonden bij je locatie"}


def aanname_tekst(herkenning: GebiedHerkenning, herkomst: Optional[str] = None) -> Optional[str]:
    """
    Van welk gebied gaat het antwoord uit, als dat niet in de vraag stond (#233)? Dan zegt de
    assistent dat vooraf: 'Ik ga uit van Bolsward-Zuidoost (geselecteerd op de kaart).'
    Kwam de buurt uit een postcode/adres of de locatie (#336), dan zegt hij dat.
    """
    if herkenning.bron != "kaart" or not herkenning.herkend:
        return None
    namen = herkenning.herkend
    if len(namen) > 5:
        lijst = f"{', '.join(namen[:5])} en nog {len(namen) - 5} andere"
    elif len(namen) > 1:
        lijst = f"{', '.join(namen[:-1])} en {namen[-1]}"
    else:
        lijst = namen[0]
    return (
        f"Ik ga uit van {lijst} ({_HERKOMST.get(herkomst, 'geselecteerd op de kaart')}). Een andere buurt? "
        "Selecteer die op de kaart of noem de naam in je vraag."
    )


def beantwoord_datavraag(
    vraag: str,
    context: Optional[Dict[str, Any]],
    db,
    zoek: Callable[[str], List[Dict[str, Any]]],
    vraag_llm: Callable[[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Beantwoord een datavraag; None als het geen datavraag is (dan navigeert de chat zoals voorheen).

    zoek(tekst):          AI-zoeken, [{uuid, naam, score}]
    vraag_llm(sys, usr, bronnen):  {"text": ..., "debug": {...}}; bronnen = indicator-uuid's (AI-logboek)
    """
    context = context or {}
    if is_navigatie(vraag):
        return None
    expliciet = is_datavraag(vraag)

    gebieden = laad_gebieden(db)
    try:
        from omnitwin.services.gemeente_validatie import laad_gemeenten

        gemeenten = laad_gemeenten(db, alleen_met_gebieden=True)
    except Exception:
        db.rollback()
        gemeenten = {}
    voorkeur = voorkeur_gebiedstype(gebieden)
    selectie = context.get("geselecteerde_gebied_ids")
    herkenning = herken_gebieden(
        vraag,
        gebieden,
        gemeenten,
        context.get("huidig_gebied_id"),
        voorkeur,
        geselecteerd=selectie if isinstance(selectie, list) else (),
    )
    per_id = {g["id"]: g for g in gebieden}

    # 'bij mij in de buurt' zonder geselecteerde buurt: niet alle buurten, maar vragen welke (#233)
    eigen_buurt = vraagt_eigen_buurt(vraag) and not herkenning.gevraagd

    # Geen gebied in vraag of kaart: alle gebieden van het voorkeurstype, als dat er weinig zijn
    if not herkenning.gevraagd and not eigen_buurt:
        van_type = [g["id"] for g in gebieden if g["gebiedstype_id"] == voorkeur]
        if 0 < len(van_type) <= MAX_ALLE_GEBIEDEN:
            herkenning.gevraagd = van_type
            herkenning.bron = "alle"

    # Indicatoren: woorden, begrippen en AI-zoeken per deelvraag (zonder gebiedsnamen)
    gebiedswoorden = (
        [g["naam"] for g in gebieden] + [plaats_van(g["naam"]) for g in gebieden] + list(gemeenten.values())
    )
    onderwerp = resterende_tekst(vraag, gebiedswoorden)
    ai_treffers: List[Dict[str, Any]] = []
    for deel in deelvragen(vraag):
        tekst = resterende_tekst(deel, gebiedswoorden)
        if len(tekst) > 3:
            try:
                ai_treffers.extend(r for r in (zoek(tekst) or []) if "error" not in r)
            except Exception:
                db.rollback()
    indicatoren = laad_indicatoren(db)
    treffers = herken_indicatoren(onderwerp, indicatoren, ai_treffers)

    gebied_herkend = herkenning.bron in ("vraag", "kaart")
    if not expliciet and not ((gebied_herkend or eigen_buurt) and treffers):
        return None  # geen datapatroon, of geen gebied plus indicator: de gewone chat neemt het over
    if not treffers and not gebied_herkend:
        return None  # geen onderwerp en geen gebied: de gewone chat neemt het over

    basis = {
        "herkend": herkenning.herkend,
        "gebieden_bron": herkenning.bron,
        "feiten": [],
        "aanname": aanname_tekst(herkenning, context.get("buurt_herkomst")),
        "vraag_buurt": False,
        "indicatoren": treffers,
        "gebied_ids": [],
        "llm_gebruikt": False,
        "model": None,
        "gebiedstype_id": None,
        "ongegrond": [],
        "llm_fout": False,
    }

    if not treffers:
        plek = f" voor {', '.join(herkenning.herkend)}" if herkenning.herkend else ""
        return {
            **basis,
            "narrative": (
                f"Daar heb ik geen cijfers over{plek}: ik vind in de database geen indicator die bij deze "
                "vraag past. Ik verzin geen getallen. Probeer een ander woord, of zoek in de lijst met indicatoren."
            ),
        }

    if not herkenning.gevraagd:
        namen = ", ".join(t.naam for t in treffers)
        if eigen_buurt:
            # #336: de viewer toont bij vraag_buurt een veld voor postcode/adres en 'Gebruik mijn locatie'
            return {
                **basis,
                "vraag_buurt": True,
                "narrative": (
                    f"Welke buurt is jouw buurt? Vul hieronder je postcode of adres in, gebruik je locatie, "
                    f"of selecteer de buurt op de kaart. Je kunt ook de naam noemen, bijvoorbeeld "
                    f"'... in Bolsward-Zuidoost'. Ik zoek dan in: {namen}."
                ),
            }
        return {
            **basis,
            "narrative": (
                "Voor welk gebied wil je dit weten? Noem een buurt, woonplaats of gemeente, "
                "of selecteer een gebied op de kaart."
            ),
        }

    alle_ids = herkenning.gevraagd + [i for i in herkenning.referentie if i not in herkenning.gevraagd]
    ind_meta = {i["uuid"]: i for i in indicatoren}
    waarden = laad_waarden(db, [t.uuid for t in treffers], alle_ids)
    feiten = bouw_feiten(
        [ind_meta[t.uuid] for t in treffers],
        waarden,
        {i: per_id[i]["naam"] for i in alle_ids if i in per_id},
        herkenning.gevraagd,
        gevraagde_volgorde(vraag),
        gevraagd_aantal(vraag),
    )
    basis["gebied_ids"] = alle_ids
    eerste = per_id.get(alle_ids[0], {})
    basis["gebiedstype_id"] = eerste.get("gebiedstype_id")
    basis["gemeente_code"] = eerste.get("gemeente_code")
    basis["feiten"] = feiten

    if not feiten:
        namen = ", ".join(t.naam for t in treffers)
        return {
            **basis,
            "narrative": (
                f"Ik vind wel indicatoren ({namen}), maar geen waarden voor "
                f"{', '.join(herkenning.herkend) or 'deze gebieden'}. Ik verzin geen getallen."
            ),
        }

    # Taalmodel: alleen de feiten; daarna controle op de getallen.
    # context.geen_llm: direct de vaste tekst (werkt zonder model; ook voor tests)
    tekst, model = "", None
    if not context.get("geen_llm"):
        try:
            antwoord = (
                vraag_llm(
                    SYSTEEMPROMPT,
                    gebruikersprompt(vraag, feiten, herkenning.herkend),
                    [f["indicator_uuid"] for f in feiten],
                )
                or {}
            )
            # Foutvlag van LLMService (#65): de tekst is dan een foutmelding, geen antwoord
            tekst = "" if antwoord.get("error") else strip_denken(antwoord.get("text", ""))
            model = (antwoord.get("debug") or {}).get("model")
        except Exception:
            tekst, model = "", None
    fout = not tekst or any(m in tekst for m in _MODELFOUTEN)
    ongegrond = [] if fout else controleer_getallen(tekst, feiten, vraag)
    llm_gebruikt = not fout and not ongegrond
    if not llm_gebruikt:
        tekst = vaste_tekst(feiten)

    met_data = {f["indicator_uuid"] for f in feiten}
    zonder_data = [t.naam for t in treffers if t.uuid not in met_data]
    if zonder_data:
        tekst += f" Geen waarden gevonden voor: {', '.join(zonder_data)}."
    return {
        **basis,
        "narrative": tekst,
        "llm_gebruikt": llm_gebruikt,
        "model": model,
        "ongegrond": ongegrond,
        "llm_fout": fout,
    }
