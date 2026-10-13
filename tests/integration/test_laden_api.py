"""
Integratietest laad-API /api/laden/v1 (#228) tegen een draaiende stack met Keycloak.

Echte tokens, geen testmodus in de app. Een machineclient met de realm-rol `beheerder` en de
client-rol `datasets:laden` maak je met deploy/keycloak/machineclient.sh:

    docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh usecase-test beheerder datasets:laden

Omgeving: OMNITWIN_BASE_URL (standaard http://localhost), OMNITWIN_CLIENT_ID en OMNITWIN_CLIENT_SECRET
(die client), optioneel OMNITWIN_TOKEN_URL. Optioneel een tweede client met alleen
`dataset:voorbeeld:laden` (bijv. etl-voorbeeld) in LADEN_BEPERKT_CLIENT_ID/LADEN_BEPERKT_CLIENT_SECRET
voor de 403-tests. Elke run gebruikt eigen dataset-id's; de waarden staan in jaar 2099, zodat ze
de demodata niet raken. Responses worden getoetst aan de schema's in docs/api/laden/openapi.yaml.
"""

import base64
import hashlib
import json
import os
import time
import uuid

import pytest
import requests

from omnitwin import usecases as uc
from omnitwin.laden.registratie import laad_openapi, valideer

pytestmark = pytest.mark.integration

BASIS = uc.basis_url()
API = f"{BASIS}/api/laden/v1"
SPEC = laad_openapi()
RUN = uuid.uuid4().hex[:6]
GEBIED = "BU19000002"
KOP = "gebied_code,gebiedstype,indicator_uuid,jaar,peildatum,scenario,waarde,n,kwaliteit,bron,opmerking"

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
    """Sessie met token; wacht bij 429 (rate-limit van Traefik, LADEN_RATE_LIMIT) volgens Retry-After."""
    return uc.LaadApi(BASIS).s


@pytest.fixture(scope="module")
def indicatoren():
    r = requests.get(
        f"{BASIS}/api/data/v1/indicatoren?select=uuid&min_waarde=is.null&max_waarde=is.null&order=uuid&limit=3",
        timeout=30,
    )
    assert r.status_code == 200, r.text[:300]
    return [x["uuid"] for x in r.json()]


def registratie(ds_id, **laadprofiel):
    return {
        "id": ds_id,
        "beschrijving": {
            "@type": "dcat:Dataset",
            "dct:title": f"Test laad-API {ds_id}",
            "dct:description": "Integratietest (#228).",
            "dct:publisher": "https://identifier.overheid.nl/tooi/id/gemeente/gm1900",
            "dct:accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
        },
        "laadprofiel": {"profiel": "waarnemingen", **laadprofiel},
    }


def csv(regels):
    return ("\n".join([KOP, *regels]) + "\n").encode()


def lever(s, ds, body, mt="text/csv", sleutel=None, **params):
    headers = {"Content-Type": mt}
    if sleutel:
        headers["Idempotency-Key"] = sleutel
    return s.post(
        f"{API}/datasets/{ds}/leveringen",
        data=body,
        headers=headers,
        params={k: str(v).lower() for k, v in params.items()},
        timeout=180,
    )


def waarde(ind, jaar=2099):
    r = requests.get(
        f"{BASIS}/api/data/v1/gebied_data?gebied_id=eq.{GEBIED}&indicator_uuid=eq.{ind}&jaar=eq.{jaar}"
        "&select=waarde,n_status",
        timeout=30,
    )
    assert r.status_code == 200, r.text[:300]
    return r.json()


@pytest.fixture(scope="module")
def dataset(s, indicatoren):
    ds = f"test-laden-{RUN}"
    r = s.post(
        f"{API}/datasets",
        json=registratie(
            ds, minimumN=10, bijOntbrekendeN="bron-onderdrukt", vervangBereik=["indicator_uuid", "gebiedstype"]
        ),
        timeout=30,
    )
    assert r.status_code == 201, r.text[:500]
    assert r.headers["location"] == f"/api/laden/v1/datasets/{ds}"
    assert schema_fouten(r.json(), "Dataset") == []
    return ds


