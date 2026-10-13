"""Organisatie en thema instellen vanuit het beheerscherm (#253).

- validatie van PUT /api/organisatie en de import (thema, logo's, e-mail, gemeentecodes);
- de themalijst met voorbeeldkleuren (licht en donker) uit static/css/themes;
- de beschikbare logo's (alleen bestaande afbeeldingen onder /static/images/);
- export -> import geeft dezelfde instelling; elke wijziging in de auditlog (wie en wat);
- zonder beheerrechten geen toegang (de afhankelijkheid vereis_admin).
"""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from omnitwin.database import get_db
from omnitwin.routers import organisatie as org_router
from omnitwin.routers.auth import vereis_admin
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
        {"pad": "/static/images/DF-LOGO-1-1000x1000-TBG.png", "naam": "Datafryslân", "rol": "partner"},
    ],
}

BEHEERDER = {"user_id": "s-123", "username": "beheer1", "is_admin": True, "type": "oidc", "onderwerp": "s-123"}


class _Rij:
    def __init__(self, d):
        self._mapping = d


class _Db:
    """Session met één organisatierij in het geheugen: SELECT leest hem, INSERT ... ON CONFLICT zet hem."""

    def __init__(self, rij=None):
        self.rij = dict(rij) if rij else None
        self.commits = 0
        self._laatste = None

    def execute(self, sql, params=None):
        q = str(sql)
        if "INSERT INTO public.organisatie" in q:
            self.rij = dict(params, logos=json.loads(params["logos"]))
            self._laatste = None
        else:
            self._laatste = self.rij
        return self

    def fetchone(self):
        return _Rij(self._laatste) if self._laatste is not None else None

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


@pytest.fixture
def audit(monkeypatch):
    regels = []
    monkeypatch.setattr(org_router.AppLogger, "info", classmethod(lambda cls, msg, **kw: regels.append((msg, kw))))
    return regels


def _client(db, gebruiker=BEHEERDER):
    app = FastAPI()
    app.include_router(org_router.router)
    app.dependency_overrides[get_db] = lambda: db
    if isinstance(gebruiker, HTTPException):

        def weiger():
            raise gebruiker

        app.dependency_overrides[vereis_admin] = weiger
    else:
        app.dependency_overrides[vereis_admin] = lambda: gebruiker
    return TestClient(app)


def _invoer(**wijziging):
    d = {k: v for k, v in SWF.items()}
    d.update(wijziging)
    return d


# ── validatie ───────────────────────────────────────────────────────────────


def test_put_geldig_zet_de_rij_en_geeft_de_organisatie(audit):
    db = _Db(SWF)
    r = _client(db).put("/api/organisatie", json=_invoer(thema="d-omnitwin", korte_naam="  SWF  "))
    assert r.status_code == 200, r.text
    assert r.json()["thema"] == "d-omnitwin"
    assert db.rij["thema"] == "d-omnitwin" and db.rij["korte_naam"] == "SWF"
    assert db.commits == 1


@pytest.mark.parametrize(
    "wijziging",
    [
        {"thema": "bestaat-niet"},
        {"thema": "../swf"},
        {"thema": "SWF"},
        {"logos": [{"pad": "/static/images/bestaat-niet.png"}]},
        {"logos": [{"pad": "/static/images/../css/styles.css"}]},
        {"logos": [{"pad": "/static/css/themes/swf.css"}]},
        {"logos": [{"pad": "https://example.org/logo.png"}]},
        {"logos": [{"pad": "/static/images/SWF-logo.png", "rol": "baas"}]},
        {"logos": [{"pad": "/static/images/SWF-logo.png", "extra": 1}]},
        {"contact_email": "geen-adres"},
        {"contact_email": "a@b"},
        {"contact_email": "twee@@voorbeeld.nl"},
        {"gemeente_codes": ["190"]},
        {"gemeente_codes": ["GM1900"]},
        {"gemeente_codes": ["19000"]},
        {"gemeente_codes": ["1900"], "standaard_gemeente_code": "0080"},
        {"oin": "123"},
        {"code": "SWF"},
        {"code": "a/b"},
        {"naam": "   "},
        {"onbekend_veld": "x"},
    ],
)
def test_put_ongeldig_422_en_niets_gewijzigd(wijziging, audit):
    db = _Db(SWF)
    r = _client(db).put("/api/organisatie", json=_invoer(**wijziging))
    assert r.status_code == 422, (wijziging, r.text)
    assert db.rij == SWF and db.commits == 0
    assert audit == []


def test_standaardgemeente_komt_vooraan_en_dubbele_codes_weg(audit):
    db = _Db(SWF)
    r = _client(db).put(
        "/api/organisatie", json=_invoer(gemeente_codes=["1900", "0080", "1900"], standaard_gemeente_code="0080")
    )
    assert r.status_code == 200, r.text
    assert db.rij["gemeente_codes"] == ["0080", "1900"]
    assert r.json()["standaard_gemeente_code"] == "0080"


