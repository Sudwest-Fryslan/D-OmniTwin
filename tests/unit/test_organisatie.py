"""De eigen organisatie als instellingsdata (#231, ADR 0007).

- de organisatie komt uit de tabel ``organisatie`` (service + GET /api/organisatie);
- rapporten vallen zonder gemeentecode terug op die van de organisatie, niet op een vaste code;
- de footer rendert de logo's uit de instelling;
- /api/kompas/standaard/hierarchie gebruikt de standaardvlag, geen vaste ID;
- geen vaste gemeentecode '1900' in de runtimecode (kleine allowlist).
"""

import inspect
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.exc import ProgrammingError

from omnitwin.database import get_db
from omnitwin.services import organisatie as org_service

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]

SWF = {
    "code": "swf",
    "naam": "Gemeente Súdwest-Fryslân",
    "korte_naam": "SWF",
    "oin": None,
    "gemeente_codes": ["1900"],
    "benchmark_provincie": "Fryslân",
    "contact_email": "geo-groep@sudwestfryslan.nl",
    "thema": "swf",
    "logos": [
        {"pad": "/static/images/SWF-logo.png", "naam": "Gemeente Súdwest-Fryslân", "rol": "eigen"},
        {"pad": "/static/images/Logo_Tytsjerksteradiel.png", "naam": "Gemeente Tytsjerksteradiel", "rol": "partner"},
        {"pad": "/static/images/LOGO-GEMEENTE-LEEUWARDEN.png", "naam": "Gemeente Leeuwarden", "rol": "partner"},
        {"pad": "/static/images/DF-LOGO-1-1000x1000-TBG.png", "naam": "Datafryslân", "rol": "partner"},
    ],
}


class _Rij:
    def __init__(self, d):
        self._mapping = d


class _NepDb:
    """Minimale Session: geeft één rij (of geen) terug, of gooit een databasefout."""

    def __init__(self, rij=None, fout=None):
        self.rij, self.fout, self.teruggedraaid = rij, fout, False

    def execute(self, *_a, **_k):
        if self.fout:
            raise self.fout
        return self

    def fetchone(self):
        return _Rij(self.rij) if self.rij is not None else None

    def rollback(self):
        self.teruggedraaid = True


# ── service ─────────────────────────────────────────────────────────────────


def test_lees_organisatie_geeft_instelling_en_standaardgemeente():
    org = org_service.lees_organisatie(_NepDb(SWF))
    assert org["naam"] == "Gemeente Súdwest-Fryslân"
    assert org["gemeente_codes"] == ["1900"]
    assert org["standaard_gemeente_code"] == "1900"
    assert [l["pad"] for l in org["logos"]] == [l["pad"] for l in SWF["logos"]]
    assert org_service.eigen_gemeente_code(_NepDb(SWF)) == "1900"


def test_andere_organisatie_andere_standaardgemeente():
    leeuwarden = dict(SWF, code="lwd", naam="Gemeente Leeuwarden", gemeente_codes=["0080"], logos=[])
    assert org_service.eigen_gemeente_code(_NepDb(leeuwarden)) == "0080"


def test_geen_organisatie_of_geen_tabel_geeft_none():
    assert org_service.lees_organisatie(_NepDb(None)) is None
    assert org_service.eigen_gemeente_code(_NepDb(None)) is None
    db = _NepDb(fout=ProgrammingError("SELECT", {}, Exception("relation organisatie does not exist")))
    assert org_service.lees_organisatie(db) is None
    assert db.teruggedraaid


def test_logos_zonder_pad_worden_overgeslagen():
    org = org_service.lees_organisatie(_NepDb(dict(SWF, logos=[{"naam": "zonder pad"}, "geen dict"])))
    assert org["logos"] == []
    org = org_service.lees_organisatie(_NepDb(dict(SWF, gemeente_codes=[])))
    assert org["standaard_gemeente_code"] is None


# ── thema (huisstijl) ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "invoer,verwacht",
    [
        ("swf", "swf"),
        ("d-omnitwin", "d-omnitwin"),
        ("gemeente-0080", "gemeente-0080"),
        (None, "d-omnitwin"),
        ("", "d-omnitwin"),
        ("../geheim", "d-omnitwin"),
        ("SWF", "d-omnitwin"),
        ("swf.css", "d-omnitwin"),
        ("a/b", "d-omnitwin"),
        ("x" + chr(10), "d-omnitwin"),
    ],
)
def test_veilig_thema(invoer, verwacht):
    assert org_service.veilig_thema(invoer) == verwacht


