"""
Use cases uit de innovatieaanvraag, nagespeeld op Bolsward (TC-06-005 t/m TC-06-008).

Leest de use-casepakketten in usecases/<naam>/usecase.json (geladen door
db-init via init_data/scripts/laad_usecase.py). Per use case: zijn de
indicatoren er (ook de afgeleide), hebben de Bolsward-buurten waarden, en is
de richting goed? Plus: vindt de AI-zoekfunctie de indicatoren bij de vraag?

Bekende tekortkomingen staan als xfail met het issue erbij; als een fix landt,
slaagt de test (XPASS) en kan de markering weg.

Draaien: zie tests/integration/test_sample_stack.py (zelfde stack en omgeving).
"""

import json
import os
from pathlib import Path

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30
BOLSWARD = {"BU19000001": "Bolsward-Noord", "BU19000002": "Bolsward-Zuidoost", "BU19000004": "Bolsward-Noordoost"}

ROOT = Path(__file__).resolve().parents[2]


def laad_usecases():
    """usecases/<naam>/usecase.json: data + inrichting + verwachte uitkomst."""
    uit = {}
    for f in sorted((ROOT / "usecases").glob("*/usecase.json")):
        u = json.loads(f.read_text(encoding="utf-8"))
        if "persona" not in u:  # alleen de demo-use cases (TC-06-*) hebben persona en verwachting
            continue
        uit[f"{u['id']} {f.parent.name}"] = u
    return uit


USE_CASES = laad_usecases()


def namen(uc):
    d = USE_CASES[uc]["data"]
    return [i["naam"] for i in d["indicatoren"]] + [a["naam"] for a in d.get("afgeleid", [])]


def lager_is_beter(uc):
    return [i["naam"] for i in USE_CASES[uc]["data"]["indicatoren"] if i["richting"] == "lager_is_beter"]


def get(pad, **params):
    r = requests.get(f"{BASE_URL}{pad}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


@pytest.fixture(scope="module")
def indicatoren():
    rijen = get("/api/data/indicatoren", select="uuid,naam,polariteit,score_type,interpretatie_logica")
    return {i["naam"]: i for i in rijen}


@pytest.fixture(scope="module")
def waarden():
    rijen = get(
        "/api/data/vw_gebied_indicator_actueel",
        select="gebied_id,indicator_uuid,waarde",
        gebied_id=f"in.({','.join(BOLSWARD)})",
    )
    return {(r["gebied_id"], r["indicator_uuid"]): r["waarde"] for r in rijen if r["waarde"] is not None}


@pytest.mark.parametrize("uc", USE_CASES)
def test_indicatoren_aanwezig_met_waarden_voor_bolsward(uc, indicatoren, waarden):
    ontbreekt, zonder_waarde = [], []
    for naam in namen(uc):
        ind = indicatoren.get(naam)
        if not ind:
            ontbreekt.append(naam)
            continue
        for gid, gnaam in BOLSWARD.items():
            if (gid, ind["uuid"]) not in waarden:
                zonder_waarde.append(f"{naam} / {gnaam}")
    assert not ontbreekt, f"{uc}: indicatoren ontbreken: {ontbreekt}"
    assert not zonder_waarde, f"{uc}: geen waarde voor: {zonder_waarde}"


@pytest.mark.parametrize("uc", [u for u in USE_CASES if lager_is_beter(u)])
def test_richting_lager_is_beter(uc, indicatoren):
    """De inrichting van de use case (laad_usecase.py) zet de richting goed (#120)."""
    # Eén codering (polariteit); de oude kolommen volgen die via de trigger (V046)
    fout = [
        n
        for n in lager_is_beter(uc)
        if indicatoren[n]["polariteit"] != "lager_is_beter"
        or indicatoren[n]["score_type"] != "+/-"
        or indicatoren[n]["interpretatie_logica"] != "-/+"
    ]
    assert not fout, f"{uc}: staat als 'hoger is beter': {fout}"


@pytest.mark.parametrize("uc", USE_CASES)
def test_ai_zoeken_vindt_indicator_bij_vraag(uc):
    resultaten = get("/api/ai/kompas/search", q=USE_CASES[uc]["ai_zoekvraag"])
    gevonden = {r.get("naam") or r.get("indicator_naam") for r in resultaten}
    assert gevonden & set(namen(uc)), f"{uc}: AI-zoeken vond {sorted(n for n in gevonden if n)}"


@pytest.mark.parametrize("uc", USE_CASES)
def test_gebiedsdetail_met_afgeleide_indicatoren(uc):
    """Afgeleide indicatoren hebben een uuid5; de API moet die accepteren (geen 500)."""
    r = requests.get(f"{BASE_URL}/api/gebiedsmonitor/gebieden/{USE_CASES[uc]['data']['focus']}", timeout=TIMEOUT)
    assert r.status_code == 200, f"{uc}: {r.status_code} {r.text[:200]}"
