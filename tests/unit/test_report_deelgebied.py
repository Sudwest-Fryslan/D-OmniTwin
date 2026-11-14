"""
Unit tests voor issue #492:
- Tekst-escaping in deelgebied-SVG (generate_deelgebied_svg_kaart en _svg_empty_fallback)
- Gebruik van het actieve standaard Kompas-profiel (is_standaard = TRUE i.p.v. hardcoded config_id = 1)
- Neutrale Samenstelling en neutrale indicatoren leveren geen normatieve aandachtspunten of kansen op
"""

from __future__ import annotations

import html
from typing import Any

import pytest

from omnitwin import polariteit
from omnitwin.services.report_service import ReportDataService

pytestmark = pytest.mark.unit


class _NepRij:
    def __init__(self, data: dict[str, Any]):
        self._mapping = data
        for k, v in data.items():
            setattr(self, k, v)

    def __getitem__(self, idx: int | str):
        if isinstance(idx, int):
            return list(self._mapping.values())[idx]
        return self._mapping[idx]


class _NepResultaat:
    def __init__(self, rijen: list[dict[str, Any]] | None = None, scalar_val: Any = None):
        self._rijen = [_NepRij(r) for r in (rijen or [])]
        self._scalar = scalar_val

    def fetchall(self):
        return self._rijen

    def fetchone(self):
        return self._rijen[0] if self._rijen else None

    def scalar(self):
        return self._scalar


class _NepDb:
    def __init__(self, execute_handler=None):
        self._execute_handler = execute_handler
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append((str(sql), params))
        if self._execute_handler:
            return self._execute_handler(str(sql), params)
        return _NepResultaat([])


def test_deelgebied_svg_empty_fallback_escaping():
    """_svg_empty_fallback moet speciale tekens (<, >, &, \", ') netjes escapen."""
    service = ReportDataService(_NepDb())
    ongefilterde_tekst = "Bolsward <Centrum> & 'Zuid' \"Test\""
    svg = service._svg_empty_fallback(ongefilterde_tekst)

    assert "<Centrum>" not in svg
    assert "& 'Zuid'" not in svg
    assert html.escape(ongefilterde_tekst) in svg
    assert (
        "&lt;Centrum&gt; &amp; &#x27;Zuid&#x27; &quot;Test&quot;" in svg
        or "&lt;Centrum&gt; &amp; 'Zuid' &quot;Test&quot;" in svg
    )


def test_deelgebied_svg_kaart_escaping(monkeypatch):
    """generate_deelgebied_svg_kaart moet deelgebied_naam en feature-namen escapen in SVG."""
    nep_payload = {
        "deelgebied_naam": "Deelgebied <Noord> & 'Oost'",
        "kwadranten": [],
    }

    geom_polygon = {
        "type": "Polygon",
        "coordinates": [[[5.5, 53.0], [5.6, 53.0], [5.6, 53.1], [5.5, 53.1], [5.5, 53.0]]],
    }

    def nep_execute(sql, params):
        if "FROM gebieden g" in sql:
            return _NepResultaat(
                [
                    {
                        "id": "BU1",
                        "naam": "Buurt <1> & 'A'",
                        "geometry": geom_polygon,
                    }
                ]
            )
        return _NepResultaat([])

    db = _NepDb(nep_execute)
    service = ReportDataService(db)
    monkeypatch.setattr(service, "generate_deelgebied_payload", lambda **_kw: nep_payload)

    svg = service.generate_deelgebied_svg_kaart(gebied_ids=["BU1"], deelgebied_naam="Deelgebied <Noord> & 'Oost'")

    # Verifieer dat raw <, >, & niet ongeëscaped in de tekst- en title-tags voorkomen
    assert "<Noord>" not in svg
    assert "<1>" not in svg
    assert html.escape("Deelgebied <Noord> & 'Oost'") in svg
    assert html.escape("Buurt <1> & 'A'") in svg


