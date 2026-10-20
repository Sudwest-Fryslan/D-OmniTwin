"""Indicatorpaneel, CSV-export en eigen voorkeuren (#258). Zonder database of netwerk."""

import csv
import io
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.services import gebruikersvoorkeuren as gv
from omnitwin.services import indicatorpaneel_service as ip

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


# ── Opmaak ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "waarde, verwacht",
    [
        (None, ""),
        (0, "0"),
        (12.5, "12,5"),
        (1234567.25, "1234567,25"),
        (-0.75, "-0,75"),
        (1 / 3, "0,333333"),
        (100.0, "100"),
        (1e-7, "0"),
        (2.5e9, "2500000000"),
    ],
)
def test_getal_nl(waarde, verwacht):
    assert ip.getal_nl(waarde) == verwacht


def test_getal_nl_decimal_uit_database():
    from decimal import Decimal

    assert ip.getal_nl(Decimal("12.500")) == "12,5"
    assert ip.getal_nl(Decimal("1E+2")) == "100"


@pytest.mark.parametrize(
    "tekst, verwacht",
    [
        ("Bolsward", "Bolsward"),
        ("=SOM(A1)", "'=SOM(A1)"),
        ("+31", "'+31"),
        ("-x", "'-x"),
        ("@a", "'@a"),
        (None, ""),
    ],
)
def test_veilige_tekst_tegen_csv_injectie(tekst, verwacht):
    assert ip.veilige_tekst(tekst) == verwacht


def test_lees_gebied_ids():
    assert ip.lees_gebied_ids(None) == []
    assert ip.lees_gebied_ids(" BU19000002, BU19000001,BU19000002,,") == ["BU19000002", "BU19000001"]
    with pytest.raises(GebruikersFout):
        ip.lees_gebied_ids("BU1;DROP TABLE")
    with pytest.raises(GebruikersFout):
        ip.lees_gebied_ids(",".join(f"BU{i}" for i in range(ip.MAX_GEBIEDEN + 1)))


def test_licentie_en_dcat_tekst():
    assert ip.licentie_naam("http://creativecommons.org/licenses/by/4.0/") == "CC BY 4.0"
    assert ip.licentie_naam("https://example.org/eigen") == "https://example.org/eigen"
    assert ip._tekst({"foaf:name": "CBS"}) == "CBS"
    assert ip._tekst([{"@id": "https://www.cbs.nl/"}]) == "https://www.cbs.nl/"
    assert ip._tekst("  ") is None
    assert ip.uitgever_naam("https://www.rivm.nl/") == "rivm.nl"
    assert ip.uitgever_naam({"foaf:name": "CBS"}) == "CBS"


def _paneel():
    return {
        "indicator": {"naam": "Hitte-eiland", "code": "UHI/1", "eenheid": "°C"},
        "bronnen": [
            {
                "sleutel": "dataset:hitte",
                "titel": "Hittekaart",
                "uitgever": "RIVM",
                "licentie": "CC BY 4.0",
                "bron": None,
                "jaargangen": [2022],
            }
        ],
        "gebieden": [
            {
                "id": "BU19000002",
                "naam": "Bolsward-Zuidoost",
                "jaar": 2022,
                "waarde": 1.25,
                "status": "gemeten",
                "bronSleutel": "dataset:hitte",
            },
            {
                "id": "BU19000001",
                "naam": "=Bolsward; centrum",
                "jaar": 2022,
                "waarde": None,
                "status": "onderdrukt",
                "bronSleutel": "dataset:hitte",
            },
            {
                "id": "BU19000003",
                "naam": "Zonder",
                "jaar": None,
                "waarde": None,
                "status": "geen-data",
                "bronSleutel": None,
            },
        ],
        "gemeentegemiddelden": [
            {
                "gemeenteCode": "1900",
                "gemeenteNaam": "Súdwest-Fryslân",
                "jaar": 2022,
                "waarde": 0.8,
                "aantalGebieden": 140,
            }
        ],
        "drempel": 10,
    }