def test_thema_css_alleen_als_bestand_bestaat(tmp_path):
    (tmp_path / "swf.css").write_text(":root{}", encoding="utf-8")
    assert org_service.thema_css({"thema": "swf"}, tmp_path) == "/static/css/themes/swf.css"
    assert org_service.thema_css({"thema": "lwd"}, tmp_path) is None
    assert org_service.thema_css({"thema": "../swf"}, tmp_path) is None  # valt terug op d-omnitwin, bestaat niet
    (tmp_path / "d-omnitwin.css").write_text(":root{}", encoding="utf-8")
    assert org_service.thema_css(None, tmp_path) == "/static/css/themes/d-omnitwin.css"
    assert org_service.thema_css({"thema": "../swf"}, tmp_path) == "/static/css/themes/d-omnitwin.css"


def test_template_laadt_themabestand_na_basis_css():
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    html = env.get_template("index.html").render(
        request=None, organisatie=None, app_version="t", thema_css="/static/css/themes/swf.css"
    )
    assert html.index('href="/static/css/styles.css"') < html.index('href="/static/css/themes/swf.css"')
    zonder = env.get_template("index.html").render(request=None, organisatie=None, app_version="t", thema_css=None)
    assert "/static/css/themes/" not in zonder


# ── GET /api/organisatie ────────────────────────────────────────────────────


