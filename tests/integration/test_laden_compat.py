"""
Integratietest compatibiliteitsingang SWF-monitor (#205 stap 9) tegen een draaiende stack met Keycloak.

Zelfde opzet als tests/integration/test_laden_api.py (machineclient met `beheerder` en
`datasets:laden`). Het schrijvende deel draait alleen als `swf-monitor-waarden` nog niet
geregistreerd is (verse stack): dan registreert de test hem zoals use case swf-adapter-fme en
levert één waarde in jaar 2098 op een indicator die op CBS-buurten mag, zodat de demodata, een
geladen monitor en de waarden van test_laden_api.py (jaar 2099)
niet geraakt worden. Responses worden getoetst aan docs/api/laden/openapi.yaml.
"""

import json
import os

import pytest
import requests

from omnitwin import usecases as uc
from omnitwin.laden.registratie import laad_openapi, valideer

pytestmark = pytest.mark.integration

BASIS = uc.basis_url()
API = f"{BASIS}/api/laden/v1"
COMPAT = f"{API}/compat/swf-monitor/monitor_api"
SPEC = laad_openapi()
GEBIED = "BU19000002"
CBS_BUURTEN = "afba67cb-6b38-4723-9c95-102a22d5b38a"
PADEN = [
    ("POST", "indicator/setup/inlezen"),
    ("POST", "indicator_waarde/inlezen"),
    ("GET", "indicator/setup"),
    ("GET", "indicator_waarde"),
    ("GET", "indicator_waarde/00000000-0000-4000-8000-000000000999"),
]

if not uc.laad_api_beschikbaar(BASIS):
    pytest.skip(f"laad-API niet beschikbaar op {API}", allow_module_level=True)
if not (os.environ.get("OMNITWIN_CLIENT_ID") and os.environ.get("OMNITWIN_CLIENT_SECRET")):
    pytest.skip("geen machineclient (OMNITWIN_CLIENT_ID, OMNITWIN_CLIENT_SECRET)", allow_module_level=True)


def schema_fouten(data, naam):
    return valideer(data, SPEC["components"]["schemas"][naam], SPEC)


def probleem(r, status, code=None):
    assert r.status_code == status, r.text[:500]
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers.get("api-version")
    assert schema_fouten(r.json(), "Probleem") == []
    if code:
        assert r.json()["code"] == code, r.json()


@pytest.fixture(scope="module")
def s():
    return uc.LaadApi(BASIS).s


@pytest.mark.parametrize("methode,pad", PADEN)
def test_zonder_token(methode, pad):
    probleem(requests.request(methode, f"{COMPAT}/{pad}", data=b"[]" if methode == "POST" else None, timeout=30), 401)


def test_lezen_volgens_schema(s):
    r = s.get(f"{COMPAT}/indicator_waarde", timeout=120)
    assert r.status_code == 200 and r.headers.get("api-version")
    for w in r.json()[:200]:
        assert schema_fouten(w, "SwfWaardeTerug") == []
    probleem(s.get(f"{COMPAT}/indicator_waarde/00000000-0000-4000-8000-000000000999", timeout=30), 404, "niet-gevonden")
    probleem(s.get(f"{COMPAT}/indicator_waarde/geen-uuid", timeout=30), 400)
    r = s.get(f"{COMPAT}/indicator/setup", timeout=60)
    if r.status_code == 404:
        probleem(r, 404, "niet-gevonden")  # swf-monitor-definities nog niet gepubliceerd
    else:
        assert r.status_code == 200 and schema_fouten(r.json(), "SwfDefinities") == []


@pytest.fixture(scope="module")
def waarden(s):
    """swf-monitor-waarden geregistreerd zoals use case swf-adapter-fme; alleen op een verse stack."""
    if s.get(f"{API}/datasets/swf-monitor-waarden", timeout=30).status_code == 200:
        pytest.skip("swf-monitor-waarden bestaat al (geladen monitor); schrijvende compat-test overgeslagen")
    ucs = uc.lees_usecases()
    ds = next(d for d in ucs["swf-adapter-fme"]["datasets"] if d["id"] == "swf-monitor-waarden")
    r = s.post(f"{API}/datasets", json=uc.registratie_voor_api(uc.lees_dataset(ucs["swf-adapter-fme"], ds)), timeout=30)
    assert r.status_code == 201, r.text[:500]
    r = requests.get(
        f"{BASIS}/api/data/v1/indicatoren?select=uuid&min_waarde=is.null&max_waarde=is.null&order=uuid&limit=20",
        timeout=30,
    )
    assert r.status_code == 200, r.text[:300]
    for ind in (x["uuid"] for x in r.json()):  # een indicator die op CBS-buurten mag (alleen valideren)
        r = s.post(
            f"{COMPAT}/indicator_waarde/inlezen",
            params={"alleenValideren": "true"},
            data=body(ind),
            headers={"Content-Type": "application/json"},
            timeout=180,
        )
        if r.status_code == 200:
            return ind
    pytest.skip("geen indicator gevonden die op CBS-buurten geleverd mag worden")


def body(ind, waarde=1.5):
    return json.dumps(
        [
            {
                "indicator_id": ind,
                "gebiedstype_id": CBS_BUURTEN,
                "gebieds_id": GEBIED,
                "waarde": waarde,
                "begingeldigheid": "2098-01-01",
                "eindgeldigheid": None,
            }
        ]
    ).encode()


def test_waarden_inlezen_idempotent_en_terug(s, waarden):
    url = f"{COMPAT}/indicator_waarde/inlezen"
    r = s.post(url, data=body(waarden), headers={"Content-Type": "application/json"}, timeout=180)
    assert r.status_code == 200, r.text[:800]
    een = r.json()
    assert schema_fouten(een, "SwfInleesResultaat") == []
    assert een["status"] == "gepubliceerd" and een["versie"] and een["aantallen"]["gepubliceerd"] == 1
    assert r.headers["location"] == f"/api/laden/v1/leveringen/{een['leveringId']}"
    # FME zet niet altijd een Content-Type; dezelfde body: geen nieuwe versie
    r = s.post(url, data=body(waarden), timeout=180)
    assert r.status_code == 200, r.text[:800]
    assert r.json()["versie"] == een["versie"] and r.json()["aantallen"]["ongewijzigd"] is True
    # alleen valideren
    r = s.post(url, params={"alleenValideren": "true"}, data=body(waarden, 2.5), timeout=180)
    assert r.status_code == 200 and r.json()["status"] == "gevalideerd" and r.json()["versie"] is None
    # terug in het oude formaat
    r = s.get(f"{COMPAT}/indicator_waarde/{waarden}", timeout=60)
    assert r.status_code == 200
    assert {
        "indicator_id": waarden,
        "gebiedstype_id": CBS_BUURTEN,
        "gebieds_id": GEBIED,
        "jaar": 2098,
        "waarde": 1.5,
    } in r.json()


def test_waarden_fouten(s, waarden):
    url = f"{COMPAT}/indicator_waarde/inlezen"
    probleem(s.post(url, data=b"{", headers={"Content-Type": "application/json"}, timeout=30), 400, "ongeldig-verzoek")
    probleem(s.post(url, data=b"[]", headers={"Content-Type": "application/json"}, timeout=30), 400, "ongeldig-verzoek")
    fout = json.loads(body(waarden))
    fout[0]["begingeldigheid"] = "0000-01-01"
    r = s.post(url, data=json.dumps(fout).encode(), headers={"Content-Type": "application/json"}, timeout=180)
    probleem(r, 422, "levering-afgekeurd")
    assert "jaar-ongeldig" in {f["code"] for f in r.json()["fouten"]}