def test_lege_optionele_velden_worden_null(audit):
    db = _Db(SWF)
    r = _client(db).put(
        "/api/organisatie", json=_invoer(contact_email="", korte_naam="", oin="", gemeente_codes=[], logos=[])
    )
    assert r.status_code == 200, r.text
    assert db.rij["contact_email"] is None and db.rij["korte_naam"] is None and db.rij["oin"] is None
    assert r.json()["standaard_gemeente_code"] is None


# ── rechten ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.parametrize(
    "methode,pad,body",
    [
        ("PUT", "/api/organisatie", SWF),
        ("GET", "/api/organisatie/themas", None),
        ("GET", "/api/organisatie/logos", None),
        ("GET", "/api/organisatie/export", None),
        ("POST", "/api/organisatie/import", {"formaat": "d-omnitwin/organisatie", "versie": 1, "organisatie": SWF}),
    ],
)
def test_zonder_beheerrechten_geweigerd(status, methode, pad, body, audit):
    db = _Db(SWF)
    r = _client(db, HTTPException(status_code=status)).request(methode, pad, json=body)
    assert r.status_code == status
    assert db.rij == SWF and audit == []


def test_lezen_blijft_publiek():
    assert _client(_Db(SWF), HTTPException(status_code=401)).get("/api/organisatie").status_code == 200


def test_schrijfroutes_hangen_aan_vereis_admin():
    """Elke route behalve de twee publieke leesroutes heeft vereis_admin als afhankelijkheid."""
    publiek = {("GET", "/api/organisatie"), ("GET", "/api/organisatie/beeldmerk.svg")}
    for route in org_router.router.routes:
        for methode in route.methods:
            if (methode, route.path) in publiek:
                continue
            deps = [d.call for d in route.dependant.dependencies]
            assert vereis_admin in deps, (methode, route.path)


# ── auditlog ────────────────────────────────────────────────────────────────


def test_audit_wie_en_wat_zonder_e_mailadres(audit):
    db = _Db(SWF)
    r = _client(db).put("/api/organisatie", json=_invoer(thema="d-omnitwin", contact_email="nieuw@voorbeeld.nl"))
    assert r.status_code == 200
    ((melding, kw),) = audit
    assert "beheer1" in melding and "sub=s-123" in melding
    assert kw["category"] == "ADMIN" and kw["user_id"] == "s-123"
    extra = kw["extra"]
    assert extra["actie"] == "organisatie.bijgewerkt" and extra["wie"] == "beheer1" and extra["sub"] == "s-123"
    assert extra["wijzigingen"]["thema"] == {"oud": "swf", "nieuw": "d-omnitwin"}
    assert extra["wijzigingen"]["contact_email"] == "gewijzigd"
    assert "nieuw@voorbeeld.nl" not in json.dumps(extra) + melding
    assert "geo-groep" not in json.dumps(extra) + melding


def test_wijzigingen_logos():
    oud = dict(SWF)
    nieuw = dict(SWF, logos=list(reversed(SWF["logos"])))
    assert org_service.wijzigingen(oud, nieuw)["logos"]["nieuw"][0] == "/static/images/DF-LOGO-1-1000x1000-TBG.png"
    hernoemd = dict(SWF, logos=[dict(SWF["logos"][0], naam="Anders"), SWF["logos"][1]])
    assert org_service.wijzigingen(oud, hernoemd) == {"logos": "namen of rollen gewijzigd"}
    assert org_service.wijzigingen(oud, dict(SWF)) == {}


# ── export en import ────────────────────────────────────────────────────────


def test_export_import_rondreis(audit):
    bron = _Db(dict(SWF, gemeente_codes=["1900", "0080"], oin="00000001234567890000"))
    r = _client(bron).get("/api/organisatie/export")
    assert r.status_code == 200, r.text
    assert r.headers["content-disposition"] == 'attachment; filename="organisatie-swf.json"'
    export = r.json()
    assert export["formaat"] == "d-omnitwin/organisatie" and export["versie"] == 1
    assert "standaard_gemeente_code" not in export["organisatie"]

    doel = _Db(dict(SWF, code="lwd", naam="Gemeente Leeuwarden", thema="d-omnitwin", logos=[]))
    r = _client(doel).post("/api/organisatie/import", json=export)
    assert r.status_code == 200, r.text
    assert _client(doel).get("/api/organisatie").json() == _client(bron).get("/api/organisatie").json()
    assert audit[-1][1]["extra"]["actie"] == "organisatie.geimporteerd"


@pytest.mark.parametrize(
    "export",
    [
        {"formaat": "iets-anders", "versie": 1, "organisatie": SWF},
        {"formaat": "d-omnitwin/organisatie", "versie": 2, "organisatie": SWF},
        {"formaat": "d-omnitwin/organisatie", "versie": 1, "organisatie": dict(SWF, thema="bestaat-niet")},
        {
            "formaat": "d-omnitwin/organisatie",
            "versie": 1,
            "organisatie": dict(SWF, logos=[{"pad": "/static/images/van-een-andere-instantie.png"}]),
        },
        {"formaat": "d-omnitwin/organisatie", "versie": 1},
    ],
)
def test_import_valideert_hetzelfde(export, audit):
    db = _Db(SWF)
    r = _client(db).post("/api/organisatie/import", json=export)
    assert r.status_code == 422, r.text
    assert db.rij == SWF and audit == []


