"""
Datavragen in de chat (#149), per use case uit usecases/*/usecase.json.

Per use case met een datavraag (persona.vraag):
- integration (zonder model): de chat haalt de juiste cijfers op. Elk getal uit
  verwacht.verwacht staat in de opgehaalde gegevens, en die gegevens zijn gelijk aan de
  database (PostgREST, vw_gebied_indicator_actueel);
- llm (met model): het antwoord noemt de verwachte buurten en elk getal in het antwoord
  is herleidbaar tot de gegevens (tests/grounding.py).

Plus: een vraag zonder passende data geeft eerlijk 'geen cijfers'.

Draaien tegen een stack met de sample-use-cases (LOAD_SAMPLE_DATA=true):

    OMNITWIN_BASE_URL=http://localhost:8120 pytest -m integration tests/integration/test_chat_datavragen.py
    LLM_TEST=1 OMNITWIN_BASE_URL=http://localhost:8120 pytest -m llm tests/integration/test_chat_datavragen.py

Het model staat in llm_config (README, 'AI Instellen'). Zonder werkend model geeft de chat
de vaste tekst uit de cijfers (debug.llm_gebruikt = false); de llm-tests falen dan.
"""

import json
import os
import re
from pathlib import Path

import pytest
import requests

from omnitwin.services.chat_datavraag import is_datavraag
from tests.grounding import getallen_in_bron, getallen_in_tekst, grounding_melding, ongegronde_getallen

BASE_URL = (os.environ.get("OMNITWIN_BASE_URL") or os.environ.get("LLM_TEST_BASE_URL") or "http://localhost").rstrip(
    "/"
)
TIMEOUT = int(os.environ.get("LLM_TEST_TIMEOUT", "900"))
ROOT = Path(__file__).resolve().parents[2]


def laad_usecases():
    uit = {}
    for f in sorted((ROOT / "usecases").glob("*/usecase.json")):
        u = json.loads(f.read_text(encoding="utf-8"))
        if "persona" not in u:  # alleen de demo-use cases (TC-06-*) hebben persona en verwachting
            continue
        if is_datavraag(u["persona"]["vraag"]):
            uit[f"{u['id']} {f.parent.name}"] = u
    return uit


USE_CASES = laad_usecases()


def verwachte_buurten(uc):
    """Buurtnamen uit data.gebieden die in verwacht.verwacht genoemd worden."""
    u = USE_CASES[uc]
    tekst = u["verwacht"]["verwacht"]
    return [n for n in u["data"]["gebieden"].values() if re.search(rf"\b{re.escape(n)}\b(?!-)", tekst)]


def verwachte_getallen(uc):
    """Niet-triviale getallen in verwacht.verwacht (zoals geschreven), behalve die uit de vraag ('65-plussers')."""
    in_vraag = {w for _, ws, _, _ in getallen_in_tekst(USE_CASES[uc]["persona"]["vraag"]) for w in ws}
    return [
        (raw, waarden, pct)
        for raw, waarden, pct, triviaal in getallen_in_tekst(USE_CASES[uc]["verwacht"]["verwacht"])
        if not triviaal and not (waarden & in_vraag)
    ]


_antwoorden = {}


def vraag(uc):
    """Eén chat-verzoek per use case, gedeeld door de tests (model is traag)."""
    if uc not in _antwoorden:
        r = requests.post(
            f"{BASE_URL}/api/chat", json={"vraag": USE_CASES[uc]["persona"]["vraag"], "context": {}}, timeout=TIMEOUT
        )
        assert r.status_code == 200, r.text[:500]
        _antwoorden[uc] = r.json()
    return _antwoorden[uc]


def bron(antwoord):
    """De data waarop het antwoord mag steunen."""
    return {"gegevens": antwoord.get("gegevens") or [], "bronnen": antwoord.get("bronnen") or []}


# ── Zonder model ─────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.parametrize("uc", USE_CASES)
def test_datavraag_haalt_verwachte_cijfers_op(uc):
    a = vraag(uc)
    assert a["intent"] == "DATAVRAAG", a
    gegevens = a.get("gegevens") or []
    assert gegevens, f"{uc}: geen gegevens opgehaald"
    assert a.get("bronnen"), f"{uc}: geen bronregel"

    gebieden = {g["gebied"] for g in gegevens}
    for naam in verwachte_buurten(uc):
        assert naam in gebieden, f"{uc}: {naam} niet in de opgehaalde gebieden {sorted(gebieden)}"

    # Elk getal uit de verwachte uitkomst moet in de opgehaalde gegevens staan
    bron_getallen = [g["waarde"] for g in gegevens]
    for raw, _, _ in verwachte_getallen(uc):
        assert not ongegronde_getallen(raw, bron_getallen), (
            f"{uc}: verwacht getal {raw} niet in de gegevens: "
            + json.dumps([(g["indicator"], g["gebied"], g["waarde"]) for g in gegevens], ensure_ascii=False)
        )


@pytest.mark.integration
@pytest.mark.parametrize("uc", USE_CASES)
def test_gegevens_gelijk_aan_database(uc):
    gegevens = vraag(uc).get("gegevens") or []
    ids = sorted({g["gebied_id"] for g in gegevens})
    r = requests.get(
        f"{BASE_URL}/api/data/vw_gebied_indicator_actueel",
        params={"select": "gebied_id,indicator_uuid,waarde,jaar", "gebied_id": f"in.({','.join(ids)})"},
        timeout=30,
    )
    r.raise_for_status()
    db = {(x["gebied_id"], x["indicator_uuid"]): x for x in r.json()}
    for g in gegevens:
        rij = db.get((g["gebied_id"], g["indicator_uuid"]))
        assert rij is not None, f"{uc}: {g['indicator']} / {g['gebied']} niet in de database"
        assert abs(float(rij["waarde"]) - g["waarde"]) < 1e-6, f"{uc}: {g} ≠ database {rij}"
        assert rij["jaar"] == g["jaar"], f"{uc}: jaar {g['jaar']} ≠ database {rij['jaar']} ({g['indicator']})"