def test_openapi_en_api_version():
    r = requests.get(f"{API}/openapi.json", timeout=30)
    assert r.status_code == 200 and r.json()["info"]["title"] == SPEC["info"]["title"]
    assert r.headers["api-version"] == SPEC["info"]["version"]
    assert r.headers["access-control-allow-origin"] == "*"


def test_zonder_token(dataset):
    probleem(requests.get(f"{API}/datasets", timeout=30), 401)
    probleem(requests.post(f"{API}/datasets/{dataset}/leveringen", data=b"x", timeout=30), 401)
    r = requests.get(f"{API}/datasets", headers={"Accept": "application/ld+json"}, timeout=30)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/ld+json")
    assert schema_fouten(r.json(), "DcatCatalogus") == []
    assert any(d["dct:identifier"] == dataset for d in r.json()["dcat:dataset"])


def test_registratie_dubbel_en_ongeldig(s, dataset):
    probleem(s.post(f"{API}/datasets", json=registratie(dataset), timeout=30), 409, "dataset-bestaat")
    probleem(s.post(f"{API}/datasets", json={"id": "x"}, timeout=30), 422, "registratie-ongeldig")
    probleem(s.post(f"{API}/datasets", data=b"{", headers={"Content-Type": "application/json"}, timeout=30), 400)


def test_leveren_n_drempel_en_publiceren(s, dataset, indicatoren):
    i1, i2 = indicatoren[:2]
    body = csv([f"{GEBIED},,{i1},2099,,,12.5,148,definitief,,", f"{GEBIED},,{i2},2099,,,3,7,,,"])
    r = lever(s, dataset, body, sleutel=f"{dataset}-1", wacht=True)
    assert r.status_code == 201, r.text[:800]
    lv = r.json()
    assert schema_fouten(lv, "Levering") == []
    assert lv["status"] == "gepubliceerd" and lv["versie"] == 1
    assert lv["sha256"] == hashlib.sha256(body).hexdigest()
    assert lv["aantallen"]["gepubliceerd"] == 1 and lv["aantallen"]["onderdrukt"] == 1
    assert waarde(i1) == [{"waarde": 12.5, "n_status": "gemeten"}]
    assert waarde(i2) == [], "waarde onder de n-drempel is gepubliceerd"
    # idempotent: zelfde sleutel en inhoud → dezelfde levering, andere inhoud → 422
    r2 = lever(s, dataset, body, sleutel=f"{dataset}-1", wacht=True)
    assert r2.status_code == 200 and r2.json()["id"] == lv["id"] and r2.json()["versie"] == 1
    probleem(lever(s, dataset, body + b"\n", sleutel=f"{dataset}-1"), 422, "idempotency-key-hergebruikt")
    # zelfde bestand zonder sleutel: geregistreerd, geen nieuwe versie
    r3 = lever(s, dataset, body, wacht=True)
    assert r3.status_code == 201 and r3.json()["versie"] == 1 and r3.json()["aantallen"].get("ongewijzigd")


def test_afkeuring_laat_vorige_versie_staan(s, dataset, indicatoren):
    i1 = indicatoren[0]
    r = lever(s, dataset, csv([f"BU00000000,,{i1},2099,,,1,50,,,", f"{GEBIED},,{i1},,,,1,50,,,"]), wacht=True)
    probleem(r, 422, "levering-afgekeurd")
    codes = {(f["code"], f.get("regel")) for f in r.json()["fouten"]}
    assert codes == {("gebied-onbekend", 1), ("jaar-ongeldig", 2)}
    assert "BU00000000" not in r.text, "brondata in de foutmelding"
    lv = s.get(f"{BASIS}{r.json()['levering']}", timeout=30).json()
    assert lv["status"] == "afgekeurd" and lv["versie"] is None and schema_fouten(lv, "Levering") == []
    assert s.get(f"{API}/datasets/{dataset}", timeout=30).json()["actueleVersie"] == 1
    assert waarde(i1) == [{"waarde": 12.5, "n_status": "gemeten"}]
    # alleen valideren: geldig maar niet gepubliceerd
    r = lever(s, dataset, csv([f"{GEBIED},,{i1},2099,,,99,50,,,"]), wacht=True, alleenValideren=True)
    assert r.status_code == 201 and r.json()["status"] == "gevalideerd" and r.json()["versie"] is None
    assert waarde(i1) == [{"waarde": 12.5, "n_status": "gemeten"}]


