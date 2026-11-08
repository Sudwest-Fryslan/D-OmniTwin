"""
Unit tests voor de Gebiedsfactsheet (#441):
- Kompas-boom + percentielklassen 1..8 (polariteit, neutrale Samenstelling, aantallen uitgesloten)
- Gemeentelijke themarangorde met >= 50% dekkingsdrempel (alleen 1 buurt + gemeente-referentie)
- Top 3 sterke kanten & aandachtspunten op Onderdeel-niveau (Ring 3)
- Kleine-aantallenonderdrukking ('onderdrukt'), waterbuurten en ontbrekende geometrie
- Router-validatie (CBS_BUURT, één gemeente, max 200 gebieden)
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.routers import report as report_router
from omnitwin.services import factsheet_service as fs
from omnitwin.services.factsheet_service import (
    FactsheetService,
    bepaal_polariteit,
    bereken_trend,
    geojson_naar_svg_paden,
    is_aantal_indicator,
    klasse_duiding,
)

pytestmark = pytest.mark.unit

GT_BUURT = "afba67cb-6b38-4723-9c95-102a22d5b38a"
GT_WIJK = "11111111-2222-3333-4444-555555555555"

U_GROEN = "e4d53c01-ef30-56a3-9fc6-29e192462066"
U_ROKEN = "a4780646-844e-4221-b07a-b4f4ade25059"
U_BUSHALTES = "93564b76-b07a-4134-868e-10654650d064"
U_WERKZAMEN = "7fd17589-46b6-460a-a1f6-ef421517ccb3"
U_KLEIN = "4661dcb9-b7c4-42f8-b7c5-a61c12568806"
U_SCHAARS = "dacb8005-ecc2-5014-a5c2-a07c119b43ae"
U_SENIOREN = "89ad6843-0db9-4044-9508-307775d4f496"


class _nep_rij:
    def __init__(self, data: dict[str, Any]):
        self._mapping = data
        for k, v in data.items():
            setattr(self, k, v)

    def __getitem__(self, idx: int | str):
        if isinstance(idx, int):
            return list(self._mapping.values())[idx]
        return self._mapping[idx]


class _nep_resultaat:
    def __init__(self, rijen: list[dict[str, Any]] | None = None, scalar_val: Any = None):
        self._rijen = [_nep_rij(r) for r in (rijen or [])]
        self._scalar = scalar_val

    def fetchall(self):
        return self._rijen

    def fetchone(self):
        return self._rijen[0] if self._rijen else None

    def scalar(self):
        if self._scalar is not None:
            return self._scalar
        if self._rijen:
            return self._rijen[0][0]
        return None

    def __iter__(self):
        return iter(self._rijen)


class _FactsheetNepDb:
    """Minimale SQLAlchemy Session-stub die SQL-queries herkent op trefwoorden."""

    def __init__(
        self,
        buurten: list[dict[str, Any]],
        hierarchie: list[dict[str, Any]],
        doel_data: list[dict[str, Any]],
        ref_data: list[dict[str, Any]],
        hero_data: list[dict[str, Any]] | None = None,
        historie_data: list[dict[str, Any]] | None = None,
        geometrie_data: list[dict[str, Any]] | None = None,
        n_ref_buurten: int = 8,
    ):
        self.buurten = buurten
        self.hierarchie = hierarchie
        self.doel_data = doel_data
        self.ref_data = ref_data
        self.hero_data = hero_data or []
        self.historie_data = historie_data or []
        self.geometrie_data = geometrie_data or []
        self.n_ref_buurten = n_ref_buurten

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}

        if "JOIN gebiedstypes gt" in sql:
            gevraagd = set(params.get("gebied_ids") or [])
            return _nep_resultaat([b for b in self.buurten if b["id"] in gevraagd])

        if "SELECT id FROM kompas_configuraties" in sql:
            return _nep_resultaat([{"id": 3}])

        if "FROM color_schemas" in sql or "color_schema" in sql:
            return _nep_resultaat([])

        if "FROM public.organisatie" in sql:
            return _nep_resultaat(
                [
                    {
                        "code": "gem",
                        "naam": "Gemeente Teststad",
                        "korte_naam": "Teststad",
                        "oin": None,
                        "gemeente_codes": ["0080"],
                        "benchmark_provincie": "Fryslân",
                        "contact_email": None,
                        "logos": [],
                        "thema": "d-omnitwin",
                        "meld_url": None,
                        "n_drempel": 10,
                    }
                ]
            )

        if "SELECT COUNT(*) FROM gebieden" in sql:
            return _nep_resultaat(scalar_val=self.n_ref_buurten)

        if "ST_SimplifyPreserveTopology" in sql:
            return _nep_resultaat(self.geometrie_data)

        if "LOWER(TRIM(i_in.naam)) = ANY" in sql:
            gevraagd = set(params.get("gebied_ids") or [])
            return _nep_resultaat([h for h in self.hero_data if h["gebied_id"] in gevraagd])

        if "FROM kompas_configuraties kc" in sql and "JOIN kompas_titels kt" in sql:
            return _nep_resultaat(self.hierarchie)

        if "ROW_NUMBER() OVER" in sql and "FROM gebied_data" in sql:
            gevraagd = set(params.get("gebied_ids") or [])
            return _nep_resultaat([d for d in self.doel_data if d["gebied_id"] in gevraagd])

        if "zscore_referentie_waarden" in sql:
            return _nep_resultaat(self.ref_data)

        if "ORDER BY gd.indicator_uuid, gd.jaar ASC" in sql:
            gevraagd = set(params.get("gebied_ids") or [])
            return _nep_resultaat([h for h in self.historie_data if h["gebied_id"] in gevraagd])

        if "SELECT naam FROM gemeenten" in sql:
            return _nep_resultaat([{"naam": "Teststad"}])

        return _nep_resultaat([])

    def rollback(self):
        pass


# ── Hulpfuncties & zuivere logica ────────────────────────────────────────────


def test_is_aantal_indicator_herkent_eenheid_en_bekende_namen():
    assert is_aantal_indicator("aantal", "Aantal bushaltes") is True
    assert is_aantal_indicator(" AANTAL ", "Willekeurig") is True
    assert is_aantal_indicator(None, "werkzamen") is True
    assert is_aantal_indicator("", "ZZP'ers") is True
    assert is_aantal_indicator("%", "Roken") is False
    assert is_aantal_indicator("km", "Huisarts") is False


def test_bepaal_polariteit_en_duiding():
    assert bepaal_polariteit("lager_is_beter", "+/+", False, "Kwaliteit van leven") == "lager_is_beter"
    assert bepaal_polariteit("hoger_is_beter", "+/+", True, "Kwaliteit van leven") == "lager_is_beter"
    assert bepaal_polariteit("hoger_is_beter", "+/+", False, "Samenstelling") == "neutraal"
    assert bepaal_polariteit("neutraal", "+/+", False, "Kwaliteit fysieke leefomgeving") == "neutraal"

    assert klasse_duiding(8, neutraal=False) == "Zeer gunstig"
    assert klasse_duiding(1, neutraal=False) == "Zeer ongunstig"
    assert klasse_duiding(8, neutraal=True) == "Hoog (neutraal)"
    assert klasse_duiding(None) is None


def test_bereken_trend_polariteitsbewust():
    # Roken daalt van 22% naar 14% -> bij 'lager_is_beter' is daling gunstig
    reeks_roken = [{"jaar": 2020, "waarde": 22.0}, {"jaar": 2024, "waarde": 14.0}]
    t_roken = bereken_trend(reeks_roken, "lager_is_beter", "%")
    assert t_roken is not None
    assert t_roken["richting"] == "dalend"
    assert t_roken["duiding"] == "gunstig"
    assert "2020: 22,0% → 2024: 14,0%" == t_roken["label"]

    # Roken stijgt -> ongunstig
    t_roken_op = bereken_trend([{"jaar": 2020, "waarde": 14.0}, {"jaar": 2024, "waarde": 20.0}], "lager_is_beter", "%")
    assert t_roken_op["richting"] == "stijgend" and t_roken_op["duiding"] == "ongunstig"

    # Kleine schommeling (< 0,5 procentpunt) -> stabiel / neutraal
    t_stabiel = bereken_trend([{"jaar": 2022, "waarde": 20.1}, {"jaar": 2024, "waarde": 20.4}], "hoger_is_beter", "%")
    assert t_stabiel["richting"] == "stabiel" and t_stabiel["duiding"] == "neutraal"

    # Samenstelling / aantal -> altijd neutrale duiding
    t_neutraal = bereken_trend([{"jaar": 2020, "waarde": 15.0}, {"jaar": 2024, "waarde": 24.0}], "neutraal", "%")
    assert t_neutraal["richting"] == "stijgend" and t_neutraal["duiding"] == "neutraal"


def test_geojson_naar_svg_paden_met_binnenring_en_selectie():
    rijen = [
        {
            "id": "BU00800100",
            "naam": "Centrum",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]],
                    [[20, 20], [40, 20], [40, 40], [20, 40], [20, 20]],  # enclave / gat
                ],
            },
        },
        {
            "id": "BU00800200",
            "naam": "Noord",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[100, 0], [200, 0], [200, 100], [100, 100], [100, 0]]]],
            },
        },
    ]
    achtergrond, geselecteerd = geojson_naar_svg_paden(rijen, {"BU00800100"})
    assert len(geselecteerd) == 1 and geselecteerd[0]["id"] == "BU00800100"
    assert geselecteerd[0]["d"].count("M ") == 2  # buitenring + binnenring voor fillRule="evenodd"
    assert len(achtergrond) == 1 and achtergrond[0]["id"] == "BU00800200"


# ── Volledige serviceflow (enkel, meervoudig, waterbuurt, validatie) ─────────


def _basis_hierarchie() -> list[dict[str, Any]]:
    base = [
        # Kwadrant 1: Fysiek -> Openbare ruimte -> Klimaat (Groen + Bushaltes aantal + duplicaat Groen)
        {
            "kwadrant_id": 1,
            "kwadrant_naam": "Kwaliteit fysieke leefomgeving",
            "kwadrant_kleur": "#10b981",
            "kwadrant_volgorde": 1,
            "thema_id": 10,
            "thema_naam": "Openbare ruimte",
            "thema_volgorde": 1,
            "onderdeel_id": 100,
            "onderdeel_naam": "Klimaat & groen",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_GROEN,
            "indicator_naam": "Boomkroonbedekking",
            "eenheid": "%",
            "polariteit": "hoger_is_beter",
            "score_type": "+/+",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "RIVM",
        },
        # Duplicaat in hetzelfde thema (#491): moet ontdubbeld worden
        {
            "kwadrant_id": 1,
            "kwadrant_naam": "Kwaliteit fysieke leefomgeving",
            "kwadrant_kleur": "#10b981",
            "kwadrant_volgorde": 1,
            "thema_id": 10,
            "thema_naam": "Openbare ruimte",
            "thema_volgorde": 1,
            "onderdeel_id": 100,
            "onderdeel_naam": "Klimaat & groen",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_GROEN,
            "indicator_naam": "Boomkroonbedekking",
            "eenheid": "%",
            "polariteit": "hoger_is_beter",
            "score_type": "+/+",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "RIVM",
        },
        {
            "kwadrant_id": 1,
            "kwadrant_naam": "Kwaliteit fysieke leefomgeving",
            "kwadrant_kleur": "#10b981",
            "kwadrant_volgorde": 1,
            "thema_id": 10,
            "thema_naam": "Openbare ruimte",
            "thema_volgorde": 1,
            "onderdeel_id": 100,
            "onderdeel_naam": "Klimaat & groen",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_BUSHALTES,
            "indicator_naam": "Aantal bushaltes",
            "eenheid": "aantal",
            "polariteit": "hoger_is_beter",
            "score_type": "+/+",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "OSM",
        },
        {
            "kwadrant_id": 1,
            "kwadrant_naam": "Kwaliteit fysieke leefomgeving",
            "kwadrant_kleur": "#10b981",
            "kwadrant_volgorde": 1,
            "thema_id": 10,
            "thema_naam": "Openbare ruimte",
            "thema_volgorde": 1,
            "onderdeel_id": 100,
            "onderdeel_naam": "Klimaat & groen",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_SCHAARS,
            "indicator_naam": "Hitte-eiland",
            "eenheid": "°C",
            "polariteit": "lager_is_beter",
            "score_type": "+/-",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "RIVM",
        },
        # Kwadrant 3: Kwaliteit van leven -> Gezondheid -> Leefstijl (Roken lager_is_beter + Eenzaamheid onderdrukt + werkzamen aantal zonder eenheid)
        {
            "kwadrant_id": 3,
            "kwadrant_naam": "Kwaliteit van leven",
            "kwadrant_kleur": "#f59e0b",
            "kwadrant_volgorde": 3,
            "thema_id": 30,
            "thema_naam": "Gezondheid",
            "thema_volgorde": 1,
            "onderdeel_id": 300,
            "onderdeel_naam": "Leefstijl",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_ROKEN,
            "indicator_naam": "Roken",
            "eenheid": "%",
            "polariteit": "lager_is_beter",
            "score_type": "+/-",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "RIVM",
        },
        {
            "kwadrant_id": 3,
            "kwadrant_naam": "Kwaliteit van leven",
            "kwadrant_kleur": "#f59e0b",
            "kwadrant_volgorde": 3,
            "thema_id": 30,
            "thema_naam": "Gezondheid",
            "thema_volgorde": 1,
            "onderdeel_id": 300,
            "onderdeel_naam": "Leefstijl",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_KLEIN,
            "indicator_naam": "Eenzaamheid",
            "eenheid": "%",
            "polariteit": "lager_is_beter",
            "score_type": "+/-",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "RIVM",
        },
        {
            "kwadrant_id": 3,
            "kwadrant_naam": "Kwaliteit van leven",
            "kwadrant_kleur": "#f59e0b",
            "kwadrant_volgorde": 3,
            "thema_id": 30,
            "thema_naam": "Gezondheid",
            "thema_volgorde": 1,
            "onderdeel_id": 300,
            "onderdeel_naam": "Leefstijl",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_WERKZAMEN,
            "indicator_naam": "werkzamen",
            "eenheid": None,
            "polariteit": "hoger_is_beter",
            "score_type": "+/+",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "SWF",
        },
        # Kwadrant 4: Samenstelling (neutraal)
        {
            "kwadrant_id": 4,
            "kwadrant_naam": "Samenstelling",
            "kwadrant_kleur": "#64748b",
            "kwadrant_volgorde": 4,
            "thema_id": 40,
            "thema_naam": "Bebouwing",
            "thema_volgorde": 1,
            "onderdeel_id": 400,
            "onderdeel_naam": "Ouderdom",
            "onderdeel_volgorde": 1,
            "indicator_uuid": U_SENIOREN,
            "indicator_naam": "Woningen gebouwd vóór 1945 (BAG)",
            "eenheid": "%",
            "polariteit": "neutraal",
            "score_type": "+/+",
            "inverse": False,
            "weging": 1.0,
            "omschrijving": "",
            "bron": "BAG",
        },
    ]
    return base


def _maak_test_db() -> _FactsheetNepDb:
    buurten = [
        {
            "id": "BU008001",
            "naam": "Buurt Een",
            "gemeente_code": "0080",
            "gebiedstype_id": GT_BUURT,
            "gebiedstype_code": "CBS_BUURT",
            "gebiedstype_naam": "Buurt",
            "gemeente_naam": "Teststad",
            "is_waterbuurt": False,
            "heeft_geom": True,
        },
        {
            "id": "BU008002",
            "naam": "Buurt Twee (zonder geom)",
            "gemeente_code": "0080",
            "gebiedstype_id": GT_BUURT,
            "gebiedstype_code": "CBS_BUURT",
            "gebiedstype_naam": "Buurt",
            "gemeente_naam": "Teststad",
            "is_waterbuurt": False,
            "heeft_geom": False,
        },
        {
            "id": "BU008099",
            "naam": "Buitenwater",
            "gemeente_code": "0080",
            "gebiedstype_id": GT_BUURT,
            "gebiedstype_code": "CBS_BUURT",
            "gebiedstype_naam": "Buurt",
            "gemeente_naam": "Teststad",
            "is_waterbuurt": True,
            "heeft_geom": True,
        },
    ]

    # 8 referentiebuurten: BU008001..BU008008
    ref_data = []
    for i in range(1, 9):
        bid = f"BU00800{i}"
        # BU008001 heeft groen=80 (hoogste -> klasse 8), roken=28 (hoogste roken -> ongunstigst -> klasse 1!)
        groen_val = 90.0 - i * 10.0  # i=1 -> 80 (hoogste), i=8 -> 10
        roken_val = 30.0 - i * 2.0  # i=1 -> 28 (hoogste roken -> klasse 1 bij lager_is_beter!), i=8 -> 14
        sen_val = i * 10.0  # i=1 -> 10% (laag), i=8 -> 80%
        ref_data.append({"gebied_id": bid, "indicator_uuid": U_GROEN, "waarde": groen_val})
        ref_data.append({"gebied_id": bid, "indicator_uuid": U_ROKEN, "waarde": roken_val})
        ref_data.append({"gebied_id": bid, "indicator_uuid": U_SENIOREN, "waarde": sen_val})
        ref_data.append({"gebied_id": bid, "indicator_uuid": U_BUSHALTES, "waarde": float(i)})
        # Eenzaamheid (U_KLEIN): BU008001 is onderdrukt, BU008002..BU008008 hebben wel data
        if i >= 2:
            ref_data.append({"gebied_id": bid, "indicator_uuid": U_KLEIN, "waarde": 10.0 + i})
    # U_SCHAARS: maar 1 buurt in referentie (< 2 -> geen_referentie)
    ref_data.append({"gebied_id": "BU008001", "indicator_uuid": U_SCHAARS, "waarde": 1.2})

    doel_data = [
        {"gebied_id": "BU008001", "indicator_uuid": U_GROEN, "waarde": 80.0, "jaar": 2024},
        {"gebied_id": "BU008001", "indicator_uuid": U_BUSHALTES, "waarde": 1.0, "jaar": 2024},
        {"gebied_id": "BU008001", "indicator_uuid": U_SCHAARS, "waarde": 1.2, "jaar": 2024},
        {"gebied_id": "BU008001", "indicator_uuid": U_ROKEN, "waarde": 28.0, "jaar": 2024},
        {"gebied_id": "BU008001", "indicator_uuid": U_KLEIN, "waarde": 35.0, "jaar": 2024},  # wordt onderdrukt!
        {"gebied_id": "BU008001", "indicator_uuid": U_WERKZAMEN, "waarde": 420.0, "jaar": 2023},
        {"gebied_id": "BU008001", "indicator_uuid": U_SENIOREN, "waarde": 80.0, "jaar": 2024},
        # Tweede buurt voor multi-selectie
        {"gebied_id": "BU008002", "indicator_uuid": U_GROEN, "waarde": 70.0, "jaar": 2024},
        {"gebied_id": "BU008002", "indicator_uuid": U_BUSHALTES, "waarde": 5.0, "jaar": 2024},
        {"gebied_id": "BU008002", "indicator_uuid": U_ROKEN, "waarde": 26.0, "jaar": 2024},
        {"gebied_id": "BU008002", "indicator_uuid": U_WERKZAMEN, "waarde": 180.0, "jaar": 2023},
        {"gebied_id": "BU008002", "indicator_uuid": U_SENIOREN, "waarde": 70.0, "jaar": 2024},
    ]

    hero_data = [
        {"gebied_id": "BU008001", "naam_key": "inwoners", "waarde": 3000, "jaar": 2024},
        {"gebied_id": "BU008001", "naam_key": "huishoudens totaal", "waarde": 1400, "jaar": 2024},
        {"gebied_id": "BU008001", "naam_key": "woningvoorraad", "waarde": 1500, "jaar": 2025},
        {"gebied_id": "BU008001", "naam_key": "bouwjaar voor 1915", "waarde": 250, "jaar": 2024},
        {"gebied_id": "BU008001", "naam_key": "bouwjaar 1915-1945", "waarde": 250, "jaar": 2024},
        {"gebied_id": "BU008001", "naam_key": "bouwjaar 1945-1984", "waarde": 500, "jaar": 2024},
        {"gebied_id": "BU008001", "naam_key": "bouwjaar vanaf 1985", "waarde": 0, "jaar": 2024},
        {"gebied_id": "BU008002", "naam_key": "inwoners", "waarde": 1000, "jaar": 2024},
        {"gebied_id": "BU008002", "naam_key": "huishoudens totaal", "waarde": 500, "jaar": 2024},
        {"gebied_id": "BU008002", "naam_key": "woningvoorraad", "waarde": 520, "jaar": 2025},
    ]

    historie_data = [
        {"gebied_id": "BU008001", "indicator_uuid": U_ROKEN, "jaar": 2020, "waarde": 22.0},
        {"gebied_id": "BU008001", "indicator_uuid": U_ROKEN, "jaar": 2024, "waarde": 28.0},
    ]

    geom_data = [
        {
            "id": "BU008001",
            "naam": "Buurt Een",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]},
        }
    ]

    return _FactsheetNepDb(
        buurten=buurten,
        hierarchie=_basis_hierarchie(),
        doel_data=doel_data,
        ref_data=ref_data,
        hero_data=hero_data,
        historie_data=historie_data,
        geometrie_data=geom_data,
    )


def test_factsheet_enkele_buurt_volledige_methodiek(monkeypatch):
    db = _maak_test_db()
    # Markeer Eenzaamheid (U_KLEIN) als onderdrukt (n < 10) voor BU008001
    monkeypatch.setattr(
        fs.pk,
        "onderdrukte_waarden",
        lambda _db, _gids, _uuids: {("BU008001", U_KLEIN, 2024)},
    )

    uit = FactsheetService(db).genereer_factsheet(["BU008001"])

    assert uit["titel"] == "Buurt Een"
    assert uit["is_meervoudig"] is False
    assert uit["is_waterbuurt"] is False
    assert uit["config_id"] == 3  # dynamisch opgehaald, niet hardcoded 1
    assert uit["referentie_label"] == "⌀ Buurtgemiddelde gemeente Teststad"

    # Hero met eigen peiljaar per KPI + BAG-percentages
    assert uit["hero"]["inwoners"] == {"waarde": 3000, "jaar": 2024, "aantal_buurten_met_data": 1}
    assert uit["hero"]["woningen"] == {"waarde": 1500, "jaar": 2025, "aantal_buurten_met_data": 1}
    assert [b["percentage"] for b in uit["hero"]["bouwperiodes"]] == [25.0, 25.0, 50.0, 0.0]

    # Kwadrant 1 (Openbare ruimte): duplicaat Groen ontdubbeld; Bushaltes (aantal) telt NIET mee in score;
    # Hitte-eiland heeft n_ref=1 -> geen_referentie. Score rust op Groen (klasse 8) -> rang #1 van 8!
    kw_fysiek = uit["kwadranten"][0]
    th_openbaar = kw_fysiek["themas"][0]
    assert th_openbaar["klasse"] == 8
    assert th_openbaar["rang"] == {"positie": 1, "totaal_met_score": 8, "min_indicatoren_vereist": 1}
    inds_openbaar = {i["indicator_uuid"]: i for i in th_openbaar["onderdelen"][0]["indicatoren"]}
    assert len(th_openbaar["onderdelen"][0]["indicatoren"]) == 3  # duplicaat verwijderd!
    assert inds_openbaar[U_BUSHALTES]["status"] == "context_aantal"
    assert inds_openbaar[U_BUSHALTES]["klasse"] is None
    assert inds_openbaar[U_SCHAARS]["status"] == "geen_referentie"

    # Kwadrant 3 (Gezondheid -> Leefstijl): Roken=28% (hoogste -> klasse 1 wegens lager_is_beter!),
    # Eenzaamheid is onderdrukt (dus BU008001 heeft 1 van 2 indicatoren = 50% dekking -> rang #8 van 8),
    # werkzamen zonder eenheid herkend als context_aantal!
    kw_leven = uit["kwadranten"][1]
    th_gezond = kw_leven["themas"][0]
    assert th_gezond["klasse"] == 1
    assert th_gezond["rang"]["positie"] == 8
    inds_gezond = {i["indicator_uuid"]: i for i in th_gezond["onderdelen"][0]["indicatoren"]}
    assert inds_gezond[U_ROKEN]["klasse"] == 1
    assert inds_gezond[U_ROKEN]["trend"]["duiding"] == "ongunstig"
    assert inds_gezond[U_KLEIN]["status"] == "onderdrukt"
    assert inds_gezond[U_KLEIN]["duiding"] == "Afgeschermd (kleine aantallen)"
    assert inds_gezond[U_WERKZAMEN]["status"] == "context_aantal"

    # Kwadrant 4 (Samenstelling): is_neutraal=True, rang=None, niet in sterke_kanten!
    kw_sam = uit["kwadranten"][2]
    assert kw_sam["is_neutraal"] is True
    assert kw_sam["themas"][0]["rang"] is None
    assert kw_sam["themas"][0]["klasse"] == 8
    assert "neutraal" in kw_sam["themas"][0]["duiding"].lower()

    # Top 3 Onderdelen: Klimaat & groen in sterke_kanten, Leefstijl in aandachtspunten, Ouderdom NIET erin
    assert [s["onderdeel_naam"] for s in uit["sterke_kanten"]] == ["Klimaat & groen"]
    assert [a["onderdeel_naam"] for a in uit["aandachtspunten"]] == ["Leefstijl"]


def test_factsheet_meervoudige_selectie_met_waterbuurt_en_ontbrekende_geom(monkeypatch):
    db = _maak_test_db()
    monkeypatch.setattr(fs.pk, "onderdrukte_waarden", lambda *_a, **_k: set())

    uit = FactsheetService(db).genereer_factsheet(["BU008001", "BU008002", "BU008099"], deelgebied_naam="Zuidwesthoek")
    assert uit["titel"] == "Zuidwesthoek"
    assert uit["is_meervoudig"] is True
    assert uit["aantal_actieve_buurten"] == 2
    assert [w["id"] for w in uit["waterbuurten_uitgesloten"]] == ["BU008099"]
    assert [g["id"] for g in uit["contour_kaart"]["ontbrekende_geometrie_buurten"]] == ["BU008002"]

    # Geen gemeentelijke rang bij meervoudige selectie
    for kw in uit["kwadranten"]:
        for th in kw["themas"]:
            assert th["rang"] is None

    # Hero somt over de 2 actieve buurten (3000 + 1000 = 4000 inwoners)
    assert uit["hero"]["inwoners"]["waarde"] == 4000

    # Relatieve indicator is inwonersgewogen: (80*3000 + 70*1000) / 4000 = 77,5
    inds_openbaar = {i["indicator_uuid"]: i for i in uit["kwadranten"][0]["themas"][0]["onderdelen"][0]["indicatoren"]}
    assert inds_openbaar[U_GROEN]["waarde"] == pytest.approx(77.5)
    # Aantal-indicator toont som (1 + 5 = 6) én waarde_per_buurt (3,0), zonder scheef verschil
    assert inds_openbaar[U_BUSHALTES]["waarde"] == 6.0
    assert inds_openbaar[U_BUSHALTES]["waarde_per_buurt"] == 3.0
    assert inds_openbaar[U_BUSHALTES]["verschil"] is None


def test_factsheet_enkele_waterbuurt_geeft_nette_melding():
    db = _maak_test_db()
    uit = FactsheetService(db).genereer_factsheet(["BU008099"])
    assert uit["is_waterbuurt"] is True
    assert uit["kwadranten"] == []
    assert any("waterbuurt" in m.lower() for m in uit["meldingen"])


def test_validatie_weigert_niet_buurt_en_meerdere_gemeenten():
    wijk_db = _FactsheetNepDb(
        buurten=[
            {
                "id": "WK008000",
                "naam": "Wijk Centrum",
                "gemeente_code": "0080",
                "gebiedstype_id": GT_WIJK,
                "gebiedstype_code": "CBS_WIJK",
                "gebiedstype_naam": "Wijk",
                "gemeente_naam": "Teststad",
                "is_waterbuurt": False,
                "heeft_geom": True,
            }
        ],
        hierarchie=[],
        doel_data=[],
        ref_data=[],
    )
    with pytest.raises(GebruikersFout, match="CBS_BUURT"):
        FactsheetService(wijk_db).genereer_factsheet(["WK008000"])

    twee_gem_db = _FactsheetNepDb(
        buurten=[
            {
                "id": "BU008001",
                "naam": "Buurt A",
                "gemeente_code": "0080",
                "gebiedstype_id": GT_BUURT,
                "gebiedstype_code": "CBS_BUURT",
                "gebiedstype_naam": "Buurt",
                "gemeente_naam": "Stad A",
                "is_waterbuurt": False,
                "heeft_geom": True,
            },
            {
                "id": "BU008501",
                "naam": "Buurt B",
                "gemeente_code": "0085",
                "gebiedstype_id": GT_BUURT,
                "gebiedstype_code": "CBS_BUURT",
                "gebiedstype_naam": "Buurt",
                "gemeente_naam": "Stad B",
                "is_waterbuurt": False,
                "heeft_geom": True,
            },
        ],
        hierarchie=[],
        doel_data=[],
        ref_data=[],
    )
    with pytest.raises(GebruikersFout, match="één gemeente"):
        FactsheetService(twee_gem_db).genereer_factsheet(["BU008001", "BU008501"])


def test_router_endpoints_en_foutcodes(monkeypatch):
    db = _maak_test_db()
    monkeypatch.setattr(fs.pk, "onderdrukte_waarden", lambda *_a, **_k: set())

    app = FastAPI()
    app.include_router(report_router.router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    r_get = client.get("/api/report/factsheet/BU008001")
    assert r_get.status_code == 200
    assert r_get.json()["titel"] == "Buurt Een"

    r_post = client.post("/api/report/factsheet", json={"gebied_ids": ["BU008001", "BU008002"]})
    assert r_post.status_code == 200
    assert r_post.json()["is_meervoudig"] is True

    r_404 = client.get("/api/report/factsheet/BU_BESTAAT_NIET")
    assert r_404.status_code == 404

    r_422 = client.post("/api/report/factsheet", json={"gebied_ids": [f"BU{i}" for i in range(205)]})
    assert r_422.status_code == 422