def test_deelgebied_payload_standaard_profiel_in_query(monkeypatch):
    """generate_deelgebied_payload moet het standaard kompas-profiel gebruiken (is_standaard = TRUE) i.p.v. config_id = 1."""
    gevonden_queries = []

    def nep_execute(sql, params):
        q = str(sql)
        gevonden_queries.append(q)
        if "FROM public.organisatie" in q:
            return _NepResultaat(
                [{"id": "org1", "standaard_gemeente_code": "GM1900", "benchmark_provincie": "Fryslân"}]
            )
        if "FROM gebieden g" in q:
            return _NepResultaat(
                [
                    {
                        "id": "BU1",
                        "naam": "Buurt 1",
                        "gemeente_code": "GM1900",
                        "gebiedstype_id": "gt1",
                        "is_water": False,
                    }
                ]
            )
        if "gebiedstype_id" in q and "LIMIT 1" in q:
            return _NepResultaat([{"gebiedstype_id": "gt1"}])
        if "SELECT gd.gebied_id, gd.waarde AS inwoners" in q:
            return _NepResultaat([{"gebied_id": "BU1", "inwoners": 1000}])
        if "WITH zscores AS" in q:
            return _NepResultaat([])
        return _NepResultaat([])

    db = _NepDb(nep_execute)
    service = ReportDataService(db)

    # Voer aanroep uit
    service.generate_deelgebied_payload(gebied_ids=["BU1"])

    zscores_query = next((q for q in gevonden_queries if "WITH zscores AS" in q), None)
    assert zscores_query is not None
    # Mag géén hardcoded config_id = 1 meer bevatten
    assert "vkh.config_id = 1" not in zscores_query
    # Moet koppelen aan het standaardprofiel (is_standaard = TRUE)
    assert "kc.is_standaard = TRUE" in zscores_query or "kc.is_standaard = true" in zscores_query