def test_asynchroon_vervangbereik_versies_en_bestand(s, dataset, indicatoren):
    i1, i2, i3 = indicatoren
    body = csv([f"{GEBIED},,{i3},2099,,,7,,,,"])  # andere indicator: i1 blijft staan (vervangbereik)
    r = lever(s, dataset, body)
    assert r.status_code == 202 and r.headers["location"].startswith("/api/laden/v1/leveringen/")
    assert r.headers.get("retry-after")
    for _ in range(120):
        lv = s.get(f"{BASIS}{r.headers['location']}", timeout=30).json()
        if lv["status"] not in ("ontvangen", "bezig"):
            break
        time.sleep(1)
    assert lv["status"] == "gepubliceerd" and lv["versie"] == 2, lv
    assert waarde(i1) == [{"waarde": 12.5, "n_status": "gemeten"}]
    assert waarde(i3) == [{"waarde": 7, "n_status": "bron-onderdrukt"}]
    v = s.get(f"{API}/datasets/{dataset}/versies", timeout=30).json()
    assert schema_fouten(v, "VersiePagina") == []
    assert [x["versie"] for x in v["versies"]] == [2, 1] and v["versies"][0]["actueel"]
    assert len(v["versies"][0]["leveringIds"]) == 2  # i1 uit versie 1, i3 uit versie 2
    probleem(s.get(f"{API}/datasets/{dataset}/versies/actueel/bestand", timeout=30), 409, "versie-meerdere-leveringen")
    b = s.get(f"{API}/datasets/{dataset}/versies/1/bestand", timeout=30)
    assert b.status_code == 200 and b.headers["content-type"].startswith("text/csv")
    assert b.headers["content-digest"] == f"sha-256=:{base64.b64encode(hashlib.sha256(b.content).digest()).decode()}:"
    lijst = s.get(f"{API}/datasets/{dataset}/leveringen", params={"status": "afgekeurd"}, timeout=30).json()
    assert schema_fouten(lijst, "LeveringPagina") == [] and {x["status"] for x in lijst["leveringen"]} == {"afgekeurd"}


def test_multipart_met_dcat_en_beschrijving(s, dataset, indicatoren):
    dcat = {"dct:temporal": {"@type": "dct:PeriodOfTime", "dcat:startDate": "2099-01-01"}}
    r = s.post(
        f"{API}/datasets/{dataset}/leveringen",
        params={"wacht": "true"},
        timeout=180,
        files={
            "bestand": ("w.csv", csv([f"{GEBIED},,{indicatoren[2]},2099,,,8,,,,"]), "text/csv"),
            "dcat": ("dcat.jsonld", json.dumps(dcat), "application/ld+json"),
        },
    )
    assert r.status_code == 201, r.text[:500]
    d = s.get(f"{API}/datasets/{dataset}", timeout=30).json()
    assert d["beschrijving"]["dct:temporal"]["dcat:startDate"] == "2099-01-01"
    assert d["beschrijving"]["dct:modified"] and d["beschrijving"]["dcat:distribution"]
    assert d["laatsteLevering"]["id"] == r.json()["id"]


def test_fouten_bij_het_leveren(s, dataset):
    probleem(lever(s, dataset, b"x", mt="text/plain"), 415, "mediatype-past-niet")
    probleem(lever(s, dataset, b"x", modus="aanvullen"), 400)
    r = s.post(
        f"{API}/datasets/{dataset}/leveringen",
        data=b"abc",
        timeout=30,
        headers={"Content-Type": "text/csv", "Content-Digest": "sha-256=:AAAA:"},
    )
    probleem(r, 400)
    probleem(lever(s, "bestaat-niet-xyz", b"x"), 404)
    probleem(s.get(f"{API}/leveringen/{uuid.uuid4()}", timeout=30), 404)
    probleem(s.get(f"{API}/datasets", params={"paginaGrootte": 1000}, timeout=30), 400)