def test_export_zonder_organisatie_404():
    assert _client(_Db(None)).get("/api/organisatie/export").status_code == 404


def test_eerste_keer_zetten_zonder_rij(audit):
    db = _Db(None)
    r = _client(db).put("/api/organisatie", json=SWF)
    assert r.status_code == 200, r.text
    assert db.rij["code"] == "swf"
    assert set(audit[0][1]["extra"]["wijzigingen"]) >= {"code", "naam", "thema"}


# ── thema's en logo's ───────────────────────────────────────────────────────


def test_themalijst_uit_static():
    lijst = _client(_Db(SWF)).get("/api/organisatie/themas").json()
    namen = [t["naam"] for t in lijst]
    assert namen == sorted(p.stem for p in (ROOT / "static/css/themes").glob("*.css"))
    swf = next(t for t in lijst if t["naam"] == "swf")
    assert swf["titel"] == "Gemeente Súdwest-Fryslân"
    licht, donker = swf["kleuren"]["licht"], swf["kleuren"]["donker"]
    assert licht["--basis-color-action-1-bg-default"] == "#a8003b"
    # Witte kopbalk met rode accentlijn, zoals sudwestfryslan.nl (#284)
    assert licht["--d-omnitwin-header-background-color-start"] == "#ffffff"
    assert donker["--d-omnitwin-header-background-color-start"] == "#262626"
    assert licht["--d-omnitwin-header-accent-color"] == "#bf0042"
    assert licht["--d-omnitwin-beeldmerk-vlak"] == "#bf0042"
    # WCAG-status uit het kopcommentaar (#284)
    assert swf["wcag_aa"] is True
    legacy = next(t for t in lijst if t["naam"] == "legacy")
    assert legacy["wcag_aa"] is False
    assert legacy["titel"] == "Klassiek groen-blauw"
    assert next(t for t in lijst if t["naam"] == "d-omnitwin")["wcag_aa"] is False


def test_themakleuren_lossen_var_op_en_donker_valt_terug_op_licht(tmp_path):
    (tmp_path / "proef.css").write_text(
        """/*
 * Thema "proef" — Gemeente Proef, als NL Design System-tokens.
 */
:root {
  --basis-color-accent-1-bg-default: #123456;
  --d-omnitwin-header-background-color-start: var(--basis-color-accent-1-bg-default);
  --d-omnitwin-header-color: var(--bestaat-niet, #ffffff);
  --basis-text-font-family-default: 'Inter', sans-serif;
  --d-omnitwin-beeldmerk-vlak: #000000;
}
[data-theme="dark"] {
  --basis-color-accent-1-bg-default: #abcdef;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme]) { --basis-color-accent-1-bg-default: #abcdef; } }
""",
        encoding="utf-8",
    )
    (tmp_path / "Ongeldig.css").write_text(":root {}", encoding="utf-8")
    lijst = org_service.themas(tmp_path)
    assert [t["naam"] for t in lijst] == ["proef"]
    t = lijst[0]
    assert t["titel"] == "Gemeente Proef"
    assert t["wcag_aa"] is None  # geen "@wcag-aa:"-regel: onbekend
    assert t["kleuren"]["licht"] == {
        "--basis-color-accent-1-bg-default": "#123456",
        "--d-omnitwin-header-background-color-start": "#123456",
        "--d-omnitwin-header-color": "#ffffff",
        "--d-omnitwin-beeldmerk-vlak": "#000000",
    }
    assert t["kleuren"]["donker"]["--basis-color-accent-1-bg-default"] == "#abcdef"
    assert t["kleuren"]["donker"]["--d-omnitwin-beeldmerk-vlak"] == "#000000"


def test_beschikbare_logos_en_logo_bestand(tmp_path):
    (tmp_path / "sub").mkdir()
    for naam in ("a.png", "b.SVG", "sub/c.webp", "leesmij.txt"):
        (tmp_path / naam).write_bytes(b"x")
    assert org_service.beschikbare_logos(tmp_path) == [
        "/static/images/a.png",
        "/static/images/b.SVG",
        "/static/images/sub/c.webp",
    ]
    assert org_service.logo_bestand("/static/images/sub/c.webp", tmp_path) is not None
    for pad in (
        "/static/images/leesmij.txt",
        "/static/images/../a.png",
        "/static/images/sub/../a.png",
        "/static/images/",
        "/static/a.png",
        "/static/images/sub\\c.webp",
        None,
        3,
    ):
        assert org_service.logo_bestand(pad, tmp_path) is None, pad


def test_logolijst_route():
    logos = _client(_Db(SWF)).get("/api/organisatie/logos").json()
    assert "/static/images/SWF-logo.png" in logos
    assert all(l.startswith("/static/images/") for l in logos)