def test_deelgebied_samenstelling_en_neutraal_geen_normatieve_aandacht_of_kans(monkeypatch):
    """Kwadrant Samenstelling en indicatoren met polariteit='neutraal' mogen geen aandachtspunten of kansen opleveren."""
    zscore_rijen = [
        # Kwadrant Samenstelling: afwijkende z-scores, maar moet neutraal blijven
        {
            "indicator_uuid": "uuid-sam-1",
            "gebied_id": "BU1",
            "buurt_naam": "Buurt 1",
            "waarde": 50.0,
            "jaar": 2024,
            "avg_waarde": 30.0,
            "std_waarde": 10.0,
            "min_waarde": 10.0,
            "max_waarde": 60.0,
            "n_ref_buurten": 20,
            "z_score": 2.0,  # extreme afwijking
            "indicator_naam": "Inwoners 65+",
            "eenheid": "%",
            "polariteit": polariteit.NEUTRAAL,
            "score_type": "+/+",
            "omschrijving": "",
            "ontologische_beschrijving": "",
            "bron": "",
            "kwadrant_naam": "Samenstelling",
            "kwadrant_kleur": "#60A5FA",
            "thema_naam": "Bevolking",
            "onderdeel_naam": "Leeftijd",
        },
        # Kwadrant Kwaliteit van leven: neutrale indicator
        {
            "indicator_uuid": "uuid-neutraal-2",
            "gebied_id": "BU1",
            "buurt_naam": "Buurt 1",
            "waarde": 15.0,
            "jaar": 2024,
            "avg_waarde": 10.0,
            "std_waarde": 2.0,
            "min_waarde": 5.0,
            "max_waarde": 20.0,
            "n_ref_buurten": 20,
            "z_score": 2.5,
            "indicator_naam": "Beschrijvende Context Indicator",
            "eenheid": "aantal",
            "polariteit": polariteit.NEUTRAAL,
            "score_type": "+/+",
            "omschrijving": "",
            "ontologische_beschrijving": "",
            "bron": "",
            "kwadrant_naam": "Kwaliteit van leven",
            "kwadrant_kleur": "#34D399",
            "thema_naam": "Gezondheid",
            "onderdeel_naam": "Leefstijl",
        },
        # Kwadrant Kwaliteit van leven: normatieve indicator (ongunstig)
        {
            "indicator_uuid": "uuid-normatief-3",
            "gebied_id": "BU1",
            "buurt_naam": "Buurt 1",
            "waarde": 25.0,
            "jaar": 2024,
            "avg_waarde": 12.0,
            "std_waarde": 3.0,
            "min_waarde": 5.0,
            "max_waarde": 30.0,
            "n_ref_buurten": 20,
            "z_score": 4.33,
            "indicator_naam": "Ernstige Eenzaamheid",
            "eenheid": "%",
            "polariteit": polariteit.LAGER_IS_BETER,
            "score_type": "+/-",
            "omschrijving": "",
            "ontologische_beschrijving": "",
            "bron": "",
            "kwadrant_naam": "Kwaliteit van leven",
            "kwadrant_kleur": "#34D399",
            "thema_naam": "Gezondheid",
            "onderdeel_naam": "Mentaal",
        },
    ]

    def nep_execute(sql, params):
        q = str(sql)
        if "FROM public.organisatie" in q:
            return _NepResultaat(
                [{"id": "org1", "standaard_gemeente_code": "GM1900", "benchmark_provincie": "Fryslân"}]
            )
        if "FROM gebieden g" in q:
            return _NepResultaat(
                [
                    {
                        "id": "BU1",
                        "naam": "Buurt 1",
                        "gemeente_code": "GM1900",
                        "gebiedstype_id": "gt1",
                        "is_water": False,
                    }
                ]
            )
        if "gebiedstype_id" in q and "LIMIT 1" in q:
            return _NepResultaat([{"gebiedstype_id": "gt1"}])
        if "SELECT gd.gebied_id, gd.waarde AS inwoners" in q:
            return _NepResultaat([{"gebied_id": "BU1", "inwoners": 1000}])
        if "WITH zscores AS" in q:
            return _NepResultaat(zscore_rijen)
        return _NepResultaat([])

    db = _NepDb(nep_execute)
    service = ReportDataService(db)

    payload = service.generate_deelgebied_payload(gebied_ids=["BU1"])

    kwadranten = {k["kwadrant_naam"]: k for k in payload["kwadranten"]}

    # 1. Kwadrant Samenstelling
    sam = kwadranten["Samenstelling"]
    assert sam["gem_zscore"] is None
    assert sam["n_aandachtspunten"] == 0
    assert sam["n_kansen"] == 0
    assert sam["totaal_aandachtspunten"] == 0
    assert sam["totaal_kansen"] == 0
    assert sam["n_aandachtspunten_sterk"] == 0
    assert sam["n_kansen_sterk"] == 0
    for th in sam["themas"]:
        assert th["top10_aandachtspunten"] == []
        assert th["top10_kansen"] == []
        assert th["totaal_aandachtspunten"] == 0
        assert th["totaal_kansen"] == 0

    # 2. Kwadrant Kwaliteit van leven
    kvl = kwadranten["Kwaliteit van leven"]
    # De normatieve indicator moet wél als aandachtspunt geteld worden
    assert kvl["n_aandachtspunten"] == 1
    assert kvl["n_kansen"] == 0
    thema_gezondheid = next(th for th in kvl["themas"] if th["thema_naam"] == "Gezondheid")
    assert len(thema_gezondheid["top10_aandachtspunten"]) == 1
    assert thema_gezondheid["top10_aandachtspunten"][0]["indicator_uuid"] == "uuid-normatief-3"
    # De neutrale indicator mag NOOIT in top10_aandachtspunten of top10_kansen zitten
    alle_aandacht_kansen = [
        i["indicator_uuid"] for i in thema_gezondheid["top10_aandachtspunten"] + thema_gezondheid["top10_kansen"]
    ]
    assert "uuid-neutraal-2" not in alle_aandacht_kansen