def test_wijzigen_patch_en_put(s, dataset):
    r = s.patch(
        f"{API}/datasets/{dataset}",
        data=json.dumps({"beschrijving": {"dct:description": "Gewijzigd."}}),
        headers={"Content-Type": "application/merge-patch+json"},
        timeout=30,
    )
    assert r.status_code == 200 and r.json()["beschrijving"]["dct:description"] == "Gewijzigd."
    probleem(s.patch(f"{API}/datasets/{dataset}", json={}, timeout=30), 415)
    reg = registratie(dataset)
    reg["laadprofiel"] = {"profiel": "kaartlaag", "doel": {"featureTabel": "t", "sleutelveld": "id"}}
    probleem(s.put(f"{API}/datasets/{dataset}", json=reg, timeout=30), 409, "profiel-vast")


def test_voorrang_laatst_gepubliceerd_bij_gelijke_voorrang(s, dataset, indicatoren):
    """Twee datasets op dezelfde sleutel zonder dct:modified (bronpeildatum = ontvangst): laatst aangeleverd wint."""
    i1 = indicatoren[0]
    andere = f"test-laden-b-{RUN}"
    assert s.post(f"{API}/datasets", json=registratie(andere, minimumN=0), timeout=30).status_code == 201
    assert lever(s, andere, csv([f"{GEBIED},,{i1},2099,,,99,5,,,"]), wacht=True).status_code == 201
    assert waarde(i1) == [{"waarde": 99, "n_status": "gemeten"}]
    assert lever(s, dataset, csv([f"{GEBIED},,{i1},2099,,,13,50,,,"]), wacht=True).status_code == 201
    assert waarde(i1) == [{"waarde": 13, "n_status": "gemeten"}]


def _lever_met_peildatum(s, ds, regel, peildatum=None):
    files = {"bestand": ("w.csv", csv([regel]), "text/csv")}
    if peildatum:
        files["dcat"] = ("dcat.jsonld", json.dumps({"dct:modified": peildatum}), "application/ld+json")
    return s.post(f"{API}/datasets/{ds}/leveringen", params={"wacht": "true"}, files=files, timeout=180)


def _stand(ind, jaar):
    r = requests.get(
        f"{BASIS}/api/data/v1/gebied_data?gebied_id=eq.{GEBIED}&indicator_uuid=eq.{ind}&jaar=eq.{jaar}"
        "&select=waarde,andere_bronnen",
        timeout=30,
    )
    assert r.status_code == 200, r.text[:300]
    assert len(r.json()) == 1, r.json()
    x = r.json()[0]
    return x["waarde"], [(a["dataset"], a["waarde"], a["bronpeildatum"]) for a in (x["andere_bronnen"] or [])]