@pytest.mark.integration
@pytest.mark.parametrize("uc", USE_CASES)
def test_knoppen_bij_datavraag(uc):
    a = vraag(uc)
    types = [x["type"] for x in a["acties"]]
    assert "TOON_OP_KAART" in types and "OPEN_KOMPAS" in types and "MAAK_RAPPORT" in types, types
    toon = next(x for x in a["acties"] if x["type"] == "TOON_OP_KAART")
    assert toon["indicator_uuid"] and toon["gebied_ids"], toon


@pytest.mark.integration
def test_vraag_zonder_data_zegt_eerlijk_geen_cijfers():
    r = requests.post(
        f"{BASE_URL}/api/chat", json={"vraag": "Hoeveel windmolens staan er in Bolsward?"}, timeout=TIMEOUT
    )
    assert r.status_code == 200, r.text[:500]
    a = r.json()
    assert a["intent"] == "DATAVRAAG"
    assert not a.get("gegevens")
    assert "geen cijfers" in a["narrative"].lower(), a["narrative"]


@pytest.mark.integration
@pytest.mark.parametrize("uc", USE_CASES)
def test_zonder_llm_vaste_tekst_met_juiste_cijfers(uc):
    """Out of the box, zonder LLM-koppeling: de vaste tekst noemt de buurten en de verwachte getallen."""
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"vraag": USE_CASES[uc]["persona"]["vraag"], "context": {"geen_llm": True}},
        timeout=60,
    )
    assert r.status_code == 200, r.text[:500]
    a = r.json()
    assert a["intent"] == "DATAVRAAG" and a["debug"]["llm_gebruikt"] is False
    for naam in verwachte_buurten(uc):
        assert naam in a["narrative"], f"{uc}: {naam} ontbreekt in: {a['narrative']}"
    tekst_getallen = getallen_in_bron(a["narrative"])
    for raw, _, _ in verwachte_getallen(uc):
        assert not ongegronde_getallen(raw, tekst_getallen), f"{uc}: {raw} ontbreekt in: {a['narrative']}"
    ongegrond = ongegronde_getallen(a["narrative"], bron(a))
    assert not ongegrond, grounding_melding(uc, a["narrative"], bron(a), ongegrond)
    assert "json" not in a["narrative"].lower() and "importbestand" not in a["narrative"]


# TC-06-004 (demo-kernvraag): geen patroon als 'welke buurt', wel gebied + indicator
GROEN_VRAAG = "Hoe groen is Bolsward-Zuidoost?"


@pytest.mark.integration
@pytest.mark.parametrize("geen_llm", [True, False], ids=["zonder-llm", "met-llm-of-terugval"])
def test_tc_06_004_hoe_groen(geen_llm):
    r = requests.post(
        f"{BASE_URL}/api/chat", json={"vraag": GROEN_VRAAG, "context": {"geen_llm": geen_llm}}, timeout=TIMEOUT
    )
    assert r.status_code == 200, r.text[:500]
    a = r.json()
    assert a["intent"] == "DATAVRAAG", a
    gegevens = a["gegevens"]
    assert {g["indicator"] for g in gegevens} >= {"Oppervlak groen per inwoner"}
    groen = {g["gebied"]: g["waarde"] for g in gegevens if g["indicator"] == "Oppervlak groen per inwoner"}
    assert "Bolsward-Zuidoost" in groen and {"Bolsward-Noord", "Bolsward-Noordoost"} <= set(groen), groen
    assert "Bolsward-Zuidoost" in a["narrative"]
    ka = a["kaart_actie"]
    # De buurten van de wijk Bolsward (BU190000..); met alle CBS-buurten (#236) zijn dat er meer dan drie
    assert ka["indicator_uuid"] and ka["gebied_ids"][0] == "BU19000002"
    assert {"BU19000001", "BU19000004"} <= set(ka["gebied_ids"]), ka
    assert all(g.startswith("BU190000") for g in ka["gebied_ids"]), ka
    ongegrond = ongegronde_getallen(a["narrative"], bron(a) | {"vraag": GROEN_VRAAG})
    assert not ongegrond, grounding_melding("TC-06-004", a["narrative"], bron(a), ongegrond)


# ── Met model ────────────────────────────────────────────────────────────────

llm = pytest.mark.skipif(os.environ.get("LLM_TEST") != "1", reason="alleen met LLM_TEST=1 en een model")


@pytest.mark.llm
@llm
@pytest.mark.parametrize("uc", USE_CASES)
def test_antwoord_door_model(uc):
    a = vraag(uc)
    assert a["debug"].get("llm_gebruikt"), f"{uc}: geen modeltekst (terugval): {a['debug']}"


@pytest.mark.llm
@llm
@pytest.mark.parametrize("uc", USE_CASES)
def test_antwoord_noemt_verwachte_buurten(uc):
    a = vraag(uc)
    for naam in verwachte_buurten(uc):
        assert naam in a["narrative"], f"{uc}: {naam} ontbreekt in: {a['narrative']}"


@pytest.mark.llm
@llm
@pytest.mark.parametrize("uc", USE_CASES)
def test_elk_getal_herleidbaar(uc):
    a = vraag(uc)
    b = bron(a)
    b["vraag"] = USE_CASES[uc]["persona"]["vraag"]
    ongegrond = ongegronde_getallen(a["narrative"], b)
    assert not ongegrond, grounding_melding(uc, a["narrative"], b, ongegrond)