def _client(router, db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_endpoint_organisatie():
    from omnitwin.routers import organisatie

    r = _client(organisatie.router, _NepDb(SWF)).get("/api/organisatie")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "swf"
    assert body["standaard_gemeente_code"] == "1900"
    assert body["contact_email"] == "geo-groep@sudwestfryslan.nl"
    assert body["thema"] == "swf"
    assert len(body["logos"]) == 4

    assert _client(organisatie.router, _NepDb(None)).get("/api/organisatie").status_code == 404


# ── rapporten: geen vaste gemeentecode ──────────────────────────────────────


def test_rapport_standaardgemeente_komt_uit_organisatie():
    from omnitwin.routers.report import MultiGebiedRequest, ThemaAnalyseRequest
    from omnitwin.services.report_service import ReportDataService

    assert MultiGebiedRequest(gebied_ids=["x"]).gemeente_code is None
    assert ThemaAnalyseRequest(gebied_ids=["x"]).gemeente_code is None
    for naam in (
        "generate_multi_gebied_payload",
        "generate_multi_gebied_geojson",
        "generate_thema_analyse_payload",
        "generate_thema_analyse_geojson",
        "generate_deelgebied_payload",
    ):
        param = inspect.signature(getattr(ReportDataService, naam)).parameters["gemeente_code"]
        assert param.default is None, naam


def test_rapport_vult_gemeente_uit_organisatie(monkeypatch):
    """Zonder gemeente_code gebruikt het multi-gebiedsrapport de gemeente van de organisatie."""
    from omnitwin.services import report_service

    gezien = {}

    def nep_referentie_params(gebiedstype_id, gemeente_code, **_k):
        gezien["gemeente_code"] = gemeente_code
        raise RuntimeError("stop")  # alleen de referentie is hier van belang

    class Db:
        def execute(self, sql, params=None):
            q = str(sql)
            if "FROM public.organisatie" in q:
                return _NepDb(dict(SWF, gemeente_codes=["0080"]))
            if "gebiedstype_id" in q and "LIMIT 1" in q:
                return _NepDb({"gebiedstype_id": "t"})
            return [_Rij({"id": "BU1"})]

    monkeypatch.setattr(report_service, "referentie_params", nep_referentie_params)
    with pytest.raises(RuntimeError, match="stop"):
        report_service.ReportDataService(Db()).generate_multi_gebied_payload(["BU1"])
    assert gezien["gemeente_code"] == "0080"


class _Telling:
    """Resultaat van de telling van de referentiegroep (scalar)."""

    def __init__(self, n):
        self.n = n

    def scalar(self):
        return self.n


@pytest.mark.parametrize(
    "methode", ["generate_multi_gebied_payload", "generate_thema_analyse_payload", "generate_deelgebied_payload"]
)
@pytest.mark.parametrize("provincie", ["Fryslân", "Groningen", None])
def test_referentie_provincie_volgt_instelling(monkeypatch, methode, provincie):
    """#324: referentie 'fryslan' filtert op organisatie.benchmark_provincie, niet op alle gebieden."""
    from omnitwin.services import report_service

    gezien = {}

    def nep_referentie_params(gebiedstype_id, gemeente_code, **k):
        gezien.update(gemeente_code=gemeente_code, provincie=k.get("provincie"))
        raise RuntimeError("stop")

    class Db:
        def execute(self, sql, params=None):
            q = str(sql)
            if "FROM public.organisatie" in q:
                return _NepDb(dict(SWF, benchmark_provincie=provincie))
            if "SELECT COUNT(*) FROM gebieden" in q:
                gezien["telling_provincie"] = params["provincie"]
                return _Telling(965)
            if "gebiedstype_id" in q and "LIMIT 1" in q:
                return _NepDb({"gebiedstype_id": "t"})
            if "FROM gemeenten" in q:
                return _Lijst([("Súdwest-Fryslân",)])
            return _Lijst(
                [_Rij({"id": "BU1", "naam": "B", "gemeente_code": "1900", "gebiedstype_id": "t", "is_water": False})]
            )

    monkeypatch.setattr(report_service, "referentie_params", nep_referentie_params)
    with pytest.raises(RuntimeError, match="stop"):
        getattr(report_service.ReportDataService(Db()), methode)(["BU1"], referentie="fryslan")
    assert gezien["gemeente_code"] is None
    assert gezien["provincie"] == provincie
    assert gezien["telling_provincie"] == provincie


class _Lijst(list):
    def fetchall(self):
        return list(self)

    def fetchone(self):
        return self[0] if self else None


def test_provincie_referentie_label_uit_de_data():
    from omnitwin.services.report_service import provincie_referentie_label

    assert provincie_referentie_label("Fryslân", 965) == "⌀ Provincie Fryslân (965 gebieden)"
    assert provincie_referentie_label("Groningen", 12) == "⌀ Provincie Groningen (12 gebieden)"
    assert provincie_referentie_label(None, 40) == "⌀ Alle gebieden (40)"


def test_referentie_params_provincie():
    from omnitwin.services.zscore_referentie import (
        SQL_REFERENTIE_STATS,
        SQL_REFERENTIE_WAARDEN,
        SQL_ZSCORE_GEBIEDEN,
        referentie_params,
    )

    assert referentie_params("t")["zs_provincie"] is None
    assert referentie_params("t", provincie="Fryslân")["zs_provincie"] == "Fryslân"
    for sql in (SQL_ZSCORE_GEBIEDEN, SQL_REFERENTIE_STATS, SQL_REFERENTIE_WAARDEN):
        assert "CAST(:zs_provincie AS varchar)" in sql


def test_geen_vaste_provincie_in_referentie():
    """#324: geen vast label 'Provincie Fryslân' of vast provinciefilter in de code."""
    bestanden = [ROOT / "src/omnitwin/services/report_service.py", ROOT / "static/js/app.js"] + [
        ROOT / f"admin-panel/src/pages/{p}Page.tsx" for p in ("Benchmark", "Deelgebied", "MultiGebied", "ThemaAnalyse")
    ]
    for pad in bestanden:
        tekst = pad.read_text(encoding="utf-8")
        assert "Provincie Fryslân" not in tekst, pad
        assert "provincie=eq.Frysl" not in tekst, pad
        assert "~965" not in tekst, pad


# ── footer ──────────────────────────────────────────────────────────────────


def _footer(organisatie):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    html = env.get_template("index.html").render(request=None, organisatie=organisatie, app_version="t")
    return html[html.index('<footer class="footer">') : html.index("</footer>")]


def test_footer_logos_uit_instelling():
    footer = _footer(org_service.lees_organisatie(_NepDb(SWF)))
    imgs = re.findall(r'<img src="([^"]+)" alt="([^"]*)" class="footer-logo" title="([^"]*)">', footer)
    assert imgs == [(l["pad"], l["naam"], l["naam"]) for l in SWF["logos"]]


def test_footer_zonder_organisatie_geen_logos():
    assert "<img" not in _footer(None)


# ── Kompas: standaardconfiguratie zonder vaste ID ───────────────────────────


def test_kompas_standaard_hierarchie(monkeypatch):
    from omnitwin.routers import kompas

    class NepService:
        def __init__(self, db):
            pass

        def get_standaard_config_id(self):
            return 7

        def get_hierarchie(self, config_id):
            return {
                "config_id": config_id,
                "config_naam": "x",
                "config_icoon": "x",
                "hierarchie": {"name": "Root", "children": []},
                "total_indicators": 0,
                "last_updated": "2026-10-02T00:00:00",
            }

    monkeypatch.setattr(kompas, "KompasService", NepService)
    r = _client(kompas.router, object()).get("/api/kompas/standaard/hierarchie")
    assert r.status_code == 200, r.text
    assert r.json()["config_id"] == 7


# ── geen vaste gemeentecode in de runtimecode ───────────────────────────────

# Waar in de runtimecode gezocht wordt (stuurdata, use cases, scripts en tests vallen erbuiten).
GESCAND = [
    ("src/omnitwin", "**/*.py"),
    ("static/js", "*.js"),
    ("admin-panel/src", "**/*.ts"),
    ("admin-panel/src", "**/*.tsx"),
    ("templates", "*.html"),
    ("db/schema", "*.sql"),
]
# '1900' of "GM1900" als losse string (geen jaartal, geen deel van een buurtcode)
LITERAL = re.compile(r"""(['"`])(?:GM|gm)?1900\1""")
# (bestand, stuk van de regel): bewust toegestaan, met reden
ALLOWLIST = {
    # voorbeeld-body in de OpenAPI-documentatie van /api/kompas/{id}/benchmark
    ("src/omnitwin/routers/kompas.py", '"gemeente_code": "1900"'),
    # terugvallijst van alle Friese gemeenten in de gemeentekiezer (geen standaard; medium in #231)
    ("static/js/app.js", "{ code: '1900', naam: 'Súdwest-Fryslân'"),
    # schema_latest.sql: commentaar bij gemeenten.code
    ("db/schema/schema_latest.sql", "bijv. 1900 voor"),
}


def test_geen_vaste_gemeentecode_in_runtimecode():
    gevonden = []
    for map_, patroon in GESCAND:
        for pad in sorted((ROOT / map_).glob(patroon)):
            rel = pad.relative_to(ROOT).as_posix()
            for nr, regel in enumerate(pad.read_text(encoding="utf-8").splitlines(), 1):
                if not LITERAL.search(regel):
                    continue
                if any(rel == f and stuk in regel for f, stuk in ALLOWLIST):
                    continue
                gevonden.append(f"{rel}:{nr}: {regel.strip()}")
    assert not gevonden, (
        "Vaste gemeentecode in code; gebruik de organisatie-instelling "
        "(omnitwin.services.organisatie, GET /api/organisatie):\n" + "\n".join(gevonden)
    )


def test_seed_en_migratie_passen_bij_elkaar():
    """De seed vult precies kolommen die de migratie aanmaakt, en bevat de SWF-gegevens."""
    migratie = (ROOT / "db/migraties/V027__organisatie.sql").read_text(encoding="utf-8")
    seed = (ROOT / "db/stuurdata/organisatie.sql").read_text(encoding="utf-8")
    tabel = migratie[migratie.index("CREATE TABLE IF NOT EXISTS public.organisatie") :]
    tabel = tabel[: tabel.index(");")]
    kolommen = set(re.findall(r"^\s{4}(\w+)\s", tabel, re.MULTILINE))
    seed_kolommen = re.search(r"INSERT INTO public\.organisatie\s*\(([^)]*)\)", seed).group(1)
    assert {k.strip() for k in seed_kolommen.split(",")} <= kolommen
    assert "ON CONFLICT (id) DO NOTHING" in seed
    assert "ARRAY['1900']" in seed and "geo-groep@sudwestfryslan.nl" in seed
    # buurten_in_deelgebied filtert op de organisatie, niet op een vaste code
    functie = migratie[migratie.index("FUNCTION postgisftw.buurten_in_deelgebied") :]
    assert "organisatie" in functie and "1900" not in functie