def test_voorrang_nieuwste_bronpeildatum_dan_laatst_aangeleverd(s, indicatoren):
    """A6 (#222): bij overlap wint de nieuwste bronpeildatum (dct:modified in dcat.jsonld), bij gelijke
    bronpeildatum de laatst aangeleverde levering; de andere waarde blijft zichtbaar als andere_bronnen."""
    i1, jaar = (
        indicatoren[0],
        2050 + int(RUN, 16) % 40,
    )  # eigen jaar per run: een herhaalde run op dezelfde stack botst niet
    a, b, c = f"test-voorrang-a-{RUN}", f"test-voorrang-b-{RUN}", f"test-voorrang-c-{RUN}"
    for ds in (a, b):
        assert s.post(f"{API}/datasets", json=registratie(ds, minimumN=0), timeout=30).status_code == 201
    intern = registratie(c, minimumN=0)
    intern["beschrijving"]["dct:accessRights"] = (
        "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC"
    )
    assert s.post(f"{API}/datasets", json=intern, timeout=30).status_code == 201
    regel = f"{GEBIED},,{i1},{jaar},,,{{}},50,,,"

    r = _lever_met_peildatum(s, a, regel.format(10), "2026-06-01")
    assert r.status_code == 201, r.text[:500]
    assert r.json()["aantallen"]["bronpeildatum"] == "2026-06-01"
    assert r.json()["aantallen"]["bronpeildatumUit"] == "dct:modified"
    # later aangeleverd, maar een oudere stand van de bron: a blijft staan, b is de tweede bron
    r = _lever_met_peildatum(s, b, regel.format(20), "2025-01-01")
    assert r.status_code == 201 and r.json()["aantallen"].get("nietZichtbaarDoorVoorrang") == 1, r.text[:500]
    assert _stand(i1, jaar) == (10, [(b, 20, "2025-01-01")])
    # gelijke bronpeildatum: de laatst aangeleverde levering wint
    assert _lever_met_peildatum(s, b, regel.format(30), "2026-06-01").status_code == 201
    assert _stand(i1, jaar) == (30, [(a, 10, "2026-06-01")])
    # een niet-openbare dataset die verliest, staat niet in andere_bronnen van een openbare winnaar
    assert _lever_met_peildatum(s, c, regel.format(99), "2000-01-01").status_code == 201
    assert _stand(i1, jaar) == (30, [(a, 10, "2026-06-01")])
    # zonder dcat: de datum van ontvangst (vandaag) is nieuwer dan 2026-06-01
    r = _lever_met_peildatum(s, a, regel.format(40))
    assert r.status_code == 201 and r.json()["aantallen"]["bronpeildatumUit"] == "ontvangst", r.text[:500]
    assert _stand(i1, jaar) == (40, [(b, 30, "2026-06-01")])
    # de verliezende waarde blijft in de eigen dataset: de versie van b telt hem nog
    v = s.get(f"{API}/datasets/{b}/versies", timeout=30).json()["versies"][0]
    assert v["actueel"] and v["aantalRegels"] == 1, v
    # een bronpeildatum in de toekomst zou altijd winnen: afgekeurd
    probleem(_lever_met_peildatum(s, b, regel.format(50), "2999-01-01"), 422, "levering-afgekeurd")
    assert _stand(i1, jaar)[0] == 40


def test_lijst_en_rechten(s, dataset):
    r = s.get(f"{API}/datasets", params={"profiel": "waarnemingen", "paginaGrootte": 100}, timeout=30)
    assert r.status_code == 200 and schema_fouten(r.json(), "DatasetPagina") == []
    assert dataset in {d["id"] for d in r.json()["datasets"]}
    cid, geheim = os.environ.get("LADEN_BEPERKT_CLIENT_ID"), os.environ.get("LADEN_BEPERKT_CLIENT_SECRET")
    if not (cid and geheim):
        pytest.skip("geen beperkte client (LADEN_BEPERKT_CLIENT_ID/SECRET)")
    os.environ["OMNITWIN_CLIENT_ID"], os.environ["OMNITWIN_CLIENT_SECRET"], oud = (
        cid,
        geheim,
        (os.environ["OMNITWIN_CLIENT_ID"], os.environ["OMNITWIN_CLIENT_SECRET"]),
    )
    try:
        beperkt = {"Authorization": f"Bearer {uc.token(BASIS)}"}
    finally:
        os.environ["OMNITWIN_CLIENT_ID"], os.environ["OMNITWIN_CLIENT_SECRET"] = oud
    probleem(requests.get(f"{API}/datasets/{dataset}", headers=beperkt, timeout=30), 403, "geen-toegang")
    probleem(requests.post(f"{API}/datasets", json=registratie("test-nee"), headers=beperkt, timeout=30), 403)
    probleem(requests.post(f"{API}/datasets/{dataset}/leveringen", data=b"x", headers=beperkt, timeout=30), 403)
    lijst = requests.get(f"{API}/datasets", headers=beperkt, timeout=30).json()
    assert dataset not in {d["id"] for d in lijst["datasets"]}


