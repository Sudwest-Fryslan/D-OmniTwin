"""
Unit test: kaartkleuring neemt polariteit en neutrale kleuring mee (#539).

Controleert zonder database:
- `_kaart_polariteit` voorrang: Samenstelling > `polariteit` > oude kolommen
- `get_kaart_attributes` in `percentiel`- en `label`-modus bij `lager_is_beter`
  (ook als `score_type` nog `+/+` is) en bij `neutraal` / kwadrant Samenstelling
- `ColorScaleService.compute_colors_for_data` leest `polariteit` met terugval op `score_type`
"""

from contextlib import nullcontext

import pytest

from omnitwin import polariteit as pol
from omnitwin.services import kleine_aantallen as ka
from omnitwin.services import labelklasse as lk
from omnitwin.services import percentielklasse as pk
from omnitwin.services.color_scale_service import ColorScaleService
from omnitwin.services.gebiedsmonitor_service import GebiedsmonitorService, _kaart_polariteit

pytestmark = pytest.mark.unit


class _FakeRow:
    def __init__(self, mapping: dict):
        self._mapping = mapping


class _FakeResult:
    def __init__(self, rows: list[dict], scalar_value=None):
        self._rows = [_FakeRow(r) for r in rows]
        self._scalar = scalar_value

    def __iter__(self):
        return iter(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


class _FakeDB:
    def __init__(self, kaart_rows: list[dict]):
        self.kaart_rows = kaart_rows
        self.queries: list[str] = []

    def begin_nested(self):
        return nullcontext()

    def execute(self, statement, params=None):
        sql = str(statement)
        self.queries.append(sql)
        if "FROM gebieden g" in sql:
            return _FakeResult(self.kaart_rows)
        if "SELECT COUNT(*)" in sql:
            return _FakeResult([], scalar_value=len(self.kaart_rows))
        return _FakeResult([])


def _maak_rijen(
    *,
    polariteit: str | None = "hoger_is_beter",
    score_type: str = "+/+",
    interpretatie_logica: str | None = None,
    is_neutraal_kwadrant: bool = False,
) -> list[dict]:
    waarden = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    return [
        {
            "id": f"BU1900000{idx}",
            "naam": f"Buurt {idx}",
            "gebiedstype_id": "00000000-0000-0000-0000-000000000001",
            "gemeente_code": "1900",
            "is_waterbuurt": False,
            "indicator_waarde": w,
            "jaar": 2025,
            "bron": "CBS",
            "n": 50,
            "indicator_naam": "Testindicator",
            "indicator_code": "IND_TEST",
            "eenheid": "%",
            "score_type": score_type,
            "polariteit": polariteit,
            "interpretatie_logica": interpretatie_logica,
            "is_neutraal_kwadrant": is_neutraal_kwadrant,
        }
        for idx, w in enumerate(waarden, start=1)
    ]


def _patch_referentie(monkeypatch, waarden: list[float]):
    monkeypatch.setattr(ka, "drempel", lambda _db: 10)
    monkeypatch.setattr(
        pk,
        "referentie_waarden",
        lambda _db, _gt, _gm, _uuids, jaar=None: {("1900", "ind-1"): waarden},
    )
    monkeypatch.setattr(pk, "onderdrukte_waarden", lambda _db, _gids, _uuids: set())
    monkeypatch.setattr(lk, "drempels_uit_db", lambda _db, _uuids: {})


@pytest.mark.parametrize(
    "row,verwacht",
    [
        ({"is_neutraal_kwadrant": True, "polariteit": "hoger_is_beter", "score_type": "+/-"}, pol.NEUTRAAL),
        ({"is_neutraal_kwadrant": False, "polariteit": "lager_is_beter", "score_type": "+/+"}, pol.LAGER_IS_BETER),
        ({"is_neutraal_kwadrant": False, "polariteit": "neutraal", "score_type": "+/-"}, pol.NEUTRAAL),
        ({"is_neutraal_kwadrant": False, "polariteit": None, "score_type": "-/+"}, pol.LAGER_IS_BETER),
        (
            {
                "is_neutraal_kwadrant": False,
                "polariteit": None,
                "score_type": "+/+",
                "interpretatie_logica": "neutraal",
            },
            pol.NEUTRAAL,
        ),
        ({"is_neutraal_kwadrant": False, "polariteit": None, "score_type": None}, pol.HOGER_IS_BETER),
    ],
)
def test_kaart_polariteit_voorrang(row, verwacht):
    assert _kaart_polariteit(row) == verwacht


def test_kaart_percentiel_volgt_polariteit_lager_is_beter_ondanks_score_type(monkeypatch):
    rijen = _maak_rijen(polariteit="lager_is_beter", score_type="+/+")
    _patch_referentie(monkeypatch, [float(r["indicator_waarde"]) for r in rijen])
    db = _FakeDB(rijen)

    res = GebiedsmonitorService(db).get_kaart_attributes(
        gebiedstype_id="00000000-0000-0000-0000-000000000001",
        indicator_uuid="ind-1",
        modus="percentiel",
    )

    assert "ind.polariteit" in db.queries[0]
    assert "v_kompas_hierarchie" in db.queries[0]
    assert res["metadata"]["polariteit"] == "lager_is_beter"
    # Laagste waarde (10.0) is gunstigst (klasse 8, blauw); hoogste (80.0) ongunstigst (klasse 1, rood)
    assert res["data"]["BU19000001"]["klasse"] == 8
    assert res["data"]["BU19000001"]["color"] == pk.PALET_FALLBACK["max"]
    assert res["data"]["BU19000008"]["klasse"] == 1
    assert res["data"]["BU19000008"]["color"] == pk.PALET_FALLBACK["min"]
    assert "(ongunstigst)" in res["metadata"]["klassen"][0]["label"]
    assert "(gunstigst)" in res["metadata"]["klassen"][-1]["label"]


def test_kaart_label_volgt_polariteit_lager_is_beter_ondanks_score_type(monkeypatch):
    rijen = _maak_rijen(polariteit="lager_is_beter", score_type="+/+")
    _patch_referentie(monkeypatch, [float(r["indicator_waarde"]) for r in rijen])
    db = _FakeDB(rijen)

    res = GebiedsmonitorService(db).get_kaart_attributes(
        gebiedstype_id="00000000-0000-0000-0000-000000000001",
        indicator_uuid="ind-1",
        modus="label",
    )

    normatief_palet = lk.palet()
    assert res["metadata"]["polariteit"] == "lager_is_beter"
    assert res["data"]["BU19000001"]["label"] == "A"
    assert res["data"]["BU19000001"]["klasse"] == 5
    assert res["data"]["BU19000001"]["color"] == normatief_palet[4]
    assert res["data"]["BU19000008"]["label"] == "E"
    assert res["data"]["BU19000008"]["klasse"] == 1
    assert res["data"]["BU19000008"]["color"] == normatief_palet[0]
    assert res["metadata"]["legenda_melding"] == lk.MELDING_VOORLOPIG
    assert "(gunstigst)" in res["metadata"]["klassen"][0]["omschrijving"]
    assert "(ongunstigst)" in res["metadata"]["klassen"][-1]["omschrijving"]


@pytest.mark.parametrize(
    "polariteit_db,is_samenstelling",
    [
        ("neutraal", False),
        ("hoger_is_beter", True),
    ],
)
def test_kaart_neutraal_percentiel_gebruikt_blauw_palet_en_neutrale_legenda(
    monkeypatch, polariteit_db, is_samenstelling
):
    rijen = _maak_rijen(polariteit=polariteit_db, score_type="+/+", is_neutraal_kwadrant=is_samenstelling)
    _patch_referentie(monkeypatch, [float(r["indicator_waarde"]) for r in rijen])
    db = _FakeDB(rijen)

    res = GebiedsmonitorService(db).get_kaart_attributes(
        gebiedstype_id="00000000-0000-0000-0000-000000000001",
        indicator_uuid="ind-1",
        modus="percentiel",
    )

    neutraal_palet = pk.palet(neutraal=True)
    assert res["metadata"]["polariteit"] == "neutraal"
    assert res["metadata"]["color_ramp"] == neutraal_palet
    # Hoogste waarde = klasse 8 (donkerblauw); laagste waarde = klasse 1 (lichtblauw)
    assert res["data"]["BU19000001"]["klasse"] == 1
    assert res["data"]["BU19000001"]["color"] == neutraal_palet[0]
    assert res["data"]["BU19000008"]["klasse"] == 8
    assert res["data"]["BU19000008"]["color"] == neutraal_palet[-1]
    assert res["metadata"]["klassen"][0]["label"] == "klasse 1: 0–12,5% (laagst)"
    assert res["metadata"]["klassen"][-1]["label"] == "klasse 8: 87,5–100% (hoogst)"
    assert not any("gunstig" in item["label"] for item in res["metadata"]["klassen"])


@pytest.mark.parametrize(
    "polariteit_db,is_samenstelling",
    [
        ("neutraal", False),
        ("hoger_is_beter", True),
    ],
)
def test_kaart_neutraal_label_ae_gebruikt_blauw_palet_en_neutrale_legenda(monkeypatch, polariteit_db, is_samenstelling):
    rijen = _maak_rijen(polariteit=polariteit_db, score_type="+/+", is_neutraal_kwadrant=is_samenstelling)
    _patch_referentie(monkeypatch, [float(r["indicator_waarde"]) for r in rijen])
    db = _FakeDB(rijen)

    res = GebiedsmonitorService(db).get_kaart_attributes(
        gebiedstype_id="00000000-0000-0000-0000-000000000001",
        indicator_uuid="ind-1",
        modus="label",
    )

    neutraal_palet = lk.palet(neutraal=True)
    assert res["metadata"]["polariteit"] == "neutraal"
    assert res["metadata"]["color_ramp"] == neutraal_palet
    assert res["data"]["BU19000001"]["label"] == "E"
    assert res["data"]["BU19000001"]["color"] == neutraal_palet[0]
    assert res["data"]["BU19000008"]["label"] == "A"
    assert res["data"]["BU19000008"]["color"] == neutraal_palet[-1]
    assert res["metadata"]["klassen"][0]["omschrijving"] == "label A (hoogst), kwintiel 80–100%"
    assert res["metadata"]["klassen"][-1]["omschrijving"] == "label E (laagst), kwintiel 0–20%"
    assert not any("gunstig" in item["omschrijving"] for item in res["metadata"]["klassen"])
    assert res["metadata"]["legenda_melding"] == lk.MELDING_VOORLOPIG_NEUTRAAL


def test_color_scale_service_gebruikt_polariteit_met_terugval_op_score_type():
    kleuren = {"min": "#111111", "mid": "#888888", "max": "#eeeeee"}

    def maak_service(config: dict) -> ColorScaleService:
        svc = ColorScaleService(db=None)
        svc.get_visualization_config = lambda _uuid: config
        return svc

    basis_ramp, _, _ = maak_service(
        {
            "colors": kleuren,
            "klassen": 5,
            "nodata_kleur": "#d1d5db",
            "classificatie": "quantile",
            "score_type": "+/+",
            "polariteit": "hoger_is_beter",
        }
    ).compute_colors_for_data([1.0, 2.0, 3.0], "ind-1")

    lager_ramp, _, _ = maak_service(
        {
            "colors": kleuren,
            "klassen": 5,
            "nodata_kleur": "#d1d5db",
            "classificatie": "quantile",
            "score_type": "+/+",
            "polariteit": "lager_is_beter",
        }
    ).compute_colors_for_data([1.0, 2.0, 3.0], "ind-1")

    neutraal_ramp, _, _ = maak_service(
        {
            "colors": kleuren,
            "klassen": 5,
            "nodata_kleur": "#d1d5db",
            "classificatie": "quantile",
            "score_type": "+/+",
            "polariteit": "neutraal",
        }
    ).compute_colors_for_data([1.0, 2.0, 3.0], "ind-1")

    assert lager_ramp == list(reversed(basis_ramp))
    assert neutraal_ramp == basis_ramp