def test_csv_formaat_bom_puntkomma_decimale_komma():
    tekst = ip.maak_csv(_paneel())
    assert tekst.startswith("﻿")
    assert tekst.encode("utf-8")[:3] == b"\xef\xbb\xbf"
    rijen = list(csv.reader(io.StringIO(tekst[1:]), delimiter=";"))
    assert rijen[0] == ["gebied-code", "gebied-naam", "indicator", "jaar", "waarde", "eenheid", "bron", "status"]
    assert rijen[1] == [
        "BU19000002",
        "Bolsward-Zuidoost",
        "Hitte-eiland",
        "2022",
        "1,25",
        "°C",
        "Hittekaart (RIVM), CC BY 4.0",
        "gemeten",
    ]
    # onderdrukt: waarde leeg, met status; tekst met ; tussen aanhalingstekens, formule geneutraliseerd
    assert rijen[2][1] == "'=Bolsward; centrum" and rijen[2][4] == "" and rijen[2][7] == "onderdrukt"
    assert rijen[3][3:5] == ["", ""] and rijen[3][7] == "geen-data"
    assert rijen[4][:2] == ["1900", "Gemiddelde Súdwest-Fryslân (140 gebieden)"]
    assert rijen[4][4] == "0,8" and rijen[4][7] == "gemeentegemiddelde"
    assert "\r\n" in tekst


def test_csv_bestandsnaam():
    assert ip.csv_bestandsnaam(_paneel(), "2026-10-04") == "indicator-UHI-1-2026-10-04.csv"


def test_gemiddelde():
    assert ip.gemiddelde([]) is None
    assert ip.gemiddelde([1.0, 2.0, 6.0]) == 3.0


# ── Eigen voorkeuren ─────────────────────────────────────────────────────────


def test_eigenaar_alleen_sub_of_lokaal_id():
    assert gv.eigenaar_van({"type": "oidc", "onderwerp": "abc-123", "username": "gebruiker"}) == "abc-123"
    assert gv.eigenaar_van({"type": "bearer", "onderwerp": "s9", "user_id": "s9"}) == "s9"
    assert gv.eigenaar_van({"type": "session", "user_id": "4f1c", "username": "admin"}) == "lokaal:4f1c"
    assert gv.eigenaar_van({"type": "api_key", "user_id": "system_admin_key"}) is None
    assert gv.eigenaar_van(None) is None


def test_kaartpositie_grenzen():
    p = gv.controleer_positie({"longitude": 5.53, "latitude": 53.03, "zoom": 13.2, "pitch": 0, "bearing": 10})
    assert p == {"longitude": 5.53, "latitude": 53.03, "zoom": 13.2, "pitch": 0.0, "bearing": 10.0}
    for fout in (
        {"longitude": 200, "latitude": 53, "zoom": 10},
        {"latitude": 53, "zoom": 10},
        {"longitude": 5, "latitude": 53, "zoom": float("nan")},
        {"longitude": "x", "latitude": 1, "zoom": 1},
    ):
        with pytest.raises(GebruikersFout):
            gv.controleer_positie(fout)


def test_favoriet_controle():
    assert gv.controleer_favoriet("  Kernen ", ["BU1", "BU2", "BU1"]) == ("Kernen", ["BU1", "BU2"])
    for naam, ids in (("", ["BU1"]), ("x" * 81, ["BU1"]), ("ok", []), ("ok", ["BU 1"])):
        with pytest.raises(GebruikersFout):
            gv.controleer_favoriet(naam, ids)


class _Leeg:
    """Database die niet aangeroepen mag worden."""

    def execute(self, *a, **k):  # pragma: no cover - mag niet gebeuren
        raise AssertionError("geen database zonder login")


@pytest.fixture
def mijn_app(monkeypatch):
    from omnitwin.routers import auth, mijn

    def niemand(request, db):
        raise HTTPException(status_code=401, detail="Niet geautoriseerd.")

    monkeypatch.setattr(auth, "huidige_gebruiker", niemand)
    app = FastAPI()
    app.include_router(mijn.router)
    app.dependency_overrides[get_db] = lambda: _Leeg()
    return TestClient(app)