def _gpkg(tmp_path, naam, features, crs=4326):
    fiona = pytest.importorskip("fiona")
    from fiona.crs import CRS

    pad = tmp_path / f"{naam}.gpkg"
    schema = {"geometry": features[0]["geometry"]["type"], "properties": {k: "str" for k in features[0]["properties"]}}
    with fiona.open(pad, "w", driver="GPKG", layer=naam, crs=CRS.from_epsg(crs), schema=schema) as dst:
        dst.writerecords(features)
    return pad.read_bytes()


def _vlak(x, y, d=0.001):
    return {"type": "Polygon", "coordinates": [[(x, y), (x + d, y), (x + d, y + d), (x, y + d), (x, y)]]}


def test_gebiedsindeling_en_kaartlaag(s, tmp_path):
    ds = f"test-gebieden-{RUN}"
    reg = registratie(ds)
    reg["laadprofiel"] = {
        "profiel": "gebiedsindeling",
        "doel": {
            "gebiedstypeId": "29fc9f28-89d9-488b-bf68-2ed176187b21",
            "featureTabel": "gebieden",
            "sleutelveld": "code",
            "labelveld": "naam",
            "codePrefix": f"T{RUN}-",
        },
    }
    assert s.post(f"{API}/datasets", json=reg, timeout=30).status_code == 201
    body = _gpkg(
        tmp_path,
        "gebieden",
        [
            {"geometry": _vlak(5.53, 53.03), "properties": {"code": "1", "naam": "Een"}},
            {"geometry": _vlak(5.54, 53.03), "properties": {"code": "2", "naam": "Twee"}},
        ],
    )
    r = lever(s, ds, body, mt="application/geopackage+sqlite3", wacht=True)
    assert r.status_code == 201, r.text[:800]
    assert r.json()["aantallen"]["gepubliceerd"] == 2
    g = requests.get(f"{BASIS}/api/data/v1/gebieden?id=eq.T{RUN}-1&select=id,naam,gebiedstype_id", timeout=30).json()
    assert g == [{"id": f"T{RUN}-1", "naam": "Een", "gebiedstype_id": "29fc9f28-89d9-488b-bf68-2ed176187b21"}]
    # vervangen: gebied 2 verdwijnt (zonder waarden: verwijderd)
    body = _gpkg(tmp_path, "gebieden", [{"geometry": _vlak(5.53, 53.03), "properties": {"code": "1", "naam": "Een"}}])
    assert lever(s, ds, body, mt="application/geopackage+sqlite3", wacht=True).json()["aantallen"]["verwijderd"] == 1
    # ongeldig CRS-verhaal: geen polygoon
    slecht = _gpkg(
        tmp_path,
        "gebieden",
        [{"geometry": {"type": "Point", "coordinates": (5.5, 53.0)}, "properties": {"code": "3", "naam": "Drie"}}],
    )
    probleem(lever(s, ds, slecht, mt="application/geopackage+sqlite3", wacht=True), 422, "levering-afgekeurd")

    kl = f"test-kaartlaag-{RUN}"
    reg = registratie(kl)
    reg["laadprofiel"] = {"profiel": "kaartlaag", "doel": {"featureTabel": "punten", "sleutelveld": "id"}}
    assert s.post(f"{API}/datasets", json=reg, timeout=30).status_code == 201
    body = _gpkg(
        tmp_path,
        "punten",
        [{"geometry": {"type": "Point", "coordinates": (5.5, 53.0)}, "properties": {"id": "a", "klasse": "x"}}],
    )
    r = lever(s, kl, body, mt="application/geopackage+sqlite3", wacht=True)
    assert r.status_code == 201, r.text[:800]
    lagen = requests.get(
        f"{BASIS}/api/data/v1/externe_kaartlagen?url=eq.laden/{kl}.gpkg&select=id,actief", timeout=30
    ).json()
    assert len(lagen) == 1 and lagen[0]["actief"] is True
    f = requests.get(f"{BASIS}/api/externe-lagen/{lagen[0]['id']}/features", timeout=30)
    assert f.status_code == 200 and len(f.json()["features"]) == 1
