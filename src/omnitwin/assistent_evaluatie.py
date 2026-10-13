"""
Evaluatie van de D-Omni Assistent (#233): vindt hij bij een vraag de juiste indicatoren?

De vragen en de verwachte indicatoren staan in tests/data/assistent_evaluatie.json.
Per vraag:
- type 'zoek': GET /api/ai/kompas/search (de lijst die de gebruiker ziet);
- type 'datavraag': POST /api/chat met de testbuurt als selectie; goed gerouteerd als het
  antwoord een datavraag is met een cijfer voor die buurt. De rangorde komt dan uit de
  indicatoren die de chat als onderbouwing teruggeeft.
  'selectie' (lijst gebied-id's) vervangt de testbuurt: [] = niets geselecteerd, twee id's =
  een multi-selectie (#233). 'route': 'vraag_buurt' = de assistent hoort te vragen welke buurt
  (geen selectie, 'mijn buurt'). Bij 'mijn_buurt' met een selectie moet het antwoord ook zeggen
  van welke buurt het uitgaat ('aanname' met de naam).

Maten (k uit het bestand, standaard 3):
- precision@k: deel van de getoonde top-k dat relevant is. Toont de assistent er minder dan k,
  dan telt alleen wat getoond is (liever 2 goede dan 8 matige); niets getoond = 0.
- recall@k: deel van de relevante indicatoren in de top-k, met als noemer min(k, aantal relevant).
- MRR: 1 / positie van de eerste relevante indicator (0 als die er niet bij zit).
- routering: deel van de datavragen dat als datavraag met een cijfer wordt beantwoord.

Vragen met "holdout" zijn niet gebruikt om synoniemen en drempels af te stemmen; hun score
apart laat zien of de verbetering ook geldt voor vragen die we niet vooraf kenden. De drempels
('drempels') gelden voor de afgestemde vragen; de holdout heeft eigen, lagere drempels
('drempels_holdout') die alleen terugval vangen (#336). Zou de holdout dezelfde drempel moeten
halen, dan dwingt elke nieuwe holdout-vraag die faalt tot afstemmen op die vraag, en is het geen
holdout meer. Na zo'n afstemronde gaan de oude holdout-vragen naar de afgestemde set
('holdout_<versie>': true) en komen er nieuwe bij.

Draaien tegen een stack met sample-data:
    python scripts/ai/evalueer_assistent.py --url http://localhost:8105
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

TESTSET = Path(__file__).resolve().parents[2] / "tests" / "data" / "assistent_evaluatie.json"


def laad_testset(pad: Path = TESTSET) -> Dict[str, Any]:
    return json.loads(Path(pad).read_text(encoding="utf-8"))


def precision_at_k(gevonden: Sequence[str], relevant: Sequence[str], k: int) -> float:
    top = list(gevonden)[:k]
    if not top:
        return 0.0
    return sum(1 for u in top if u in relevant) / len(top)


def recall_at_k(gevonden: Sequence[str], relevant: Sequence[str], k: int) -> float:
    if not relevant:
        return 1.0
    top = list(gevonden)[:k]
    return sum(1 for u in set(top) if u in relevant) / min(k, len(set(relevant)))


def reciprocal_rank(gevonden: Sequence[str], relevant: Sequence[str]) -> float:
    for i, u in enumerate(gevonden, start=1):
        if u in relevant:
            return 1.0 / i
    return 0.0


def scoor(resultaten: List[Dict[str, Any]], k: int) -> Dict[str, float]:
    """resultaten: [{type, relevant, gevonden: [uuid], gerouteerd: bool|None}] → gemiddelden."""
    n = len(resultaten) or 1
    datavragen = [r for r in resultaten if r.get("type") == "datavraag"]
    return {
        "aantal": len(resultaten),
        "precision_at_k": sum(precision_at_k(r["gevonden"], r["relevant"], k) for r in resultaten) / n,
        "recall_at_k": sum(recall_at_k(r["gevonden"], r["relevant"], k) for r in resultaten) / n,
        "mrr": sum(reciprocal_rank(r["gevonden"], r["relevant"]) for r in resultaten) / n,
        "routering": (sum(1 for r in datavragen if r.get("gerouteerd")) / len(datavragen)) if datavragen else 1.0,
        "gemiddeld_getoond": sum(len(r["gevonden"]) for r in resultaten) / n,
    }


def onder_drempel(scores: Dict[str, float], drempels: Dict[str, float]) -> List[str]:
    """Maten die onder de afgesproken drempel liggen, leesbaar."""
    return [f"{m} {scores[m]:.3f} < {d}" for m, d in drempels.items() if scores.get(m, 0.0) < d]


def drempelfouten(resultaten: List[Dict[str, Any]], testset: Dict[str, Any]) -> List[str]:
    """Maten onder de drempel: afgestemde vragen tegen 'drempels', holdout tegen 'drempels_holdout'."""
    k = testset.get("k", 3)
    fout = []
    for naam, holdout, sleutel in (("afgestemd", False, "drempels"), ("holdout", True, "drempels_holdout")):
        deel = [r for r in resultaten if bool(r.get("holdout")) == holdout]
        if deel and testset.get(sleutel):
            fout += [f"{naam}: {f}" for f in onder_drempel(scoor(deel, k), testset[sleutel])]
    return fout


def gerouteerd(
    v: Dict[str, Any], antwoord: Dict[str, Any], selectie: Sequence[str], namen: Optional[Dict[str, str]] = None
) -> bool:
    """Goed beantwoord? Zie de kop van dit bestand ('route', 'selectie', 'mijn_buurt')."""
    if v.get("route") == "vraag_buurt":
        return "welke buurt" in (antwoord.get("narrative") or "").lower() and not antwoord.get("gegevens")
    if antwoord.get("intent") != "DATAVRAAG":
        return False
    met_cijfer = {g.get("gebied_id") for g in antwoord.get("gegevens") or []}
    verwacht = list(v.get("gebieden") or selectie)
    if not all(g in met_cijfer for g in verwacht):
        return False
    if v.get("mijn_buurt") and selectie:
        aanname = antwoord.get("aanname") or ""
        return all((namen or {}).get(g, g) in aanname for g in selectie)
    return True


def evalueer(
    testset: Dict[str, Any], zoek: Callable[[str], List[str]], chat: Callable[..., Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    zoek(vraag)               → uuids in de volgorde die de gebruiker ziet
    chat(vraag, gebied_ids)   → antwoord van /api/chat (dict); gebied_ids = de selectie op de kaart
    """
    gebied = testset.get("gebied")
    namen = testset.get("gebiedsnamen") or {}
    uit = []
    for v in testset["vragen"]:
        r = {
            "vraag": v["vraag"],
            "type": v["type"],
            "relevant": v["relevant"],
            "gerouteerd": None,
            "holdout": bool(v.get("holdout")),
        }
        if v["type"] == "datavraag":
            selectie = v["selectie"] if "selectie" in v else ([gebied] if gebied else [])
            antwoord = chat(v["vraag"], selectie)
            r["intent"] = antwoord.get("intent")
            r["gevonden"] = [i["uuid"] for i in antwoord.get("indicatoren") or []]
            r["gerouteerd"] = gerouteerd(v, antwoord, selectie, namen)
            r["narrative"] = antwoord.get("narrative", "")
            r["aanname"] = antwoord.get("aanname")
        else:
            r["gevonden"] = zoek(v["vraag"])
        uit.append(r)
    return uit


def http_zoek_en_chat(basis_url: str, timeout: int = 120):
    """zoek- en chatfuncties tegen een draaiende installatie."""
    import requests

    s = requests.Session()
    basis = basis_url.rstrip("/")

    def zoek(vraag: str) -> List[str]:
        r = s.get(f"{basis}/api/ai/kompas/search", params={"q": vraag, "limit": 10}, timeout=timeout)
        r.raise_for_status()
        return [x["uuid"] for x in r.json() if "uuid" in x]

    def chat(vraag: str, gebied_ids: Sequence[str] = ()) -> Dict[str, Any]:
        context: Dict[str, Any] = {"geen_llm": True}
        if isinstance(gebied_ids, str):
            gebied_ids = [gebied_ids]
        if gebied_ids:
            # zoals static/js/chat.js: het eerste gebied plus de hele selectie
            context["huidig_gebied_id"] = gebied_ids[0]
            context["geselecteerde_gebied_ids"] = list(gebied_ids)
        r = s.post(f"{basis}/api/chat", json={"vraag": vraag, "context": context}, timeout=timeout)
        r.raise_for_status()
        return r.json()

    return zoek, chat