@pytest.mark.parametrize(
    "methode, pad, body",
    [
        ("get", "/api/mijn/favorieten", None),
        ("post", "/api/mijn/favorieten", {"naam": "x", "gebiedIds": ["BU1"]}),
        ("delete", "/api/mijn/favorieten/7b1c6f2e-1d1a-4c1e-9c43-6a4b7a0f3c11", None),
        ("get", "/api/mijn/instellingen", None),
        ("put", "/api/mijn/instellingen", {"kaartpositie": {"longitude": 5, "latitude": 53, "zoom": 9}}),
    ],
)
def test_mijn_zonder_login_401(mijn_app, methode, pad, body):
    r = getattr(mijn_app, methode)(pad, **({"json": body} if body else {}))
    assert r.status_code == 401, r.text


def test_mijn_script_met_key_401(monkeypatch, mijn_app):
    from omnitwin.routers import auth

    monkeypatch.setattr(
        auth,
        "huidige_gebruiker",
        lambda request, db: {"type": "api_key", "user_id": "system_admin_key", "is_admin": True},
    )
    assert mijn_app.get("/api/mijn/favorieten").status_code == 401


# ── Inbouw ───────────────────────────────────────────────────────────────────


def test_routes_in_de_app():
    from omnitwin.routers import indicatorpaneel, mijn

    paden = {r.path for r in indicatorpaneel.router.routes} | {r.path for r in mijn.router.routes}
    assert {
        "/api/gebiedsmonitor/indicatorpaneel",
        "/api/gebiedsmonitor/indicatorpaneel.csv",
        "/api/mijn/favorieten",
        "/api/mijn/favorieten/{favoriet_id}",
        "/api/mijn/instellingen",
    } <= paden
    main = (ROOT / "src/omnitwin/main.py").read_text(encoding="utf-8")
    assert "app.include_router(indicatorpaneel.router)" in main and "app.include_router(mijn.router)" in main


def test_mijn_niet_open_bij_dichte_viewer():
    from omnitwin import viewer_toegang

    assert not viewer_toegang.is_open_pad("/api/mijn/favorieten")
    assert not viewer_toegang.is_open_pad("/api/gebiedsmonitor/indicatorpaneel.csv")


def test_migratie_alleen_sub_geen_persoonsgegevens():
    sql = (ROOT / "db/migraties/V035__gebruikersvoorkeuren.sql").read_text(encoding="utf-8").lower()
    kolommen = sql.split("create table")[1:]
    for blok in kolommen:
        for verboden in ("email", "e_mail", "gebruikersnaam", "username", "naam_gebruiker"):
            assert verboden not in blok.split(");")[0], verboden
    assert "on delete cascade" in sql
    # niet via PostgREST
    rollen = (ROOT / "db/migraties/R__api_rollen.sql").read_text(encoding="utf-8")
    assert "gebruiker_favorieten" not in rollen and "gebruiker_voorkeuren" not in rollen


def test_viewer_laadt_paneel_en_favorieten():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    for nodig in (
        'id="rechter-dock"',
        'id="dock-panel-kompas"',
        'id="ip-grafiek"',
        'id="ip-csv"',
        'id="mijn-favorieten"',
        'name="omnitwin-ingelogd"',
        "/static/js/mijn.js",
    ):
        assert nodig in html, nodig


# ── Paneel met een nepdatabase: onderdrukking en gemiddelde ─────────────────


class _Resultaat:
    def __init__(self, rijen):
        self.rijen = rijen

    def mappings(self):
        return self

    def first(self):
        return self.rijen[0] if self.rijen else None

    def scalar(self):
        return self.rijen[0] if self.rijen else None

    def __iter__(self):
        return iter(self.rijen)


class _NepDb:
    """Antwoordt op de vragen van IndicatorpaneelService naar de tekst van de SQL."""

    def __init__(self):
        self.vragen = []

    def execute(self, sql, params=None):
        q = str(sql)
        self.vragen.append((q, params))
        if "FROM indicatoren WHERE uuid" in q:
            return _Resultaat(
                [
                    {
                        "uuid": "u1",
                        "naam": "Hitte",
                        "code": "UHI",
                        "omschrijving": "Uitleg",
                        "ontologische_beschrijving": None,
                        "eenheid": "°C",
                        "score_type": "-/-",
                        "bron": "RIVM",
                    }
                ]
            )
        if "array_agg(DISTINCT gd.jaar" in q:
            return _Resultaat(
                [
                    {
                        "dataset_id": "hitte",
                        "beschrijving": {
                            "dct:title": "Hittekaart",
                            "dct:publisher": "https://www.rivm.nl/",
                            "dct:license": "http://creativecommons.org/publicdomain/zero/1.0/",
                        },
                        "bron": None,
                        "jaren": [2022],
                    }
                ]
            )
        if "LEFT JOIN LATERAL" in q:
            return _Resultaat(
                [
                    {
                        "id": "BU2",
                        "naam": "Twee",
                        "gemeente_code": "1900",
                        "gebiedstype_id": "gt",
                        "is_waterbuurt": False,
                        "waarde": 1.5,
                        "jaar": 2022,
                        "n": 40,
                        "bron": None,
                        "levering_id": "lv1",
                    },
                    {
                        "id": "BU1",
                        "naam": "Een",
                        "gemeente_code": "1900",
                        "gebiedstype_id": "gt",
                        "is_waterbuurt": False,
                        "waarde": 9.9,
                        "jaar": 2022,
                        "n": 4,
                        "bron": None,
                        "levering_id": "lv1",
                    },
                    {
                        "id": "BU3",
                        "naam": "Drie",
                        "gemeente_code": "1900",
                        "gebiedstype_id": "gt",
                        "is_waterbuurt": False,
                        "waarde": None,
                        "jaar": None,
                        "n": None,
                        "bron": None,
                        "levering_id": None,
                    },
                ]
            )
        if "FROM laden.leveringen" in q:
            return _Resultaat([("lv1", "hitte")])
        if "FROM gemeenten" in q:
            return _Resultaat([("1900", "Súdwest-Fryslân")])
        raise AssertionError(q)


def test_paneel_onderdrukt_en_gemiddelde(monkeypatch):
    from omnitwin.services import percentielklasse as pk

    gevraagd = {}

    def referentie(db, gt, gemeenten, inds, jaar=None, drempel=10):
        gevraagd.update(gt=gt, gemeenten=list(gemeenten), jaar=jaar, drempel=drempel)
        return {("1900", "u1"): [1.0, 2.0, 3.0]}

    monkeypatch.setattr(pk, "referentie_waarden", referentie)
    paneel = ip.IndicatorpaneelService(_NepDb()).paneel("u1", ["BU1", "BU2", "BU3"])
    g = {x["id"]: x for x in paneel["gebieden"]}
    assert [x["id"] for x in paneel["gebieden"]] == ["BU1", "BU2", "BU3"]  # volgorde van de selectie
    assert g["BU2"]["waarde"] == 1.5 and g["BU2"]["status"] == "gemeten" and g["BU2"]["bronSleutel"] == "dataset:hitte"
    assert g["BU1"]["waarde"] is None and g["BU1"]["status"] == "onderdrukt"  # n = 4 < 10
    assert g["BU3"]["status"] == "geen-data"
    assert paneel["bronnen"][0]["uitgever"] == "rivm.nl"
    assert paneel["bronnen"][0]["licentie"] == "CC0 1.0" and paneel["bronnen"][0]["jaargangen"] == [2022]
    gm = paneel["gemeentegemiddelden"]
    assert gm == [
        {
            "gemeenteCode": "1900",
            "gemeenteNaam": "Súdwest-Fryslân",
            "gebiedstypeId": "gt",
            "jaar": 2022,
            "waarde": 2.0,
            "aantalGebieden": 3,
        }
    ]
    assert gevraagd == {"gt": "gt", "gemeenten": ["1900"], "jaar": 2022, "drempel": 10}
    # De onderdrukte waarde staat ook niet in de CSV
    assert "9,9" not in ip.maak_csv(paneel)
