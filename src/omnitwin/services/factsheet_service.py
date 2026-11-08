"""
Gebiedsfactsheet Service (#441)
===============================
Deterministische berekening voor de Gebiedsfactsheet (/rapport/factsheet),
gebouwd op de bestaande Kompas-hiërarchie en percentielklassen 1..8
(omnitwin.services.percentielklasse, #255) en kleine-aantallenonderdrukking (#325).

Ondersteunt uitsluitend CBS-buurten (CBS_BUURT) binnen één gemeente (1 buurt of
meervoudige buurtselectie). Geen LLM-aanroepen, geen ruwe SVG-HTML.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin.fouten import GebruikersFout
from omnitwin.services import percentielklasse as pk
from omnitwin.services.color_scale_service import ColorScaleService
from omnitwin.services.kompas_service import GEEN_DATA_KLEUR, KompasService
from omnitwin.services.organisatie import eigen_gemeente_code, lees_organisatie
from omnitwin.services.zscore_referentie import (
    CBS_BUURT_CODE,
    SCENARIO_STANDAARD,
    SQL_REFERENTIE_WAARDEN,
    referentie_params,
)

GELDIGE_REFERENTIES = ("gemeente", "fryslan", "provincie")

# Bekende tel-indicatoren waarbij de eenheid in de bron nog leeg staat (tot #491 is afgerond)
BEKENDE_AANTAL_NAMEN = frozenset({"werkzamen", "zzp'ers"})

# Bouwperiodes uit de BAG voor de Hero-balk (volgorde oud -> nieuw)
BAG_BOUWPERIODES: tuple[tuple[str, str], ...] = (
    ("bouwjaar voor 1915", "Vóór 1915"),
    ("bouwjaar 1915-1945", "1915–1945"),
    ("bouwjaar 1945-1984", "1945–1984"),
    ("bouwjaar vanaf 1985", "Vanaf 1985"),
)

HERO_INDICATOR_NAMEN: tuple[str, ...] = (
    "inwoners",
    "huishoudens totaal",
    "huishoudens (bag woonfunctie)",
    "woningvoorraad",
    "woonfunctie",
    *(naam for naam, _ in BAG_BOUWPERIODES),
)

MIN_REFERENTIE_BUURTEN = 2
THEMA_RANG_DEKKING_FRACTIE = 0.5


def is_aantal_indicator(eenheid: str | None, naam: str | None) -> bool:
    """True als de indicator een absoluut aantal telt en dus niet normatief meeweegt."""
    eenheid_norm = (eenheid or "").strip().lower()
    naam_norm = (naam or "").strip().lower()
    return eenheid_norm == "aantal" or naam_norm in BEKENDE_AANTAL_NAMEN


def klasse_duiding(klasse: int | None, neutraal: bool = False) -> str | None:
    """Korte tekstduiding bij klasse 1..8 (WCAG 2.1 AA: nooit informatie alleen via kleur)."""
    if klasse is None:
        return None
    if neutraal:
        if klasse >= 7:
            return "Hoog (neutraal)"
        if klasse == 6:
            return "Boven midden (neutraal)"
        if klasse in (4, 5):
            return "Midden (neutraal)"
        if klasse == 3:
            return "Onder midden (neutraal)"
        return "Laag (neutraal)"
    mapping = {
        8: "Zeer gunstig",
        7: "Gunstig",
        6: "Licht gunstig",
        5: "Gemiddeld",
        4: "Gemiddeld",
        3: "Licht ongunstig",
        2: "Ongunstig",
        1: "Zeer ongunstig",
    }
    return mapping.get(klasse)


def bepaal_polariteit(
    polariteit_db: str | None,
    score_type: str | None,
    inverse: bool | None,
    kwadrant_naam: str | None,
) -> str:
    """Bepaalt 'hoger_is_beter' | 'lager_is_beter' | 'neutraal' voor een indicator in het Kompas."""
    if pk.is_neutraal_kwadrant(kwadrant_naam):
        return "neutraal"
    if inverse:
        return "lager_is_beter"
    if polariteit_db in ("hoger_is_beter", "lager_is_beter", "neutraal"):
        return polariteit_db
    return pk.richting(score_type, inverse, kwadrant_naam)


def formatteer_getal_nl(waarde: float, eenheid: str | None = None) -> str:
    """Formatteert een meetwaarde voor toegankelijke trendlabels (NL-notatie)."""
    if abs(waarde - round(waarde)) < 1e-6 and (eenheid or "").strip().lower() in ("aantal", "jaar", "m"):
        tekst = f"{int(round(waarde)):,}".replace(",", ".")
    else:
        tekst = f"{waarde:.1f}".replace(".", ",")
    eenheid_str = (eenheid or "").strip()
    if not eenheid_str or eenheid_str.lower() == "aantal":
        return tekst
    if eenheid_str == "%":
        return f"{tekst}%"
    return f"{tekst} {eenheid_str}"


def bereken_trend(
    historie: list[dict[str, Any]],
    polariteit_richting: str,
    eenheid: str | None,
    is_aantal: bool = False,
) -> dict[str, Any] | None:
    """
    Bepaalt de meerjarige trend ('stijgend' | 'dalend' | 'stabiel') en polariteitsbewuste
    duiding ('gunstig' | 'ongunstig' | 'neutraal') uit een chronologische tijdreeks.
    """
    if len(historie) < 2:
        return None
    eerste = historie[0]
    laatste = historie[-1]
    if laatste["jaar"] <= eerste["jaar"]:
        return None

    v_oud = float(eerste["waarde"])
    v_nieuw = float(laatste["waarde"])
    delta = v_nieuw - v_oud
    eenheid_norm = (eenheid or "").strip()

    if abs(delta) < 1e-6:
        richting = "stabiel"
    elif eenheid_norm == "%" and abs(delta) < 0.5:
        richting = "stabiel"
    elif eenheid_norm != "%" and abs(v_oud) > 1e-6 and (abs(delta) / abs(v_oud)) < 0.02:
        richting = "stabiel"
    else:
        richting = "stijgend" if delta > 0 else "dalend"

    if richting == "stabiel" or polariteit_richting == "neutraal" or is_aantal:
        duiding = "neutraal"
    elif polariteit_richting == "hoger_is_beter":
        duiding = "gunstig" if richting == "stijgend" else "ongunstig"
    else:
        duiding = "gunstig" if richting == "dalend" else "ongunstig"

    label = (
        f"{eerste['jaar']}: {formatteer_getal_nl(v_oud, eenheid)} → "
        f"{laatste['jaar']}: {formatteer_getal_nl(v_nieuw, eenheid)}"
    )
    return {
        "richting": richting,
        "duiding": duiding,
        "delta": round(delta, 2),
        "van_jaar": int(eerste["jaar"]),
        "tot_jaar": int(laatste["jaar"]),
        "label": label,
    }


def geojson_naar_svg_paden(
    geometrie_rijen: list[dict[str, Any]],
    geselecteerde_ids: set[str],
    svg_w: int = 400,
    svg_h: int = 320,
    marge: int = 16,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Projecteert GeoJSON Polygon/MultiPolygon geometrieën (in vlakke RD-coördinaten)
    met behoud van 1:1 beeldverhouding naar SVG path `d`-strings voor React `<path fillRule="evenodd">`.
    """
    alle_ringen_per_gebied: list[tuple[str, str, list[list[tuple[float, float]]]]] = []
    xs: list[float] = []
    ys: list[float] = []

    for rij in geometrie_rijen:
        geom = rij.get("geometry")
        if not isinstance(geom, dict):
            continue
        gtype = geom.get("type")
        coords = geom.get("coordinates") or []
        ringen: list[list[tuple[float, float]]] = []
        if gtype == "Polygon":
            for ring in coords:
                pts = [(float(c[0]), float(c[1])) for c in ring if len(c) >= 2]
                if len(pts) >= 3:
                    ringen.append(pts)
        elif gtype == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    pts = [(float(c[0]), float(c[1])) for c in ring if len(c) >= 2]
                    if len(pts) >= 3:
                        ringen.append(pts)
        if ringen:
            for ring in ringen:
                for x, y in ring:
                    xs.append(x)
                    ys.append(y)
            alle_ringen_per_gebied.append((str(rij["id"]), str(rij["naam"]), ringen))

    if not xs or not ys:
        return [], []

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    dx = max_x - min_x or 1.0
    dy = max_y - min_y or 1.0

    binnen_w = max(1.0, svg_w - 2 * marge)
    binnen_h = max(1.0, svg_h - 2 * marge)
    schaal = min(binnen_w / dx, binnen_h / dy)
    offset_x = (svg_w - dx * schaal) / 2.0
    offset_y = (svg_h - dy * schaal) / 2.0

    achtergrond: list[dict[str, str]] = []
    geselecteerd: list[dict[str, str]] = []

    for gid, naam, ringen in alle_ringen_per_gebied:
        onderdelen: list[str] = []
        for ring in ringen:
            geprojecteerd = [
                f"{offset_x + (x - min_x) * schaal:.1f} {offset_y + (max_y - y) * schaal:.1f}" for x, y in ring
            ]
            onderdelen.append("M " + " L ".join(geprojecteerd) + " Z")
        pad_obj = {"id": gid, "naam": naam, "d": " ".join(onderdelen)}
        if gid in geselecteerde_ids:
            geselecteerd.append(pad_obj)
        else:
            achtergrond.append(pad_obj)

    return achtergrond, geselecteerd


class FactsheetService:
    """Genereert de volledige JSON-payload voor de Gebiedsfactsheet."""

    def __init__(self, db: Session):
        self.db = db

    def genereer_factsheet(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        deelgebied_naam: str | None = None,
        config_id: int | None = None,
    ) -> dict[str, Any]:
        schone_ids = list(dict.fromkeys(g.strip() for g in gebied_ids if g and g.strip()))
        if not schone_ids:
            raise GebruikersFout("Minimaal 1 gebied_id is vereist.")

        ref_norm = (referentie or "gemeente").strip().lower()
        if ref_norm not in GELDIGE_REFERENTIES:
            raise GebruikersFout(f"Onbekende referentie '{referentie}'. Kies 'gemeente' of 'fryslan'.")
        ref_modus = "gemeente" if ref_norm == "gemeente" else "fryslan"

        geb_rows = self._valideer_en_haal_buurten(schone_ids)
        eerste = geb_rows[0]
        gebiedstype_id = str(eerste["gebiedstype_id"])

        gevonden_gemeenten = {str(r["gemeente_code"]) for r in geb_rows if r.get("gemeente_code")}
        if len(gevonden_gemeenten) > 1:
            raise GebruikersFout(
                "De Gebiedsfactsheet ondersteunt alleen buurten binnen één gemeente. "
                "Selecteer buurten uit dezelfde gemeente."
            )

        gem_code = next(iter(gevonden_gemeenten), None) or gemeente_code or eigen_gemeente_code(self.db)
        if gemeente_code and gem_code and str(gemeente_code) != str(gem_code):
            raise GebruikersFout(f"De geselecteerde buurten horen bij gemeente {gem_code}, niet bij {gemeente_code}.")
        gem_naam = eerste.get("gemeente_naam") or self._haal_gemeente_naam(gem_code) or gem_code or "Onbekend"

        waterbuurten = [{"id": str(r["id"]), "naam": str(r["naam"])} for r in geb_rows if r.get("is_waterbuurt")]
        actieve_buurten = [r for r in geb_rows if not r.get("is_waterbuurt")]

        contour_kaart = self._bouw_contour_kaart(
            gemeente_code=gem_code,
            gebiedstype_id=gebiedstype_id,
            geselecteerde_ids={str(r["id"]) for r in geb_rows},
            geb_rows=geb_rows,
        )

        kompas_svc = KompasService(self.db)
        gekozen_config_id = config_id if config_id is not None else kompas_svc.get_standaard_config_id()

        color_svc = ColorScaleService(self.db)
        kleuren_normatief = pk.palet(color_svc, neutraal=False)
        kleuren_neutraal = pk.palet(color_svc, neutraal=True)

        provincie, referentie_label, n_ref_totaal = self._bepaal_referentie_kader(
            ref_modus=ref_modus,
            gebiedstype_id=gebiedstype_id,
            gemeente_code=gem_code,
            gemeente_naam=gem_naam,
        )

        is_enkel = len(schone_ids) == 1
        titel = (
            deelgebied_naam.strip()
            if deelgebied_naam and deelgebied_naam.strip()
            else (str(eerste["naam"]) if is_enkel else f"{len(actieve_buurten) or len(schone_ids)} buurten")
        )

        # Uitsluitend waterbuurt(en) geselecteerd: nette factsheet met melding zonder normatieve scores
        if not actieve_buurten:
            return {
                "titel": titel,
                "is_meervoudig": not is_enkel,
                "is_waterbuurt": True,
                "totaal_geselecteerd": len(schone_ids),
                "aantal_actieve_buurten": 0,
                "geselecteerde_buurten": [
                    {"id": str(r["id"]), "naam": str(r["naam"]), "is_waterbuurt": True} for r in geb_rows
                ],
                "waterbuurten_uitgesloten": waterbuurten,
                "gemeente_code": gem_code,
                "gemeente_naam": gem_naam,
                "referentie_modus": ref_modus,
                "referentie_label": referentie_label,
                "n_referentie_buurten": n_ref_totaal,
                "config_id": gekozen_config_id,
                "hero": {
                    "inwoners": None,
                    "huishoudens": None,
                    "woningen": None,
                    "bouwperiodes": [],
                    "bouwperiodes_jaar": None,
                },
                "contour_kaart": contour_kaart,
                "kwadranten": [],
                "sterke_kanten": [],
                "aandachtspunten": [],
                "klassen_legenda": pk.legenda(kleuren_normatief),
                "klassen_legenda_neutraal": pk.legenda(kleuren_neutraal),
                "meldingen": [
                    "Dit gebied is een waterbuurt. Waterbuurten vallen buiten de bewoningsbenchmark "
                    "en krijgen geen percentielklassen of rangpositie."
                ],
            }

        actieve_ids = [str(r["id"]) for r in actieve_buurten]
        hero, inwoners_per_buurt = self._haal_hero_en_gewichten(actieve_ids)

        hierarchie_rijen = self._haal_kompas_hierarchie(gekozen_config_id)
        alle_uuids = sorted({r["indicator_uuid"] for r in hierarchie_rijen})

        doel_waarden, onderdrukt_set = self._haal_doel_waarden(actieve_ids, alle_uuids)
        ref_per_indicator, buurt_waarden_in_ref = self._haal_referentie_data(
            gebiedstype_id=gebiedstype_id,
            gemeente_code=gem_code if ref_modus == "gemeente" else None,
            provincie=provincie,
            indicator_uuids=alle_uuids,
        )
        historie_map = self._haal_historie(actieve_ids, alle_uuids, inwoners_per_buurt)

        kan_rang_tonen = len(actieve_ids) == 1 and ref_modus == "gemeente"
        enkele_buurt_id = actieve_ids[0] if kan_rang_tonen else None

        kwadranten, sterke_kanten, aandachtspunten = self._bouw_kompas_structuur(
            hierarchie_rijen=hierarchie_rijen,
            actieve_ids=actieve_ids,
            inwoners_per_buurt=inwoners_per_buurt,
            doel_waarden=doel_waarden,
            onderdrukt_set=onderdrukt_set,
            ref_per_indicator=ref_per_indicator,
            buurt_waarden_in_ref=buurt_waarden_in_ref,
            historie_map=historie_map,
            kleuren_normatief=kleuren_normatief,
            kleuren_neutraal=kleuren_neutraal,
            enkele_buurt_id=enkele_buurt_id,
        )

        meldingen: list[str] = []
        if waterbuurten:
            namen = ", ".join(w["naam"] for w in waterbuurten)
            meldingen.append(f"Waterbuurt(en) uitgesloten van de normatieve weging: {namen}.")
        if contour_kaart["ontbrekende_geometrie_buurten"]:
            namen_geom = ", ".join(b["naam"] for b in contour_kaart["ontbrekende_geometrie_buurten"])
            meldingen.append(
                f"Voor {len(contour_kaart['ontbrekende_geometrie_buurten'])} geselecteerde buurt(en) "
                f"is geen kaartgeometrie beschikbaar ({namen_geom})."
            )

        return {
            "titel": titel,
            "is_meervoudig": len(actieve_ids) > 1,
            "is_waterbuurt": False,
            "totaal_geselecteerd": len(schone_ids),
            "aantal_actieve_buurten": len(actieve_ids),
            "geselecteerde_buurten": [
                {
                    "id": str(r["id"]),
                    "naam": str(r["naam"]),
                    "is_waterbuurt": bool(r.get("is_waterbuurt")),
                    "inwoners": round(inwoners_per_buurt[str(r["id"])]) if str(r["id"]) in inwoners_per_buurt else None,
                }
                for r in geb_rows
            ],
            "waterbuurten_uitgesloten": waterbuurten,
            "gemeente_code": gem_code,
            "gemeente_naam": gem_naam,
            "referentie_modus": ref_modus,
            "referentie_label": referentie_label,
            "n_referentie_buurten": n_ref_totaal,
            "config_id": gekozen_config_id,
            "hero": hero,
            "contour_kaart": contour_kaart,
            "kwadranten": kwadranten,
            "sterke_kanten": sterke_kanten,
            "aandachtspunten": aandachtspunten,
            "klassen_legenda": pk.legenda(kleuren_normatief),
            "klassen_legenda_neutraal": pk.legenda(kleuren_neutraal),
            "meldingen": meldingen,
        }

    # ── Interne hulpfuncties ───────────────────────────────────────────────────

    def _valideer_en_haal_buurten(self, gebied_ids: list[str]) -> list[dict[str, Any]]:
        query = text("""
            SELECT g.id, g.naam, g.gemeente_code, g.gebiedstype_id,
                   gt.code AS gebiedstype_code, gt.naam AS gebiedstype_naam,
                   gem.naam AS gemeente_naam,
                   public.is_waterbuurt(g.naam, g.metadata) AS is_waterbuurt,
                   (g.geom IS NOT NULL) AS heeft_geom
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            LEFT JOIN gemeenten gem ON g.gemeente_code = gem.code
            WHERE g.id = ANY(CAST(:gebied_ids AS varchar[]))
        """)
        rows = [dict(r._mapping) for r in self.db.execute(query, {"gebied_ids": gebied_ids}).fetchall()]
        op_id = {str(r["id"]): r for r in rows}

        ontbrekend = [gid for gid in gebied_ids if gid not in op_id]
        if ontbrekend:
            raise GebruikersFout(f"Gebied(en) niet gevonden: {', '.join(ontbrekend[:5])}.")

        geordend = [op_id[gid] for gid in gebied_ids]
        niet_buurt = [str(r["naam"]) for r in geordend if r.get("gebiedstype_code") != CBS_BUURT_CODE]
        if niet_buurt:
            raise GebruikersFout(
                "De Gebiedsfactsheet ondersteunt uitsluitend buurten (CBS_BUURT). "
                f"Niet-buurt geselecteerd: {', '.join(niet_buurt[:3])}."
            )
        return geordend

    def _haal_gemeente_naam(self, gemeente_code: str | None) -> str | None:
        if not gemeente_code:
            return None
        rij = self.db.execute(
            text("SELECT naam FROM gemeenten WHERE code = :code"),
            {"code": gemeente_code},
        ).fetchone()
        return str(rij[0]) if rij and rij[0] else None

    def _bepaal_referentie_kader(
        self,
        ref_modus: str,
        gebiedstype_id: str,
        gemeente_code: str | None,
        gemeente_naam: str,
    ) -> tuple[str | None, str, int]:
        if ref_modus == "gemeente":
            aantal = (
                self.db.execute(
                    text("""
                        SELECT COUNT(*) FROM gebieden g
                        WHERE g.gebiedstype_id = CAST(:gt AS uuid)
                          AND (CAST(:gm AS varchar) IS NULL OR g.gemeente_code = CAST(:gm AS varchar))
                          AND NOT public.is_waterbuurt(g.naam, g.metadata)
                    """),
                    {"gt": gebiedstype_id, "gm": gemeente_code},
                ).scalar()
                or 0
            )
            return None, f"⌀ Buurtgemiddelde gemeente {gemeente_naam}", int(aantal)

        provincie = (lees_organisatie(self.db) or {}).get("benchmark_provincie") or None
        aantal_prov = (
            self.db.execute(
                text("""
                    SELECT COUNT(*) FROM gebieden g
                    WHERE g.gebiedstype_id = CAST(:gt AS uuid)
                      AND NOT public.is_waterbuurt(g.naam, g.metadata)
                      AND (CAST(:provincie AS varchar) IS NULL OR EXISTS (
                            SELECT 1 FROM gemeenten gm
                            WHERE gm.code = g.gemeente_code AND gm.provincie = CAST(:provincie AS varchar)))
                """),
                {"gt": gebiedstype_id, "provincie": provincie},
            ).scalar()
            or 0
        )
        n_int = int(aantal_prov)
        if provincie:
            return provincie, f"⌀ Buurtgemiddelde provincie {provincie} ({n_int} buurten)", n_int
        return None, f"⌀ Buurtgemiddelde alle buurten ({n_int} buurten)", n_int

    def _bouw_contour_kaart(
        self,
        gemeente_code: str | None,
        gebiedstype_id: str,
        geselecteerde_ids: set[str],
        geb_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ontbrekend_geom = [{"id": str(r["id"]), "naam": str(r["naam"])} for r in geb_rows if not r.get("heeft_geom")]
        query = text("""
            SELECT g.id, g.naam,
                   ST_AsGeoJSON(
                       ST_SimplifyPreserveTopology(ST_Transform(g.geom, 28992), 20)
                   )::json AS geometry
            FROM gebieden g
            WHERE g.gebiedstype_id = CAST(:gebiedstype_id AS uuid)
              AND (CAST(:gemeente_code AS varchar) IS NULL OR g.gemeente_code = CAST(:gemeente_code AS varchar))
              AND g.geom IS NOT NULL
            ORDER BY g.id
        """)
        geom_rijen = [
            dict(r._mapping)
            for r in self.db.execute(
                query,
                {"gebiedstype_id": gebiedstype_id, "gemeente_code": gemeente_code},
            ).fetchall()
        ]
        achtergrond, geselecteerd = geojson_naar_svg_paden(geom_rijen, geselecteerde_ids)
        return {
            "view_box": "0 0 400 320",
            "achtergrond_paden": achtergrond,
            "geselecteerde_paden": geselecteerd,
            "ontbrekende_geometrie_buurten": ontbrekend_geom,
        }

    def _haal_hero_en_gewichten(self, actieve_ids: list[str]) -> tuple[dict[str, Any], dict[str, float]]:
        query = text("""
            SELECT gd.gebied_id, LOWER(TRIM(i.naam)) AS naam_key, gd.waarde, gd.jaar
            FROM (
                SELECT gd_in.gebied_id, gd_in.indicator_uuid, gd_in.waarde, gd_in.jaar, gd_in.n,
                       ROW_NUMBER() OVER (
                           PARTITION BY gd_in.gebied_id, gd_in.indicator_uuid
                           ORDER BY gd_in.jaar DESC
                       ) AS rn
                FROM gebied_data gd_in
                JOIN indicatoren i_in ON i_in.uuid = gd_in.indicator_uuid
                WHERE gd_in.gebied_id = ANY(CAST(:gebied_ids AS varchar[]))
                  AND LOWER(TRIM(i_in.naam)) = ANY(CAST(:namen AS text[]))
                  AND i_in.is_actief = TRUE
                  AND i_in.vervangen_door_id IS NULL
                  AND COALESCE(gd_in.scenario_id, 'current') = :scenario_id
                  AND gd_in.jaar IS NOT NULL
                  AND gd_in.waarde IS NOT NULL
            ) gd
            JOIN indicatoren i ON i.uuid = gd.indicator_uuid
            WHERE gd.rn = 1 AND NOT public.is_kleine_aantallen(gd.n)
        """)
        rows = [
            dict(r._mapping)
            for r in self.db.execute(
                query,
                {
                    "gebied_ids": actieve_ids,
                    "namen": list(HERO_INDICATOR_NAMEN),
                    "scenario_id": SCENARIO_STANDAARD,
                },
            ).fetchall()
        ]

        per_naam: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            per_naam[str(r["naam_key"])].append(r)

        inwoners_per_buurt: dict[str, float] = {}
        for r in per_naam.get("inwoners", []):
            val = float(r["waarde"])
            if val >= 0:
                inwoners_per_buurt[str(r["gebied_id"])] = val

        def _som_kpi(kandidaten: tuple[str, ...]) -> dict[str, Any] | None:
            for sleutel in kandidaten:
                items = per_naam.get(sleutel)
                if items:
                    totaal = sum(float(x["waarde"]) for x in items)
                    jaren = [int(x["jaar"]) for x in items]
                    return {
                        "waarde": int(round(totaal)),
                        "jaar": max(jaren),
                        "aantal_buurten_met_data": len(items),
                    }
            return None

        inwoners_kpi = _som_kpi(("inwoners",))
        huishoudens_kpi = _som_kpi(("huishoudens totaal", "huishoudens (bag woonfunctie)"))
        woningen_kpi = _som_kpi(("woningvoorraad", "woonfunctie"))

        bag_tellingen: list[tuple[str, float, int | None]] = []
        bag_jaren: list[int] = []
        for naam_key, label in BAG_BOUWPERIODES:
            items = per_naam.get(naam_key, [])
            som = sum(float(x["waarde"]) for x in items) if items else 0.0
            jaar_max = max((int(x["jaar"]) for x in items), default=None)
            if jaar_max is not None:
                bag_jaren.append(jaar_max)
            bag_tellingen.append((label, max(0.0, som), jaar_max))

        totaal_bag = sum(aantal for _, aantal, _ in bag_tellingen)
        bouwperiodes = []
        if totaal_bag > 0:
            for label, aantal, _ in bag_tellingen:
                bouwperiodes.append(
                    {
                        "label": label,
                        "aantal": int(round(aantal)),
                        "percentage": round(aantal / totaal_bag * 100.0, 1),
                    }
                )

        hero = {
            "inwoners": inwoners_kpi,
            "huishoudens": huishoudens_kpi,
            "woningen": woningen_kpi,
            "bouwperiodes": bouwperiodes,
            "bouwperiodes_jaar": max(bag_jaren) if bag_jaren and totaal_bag > 0 else None,
        }
        return hero, inwoners_per_buurt

    def _haal_kompas_hierarchie(self, config_id: int) -> list[dict[str, Any]]:
        query = text("""
            SELECT
                kt.id AS kwadrant_id,
                kt.naam AS kwadrant_naam,
                kt.kleur AS kwadrant_kleur,
                kt.volgorde AS kwadrant_volgorde,
                kth.id AS thema_id,
                kth.naam AS thema_naam,
                kth.volgorde AS thema_volgorde,
                ko.id AS onderdeel_id,
                ko.naam AS onderdeel_naam,
                ko.volgorde AS onderdeel_volgorde,
                i.uuid::text AS indicator_uuid,
                i.naam AS indicator_naam,
                COALESCE(sr.eenheid, i.eenheid) AS eenheid,
                i.polariteit,
                COALESCE(sr.score_type, i.score_type) AS score_type,
                sr.inverse,
                COALESCE(kim.weging, 1.0) AS weging,
                i.omschrijving,
                i.bron
            FROM kompas_configuraties kc
            JOIN kompas_titels kt ON kt.config_id = kc.id
            JOIN kompas_themas kth ON kth.titel_id = kt.id
            JOIN kompas_onderdelen ko ON ko.thema_id = kth.id
            JOIN kompas_indicator_mapping kim ON kim.onderdeel_id = ko.id AND kim.config_id = kc.id
            JOIN indicatoren i ON i.uuid = kim.indicator_uuid
            LEFT JOIN kompas_indicator_scoring_regels sr
                ON sr.indicator_uuid = i.uuid AND sr.config_id = kc.id
            WHERE kc.id = :config_id
              AND kc.is_actief = TRUE
              AND i.is_actief = TRUE
              AND i.vervangen_door_id IS NULL
            ORDER BY kt.volgorde, kth.volgorde, ko.volgorde, i.naam
        """)
        rows = [dict(r._mapping) for r in self.db.execute(query, {"config_id": config_id}).fetchall()]
        # Ontdubbel per (thema_id, indicator_uuid) (#491)
        gezien: set[tuple[int, str]] = set()
        uniek: list[dict[str, Any]] = []
        for r in rows:
            sleutel = (int(r["thema_id"]), str(r["indicator_uuid"]))
            if sleutel in gezien:
                continue
            gezien.add(sleutel)
            uniek.append(r)
        return uniek

    def _haal_doel_waarden(
        self, actieve_ids: list[str], indicator_uuids: list[str]
    ) -> tuple[dict[tuple[str, str], tuple[float, int]], set[tuple[str, str, int]]]:
        if not actieve_ids or not indicator_uuids:
            return {}, set()
        query = text("""
            SELECT gd.gebied_id, gd.indicator_uuid::text AS indicator_uuid, gd.waarde, gd.jaar
            FROM (
                SELECT gebied_id, indicator_uuid, waarde, jaar,
                       ROW_NUMBER() OVER (
                           PARTITION BY gebied_id, indicator_uuid
                           ORDER BY jaar DESC
                       ) AS rn
                FROM gebied_data
                WHERE gebied_id = ANY(CAST(:gebied_ids AS varchar[]))
                  AND indicator_uuid = ANY(CAST(:indicator_uuids AS uuid[]))
                  AND COALESCE(scenario_id, 'current') = :scenario_id
                  AND jaar IS NOT NULL
                  AND waarde IS NOT NULL
            ) gd
            WHERE gd.rn = 1
        """)
        rows = self.db.execute(
            query,
            {
                "gebied_ids": actieve_ids,
                "indicator_uuids": indicator_uuids,
                "scenario_id": SCENARIO_STANDAARD,
            },
        ).fetchall()
        onderdrukt = pk.onderdrukte_waarden(self.db, actieve_ids, indicator_uuids)
        doel: dict[tuple[str, str], tuple[float, int]] = {}
        for r in rows:
            gid = str(r.gebied_id)
            uid = str(r.indicator_uuid)
            jaar = int(r.jaar)
            if (gid, uid, jaar) in onderdrukt:
                continue
            doel[(gid, uid)] = (float(r.waarde), jaar)
        return doel, onderdrukt

    def _haal_referentie_data(
        self,
        gebiedstype_id: str,
        gemeente_code: str | None,
        provincie: str | None,
        indicator_uuids: list[str],
    ) -> tuple[dict[str, list[float]], dict[tuple[str, str], float]]:
        if not indicator_uuids:
            return {}, {}
        params = referentie_params(
            gebiedstype_id=gebiedstype_id,
            gemeente_code=gemeente_code,
            indicator_uuids=indicator_uuids,
            provincie=provincie,
        )
        query = text(f"""
            SELECT rw.gebied_id, rw.indicator_uuid::text AS indicator_uuid, rw.waarde
            FROM {SQL_REFERENTIE_WAARDEN} rw
            WHERE rw.waarde IS NOT NULL
        """)
        ref_per_ind: dict[str, list[float]] = defaultdict(list)
        buurt_map: dict[tuple[str, str], float] = {}
        for r in self.db.execute(query, params).fetchall():
            uid = str(r.indicator_uuid)
            val = float(r.waarde)
            ref_per_ind[uid].append(val)
            buurt_map[(str(r.gebied_id), uid)] = val
        return dict(ref_per_ind), buurt_map

    def _haal_historie(
        self,
        actieve_ids: list[str],
        indicator_uuids: list[str],
        inwoners_per_buurt: dict[str, float],
    ) -> dict[str, dict[int, list[tuple[str, float]]]]:
        if not actieve_ids or not indicator_uuids:
            return {}
        query = text("""
            SELECT gd.gebied_id, gd.indicator_uuid::text AS indicator_uuid, gd.jaar, gd.waarde
            FROM gebied_data gd
            WHERE gd.gebied_id = ANY(CAST(:gebied_ids AS varchar[]))
              AND gd.indicator_uuid = ANY(CAST(:indicator_uuids AS uuid[]))
              AND COALESCE(gd.scenario_id, 'current') = :scenario_id
              AND gd.jaar IS NOT NULL
              AND gd.waarde IS NOT NULL
              AND NOT public.is_kleine_aantallen(gd.n)
            ORDER BY gd.indicator_uuid, gd.jaar ASC
        """)
        uit: dict[str, dict[int, list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
        for r in self.db.execute(
            query,
            {
                "gebied_ids": actieve_ids,
                "indicator_uuids": indicator_uuids,
                "scenario_id": SCENARIO_STANDAARD,
            },
        ).fetchall():
            uit[str(r.indicator_uuid)][int(r.jaar)].append((str(r.gebied_id), float(r.waarde)))
        return uit

    def _aggregeer_tijdreeks(
        self,
        per_jaar: dict[int, list[tuple[str, float]]],
        inwoners_per_buurt: dict[str, float],
        is_aantal: bool,
        n_huidige_buurten: int,
        is_meervoudig: bool,
    ) -> list[dict[str, Any]]:
        if not per_jaar:
            return []
        min_buurten = (
            n_huidige_buurten
            if (is_meervoudig and is_aantal)
            else (max(1, math.ceil(0.5 * n_huidige_buurten)) if is_meervoudig else 1)
        )
        reeks: list[dict[str, Any]] = []
        for jaar in sorted(per_jaar.keys()):
            pts = per_jaar[jaar]
            if len(pts) < min_buurten:
                continue
            if is_aantal:
                waarde = sum(v for _, v in pts)
            elif not is_meervoudig:
                waarde = pts[0][1]
            else:
                w_som = 0.0
                vw_som = 0.0
                for gid, v in pts:
                    gew = inwoners_per_buurt.get(gid, 0.0)
                    if gew > 0:
                        vw_som += v * gew
                        w_som += gew
                waarde = (vw_som / w_som) if w_som > 0 else (sum(v for _, v in pts) / len(pts))
            reeks.append({"jaar": jaar, "waarde": round(waarde, 2)})
        return reeks[-8:]

    def _bouw_kompas_structuur(
        self,
        hierarchie_rijen: list[dict[str, Any]],
        actieve_ids: list[str],
        inwoners_per_buurt: dict[str, float],
        doel_waarden: dict[tuple[str, str], tuple[float, int]],
        onderdrukt_set: set[tuple[str, str, int]],
        ref_per_indicator: dict[str, list[float]],
        buurt_waarden_in_ref: dict[tuple[str, str], float],
        historie_map: dict[str, dict[int, list[tuple[str, float]]]],
        kleuren_normatief: list[str],
        kleuren_neutraal: list[str],
        enkele_buurt_id: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        is_meervoudig = len(actieve_ids) > 1
        onderdrukt_paren = {(gid, uid) for gid, uid, _ in onderdrukt_set}

        # Boomopbouw met behoud van volgorde: kwadrant -> thema -> onderdeel -> indicatoren
        kw_map: dict[int, dict[str, Any]] = {}
        for r in hierarchie_rijen:
            kw_id = int(r["kwadrant_id"])
            th_id = int(r["thema_id"])
            ond_id = int(r["onderdeel_id"])
            kw_naam = str(r["kwadrant_naam"])
            is_neutraal_kw = pk.is_neutraal_kwadrant(kw_naam)

            if kw_id not in kw_map:
                kw_map[kw_id] = {
                    "kwadrant_id": kw_id,
                    "kwadrant_naam": kw_naam,
                    "kwadrant_kleur": r.get("kwadrant_kleur") or "#0ea5e9",
                    "is_neutraal": is_neutraal_kw,
                    "_themas": {},
                }
            th_dict = kw_map[kw_id]["_themas"]
            if th_id not in th_dict:
                th_dict[th_id] = {
                    "thema_id": th_id,
                    "thema_naam": str(r["thema_naam"]),
                    "is_neutraal": is_neutraal_kw,
                    "_onderdelen": {},
                }
            ond_dict = th_dict[th_id]["_onderdelen"]
            if ond_id not in ond_dict:
                ond_dict[ond_id] = {
                    "onderdeel_id": ond_id,
                    "onderdeel_naam": str(r["onderdeel_naam"]),
                    "is_neutraal": is_neutraal_kw,
                    "_rijen": [],
                }
            ond_dict[ond_id]["_rijen"].append(r)

        alle_landbuurten_in_ref = sorted({gid for gid, _ in buurt_waarden_in_ref})
        kwadranten_uit: list[dict[str, Any]] = []
        kandidaat_onderdelen: list[dict[str, Any]] = []

        for kw in kw_map.values():
            is_neutraal_kw = bool(kw["is_neutraal"])
            palet_kw = kleuren_neutraal if is_neutraal_kw else kleuren_normatief
            themas_uit: list[dict[str, Any]] = []
            kw_paren: list[tuple[int | None, float]] = []

            for th in kw["_themas"].values():
                onderdelen_uit: list[dict[str, Any]] = []
                th_paren: list[tuple[int | None, float]] = []
                # Voor gemeentelijke themarangorde (1 buurt): lijst van (uid, hoger_beter, gewicht)
                th_rang_indicatoren: list[tuple[str, bool, float]] = []

                for ond in th["_onderdelen"].values():
                    ind_items: list[dict[str, Any]] = []
                    ond_paren: list[tuple[int | None, float]] = []

                    for r in ond["_rijen"]:
                        uid = str(r["indicator_uuid"])
                        naam = str(r["indicator_naam"])
                        eenheid = r.get("eenheid") or ""
                        weging = float(r.get("weging") or 1.0)
                        pol_richting = bepaal_polariteit(
                            r.get("polariteit"), r.get("score_type"), r.get("inverse"), kw["kwadrant_naam"]
                        )
                        ind_is_neutraal = is_neutraal_kw or pol_richting == "neutraal"
                        hoger_beter = True if ind_is_neutraal else (pol_richting == "hoger_is_beter")
                        ind_palet = kleuren_neutraal if ind_is_neutraal else kleuren_normatief
                        is_aantal = is_aantal_indicator(eenheid, naam)

                        ref_lijst = ref_per_indicator.get(uid, [])
                        n_ref = len(ref_lijst)
                        ref_gem = (sum(ref_lijst) / n_ref) if n_ref > 0 else None

                        if not ind_is_neutraal and not is_aantal and n_ref >= MIN_REFERENTIE_BUURTEN:
                            th_rang_indicatoren.append((uid, hoger_beter, n_ref * weging))

                        buurt_treffers = [
                            (gid, doel_waarden[(gid, uid)][0], doel_waarden[(gid, uid)][1])
                            for gid in actieve_ids
                            if (gid, uid) in doel_waarden
                        ]
                        n_onderdrukt = sum(1 for gid in actieve_ids if (gid, uid) in onderdrukt_paren)

                        historie = self._aggregeer_tijdreeks(
                            per_jaar=historie_map.get(uid, {}),
                            inwoners_per_buurt=inwoners_per_buurt,
                            is_aantal=is_aantal,
                            n_huidige_buurten=max(1, len(buurt_treffers)),
                            is_meervoudig=is_meervoudig,
                        )
                        trend = bereken_trend(historie, pol_richting, eenheid, is_aantal=is_aantal)

                        if not buurt_treffers:
                            status = "onderdrukt" if n_onderdrukt > 0 else "geen_data"
                            ind_items.append(
                                {
                                    "indicator_uuid": uid,
                                    "naam": naam,
                                    "eenheid": eenheid,
                                    "polariteit": pol_richting,
                                    "is_aantal": is_aantal,
                                    "is_neutraal": ind_is_neutraal,
                                    "status": status,
                                    "jaar": None,
                                    "waarde": None,
                                    "waarde_per_buurt": None,
                                    "ref_gemiddelde": round(ref_gem, 2) if ref_gem is not None else None,
                                    "verschil": None,
                                    "n_referentie": n_ref,
                                    "klasse": None,
                                    "score": None,
                                    "klasse_kleur": GEEN_DATA_KLEUR,
                                    "duiding": (
                                        "Afgeschermd (kleine aantallen)" if status == "onderdrukt" else "Geen data"
                                    ),
                                    "historie": [],
                                    "trend": None,
                                    "bron": r.get("bron") or "",
                                }
                            )
                            continue

                        peiljaar = max(j for _, _, j in buurt_treffers)
                        if is_aantal:
                            som_waarde = sum(v for _, v, _ in buurt_treffers)
                            gem_per_buurt = som_waarde / len(buurt_treffers)
                            verschil_aantal = (
                                round(som_waarde - ref_gem, 2) if (not is_meervoudig and ref_gem is not None) else None
                            )
                            ind_items.append(
                                {
                                    "indicator_uuid": uid,
                                    "naam": naam,
                                    "eenheid": eenheid or "aantal",
                                    "polariteit": "neutraal",
                                    "is_aantal": True,
                                    "is_neutraal": True,
                                    "status": "context_aantal",
                                    "jaar": peiljaar,
                                    "waarde": round(som_waarde, 2),
                                    "waarde_per_buurt": round(gem_per_buurt, 2) if is_meervoudig else None,
                                    "ref_gemiddelde": round(ref_gem, 2) if ref_gem is not None else None,
                                    "verschil": verschil_aantal,
                                    "n_referentie": n_ref,
                                    "klasse": None,
                                    "score": None,
                                    "klasse_kleur": GEEN_DATA_KLEUR,
                                    "duiding": "Context (aantal)",
                                    "historie": historie,
                                    "trend": trend,
                                    "bron": r.get("bron") or "",
                                }
                            )
                            continue

                        # Relatieve indicator: inwonersgewogen gemiddelde voor weergave
                        if not is_meervoudig:
                            weergave_waarde = buurt_treffers[0][1]
                        else:
                            w_som = 0.0
                            vw_som = 0.0
                            for gid, v, _ in buurt_treffers:
                                gew = inwoners_per_buurt.get(gid, 0.0)
                                if gew > 0:
                                    vw_som += v * gew
                                    w_som += gew
                            weergave_waarde = (
                                (vw_som / w_som)
                                if w_som > 0
                                else (sum(v for _, v, _ in buurt_treffers) / len(buurt_treffers))
                            )

                        if n_ref < MIN_REFERENTIE_BUURTEN:
                            ind_items.append(
                                {
                                    "indicator_uuid": uid,
                                    "naam": naam,
                                    "eenheid": eenheid,
                                    "polariteit": pol_richting,
                                    "is_aantal": False,
                                    "is_neutraal": ind_is_neutraal,
                                    "status": "geen_referentie",
                                    "jaar": peiljaar,
                                    "waarde": round(weergave_waarde, 2),
                                    "waarde_per_buurt": None,
                                    "ref_gemiddelde": round(ref_gem, 2) if ref_gem is not None else None,
                                    "verschil": None,
                                    "n_referentie": n_ref,
                                    "klasse": None,
                                    "score": None,
                                    "klasse_kleur": GEEN_DATA_KLEUR,
                                    "duiding": "Geen referentie",
                                    "historie": historie,
                                    "trend": trend,
                                    "bron": r.get("bron") or "",
                                }
                            )
                            continue

                        # Percentielklasse per (buurt, indicator)-paar conform percentielklasse.py
                        ind_paren: list[tuple[int | None, float]] = []
                        for _, v, _ in buurt_treffers:
                            k_buurt = pk.klasse(v, ref_lijst, hoger_beter=hoger_beter)
                            ind_paren.append((k_buurt, n_ref * weging))

                        ind_score = pk.gemiddelde_score(ind_paren)
                        ind_klasse = pk.rond_klasse(ind_score) if ind_score is not None else None
                        ind_kleur = ind_palet[ind_klasse - 1] if ind_klasse else GEEN_DATA_KLEUR
                        verschil = (weergave_waarde - ref_gem) if ref_gem is not None else None

                        # Alleen niet-neutrale indicatoren wegen mee in een normatief kwadrant;
                        # binnen Samenstelling (is_neutraal_kw) wegen ze wél mee voor de neutrale balk.
                        if is_neutraal_kw or not ind_is_neutraal:
                            ond_paren.extend(ind_paren)
                            th_paren.extend(ind_paren)
                            kw_paren.extend(ind_paren)

                        ind_items.append(
                            {
                                "indicator_uuid": uid,
                                "naam": naam,
                                "eenheid": eenheid,
                                "polariteit": pol_richting,
                                "is_aantal": False,
                                "is_neutraal": ind_is_neutraal,
                                "status": "ok",
                                "jaar": peiljaar,
                                "waarde": round(weergave_waarde, 2),
                                "waarde_per_buurt": None,
                                "ref_gemiddelde": round(ref_gem, 2) if ref_gem is not None else None,
                                "verschil": round(verschil, 2) if verschil is not None else None,
                                "n_referentie": n_ref,
                                "klasse": ind_klasse,
                                "score": round(ind_score, 2) if ind_score is not None else None,
                                "klasse_kleur": ind_kleur,
                                "duiding": klasse_duiding(ind_klasse, neutraal=ind_is_neutraal),
                                "historie": historie,
                                "trend": trend,
                                "bron": r.get("bron") or "",
                            }
                        )

                    ond_score = pk.gemiddelde_score(ond_paren)
                    ond_klasse = pk.rond_klasse(ond_score) if ond_score is not None else None
                    ond_kleur = palet_kw[ond_klasse - 1] if ond_klasse else GEEN_DATA_KLEUR
                    n_ond_met_score = sum(1 for i in ind_items if i["status"] == "ok" and i["klasse"] is not None)

                    ond_uit = {
                        "onderdeel_id": ond["onderdeel_id"],
                        "onderdeel_naam": ond["onderdeel_naam"],
                        "is_neutraal": is_neutraal_kw,
                        "klasse": ond_klasse,
                        "score": round(ond_score, 2) if ond_score is not None else None,
                        "klasse_kleur": ond_kleur,
                        "duiding": klasse_duiding(ond_klasse, neutraal=is_neutraal_kw),
                        "aantal_indicatoren_met_score": n_ond_met_score,
                        "indicatoren": ind_items,
                    }
                    onderdelen_uit.append(ond_uit)

                    if not is_neutraal_kw and ond_score is not None and ond_klasse is not None:
                        norm_inds = [
                            i
                            for i in ind_items
                            if i["status"] == "ok" and not i["is_neutraal"] and i["score"] is not None
                        ]
                        kandidaat_onderdelen.append(
                            {
                                "onderdeel_id": ond["onderdeel_id"],
                                "onderdeel_naam": ond["onderdeel_naam"],
                                "thema_id": th["thema_id"],
                                "thema_naam": th["thema_naam"],
                                "kwadrant_naam": kw["kwadrant_naam"],
                                "klasse": ond_klasse,
                                "score": ond_score,
                                "klasse_kleur": ond_kleur,
                                "duiding": klasse_duiding(ond_klasse, neutraal=False),
                                "aantal_indicatoren_met_score": n_ond_met_score,
                                "_norm_indicatoren": norm_inds,
                            }
                        )

                th_score = pk.gemiddelde_score(th_paren)
                th_klasse = pk.rond_klasse(th_score) if th_score is not None else None
                th_kleur = palet_kw[th_klasse - 1] if th_klasse else GEEN_DATA_KLEUR

                n_th_beschikbaar = len(th_rang_indicatoren)
                n_th_eigen = sum(
                    1
                    for ond_u in onderdelen_uit
                    for ind_u in ond_u["indicatoren"]
                    if ind_u["status"] == "ok" and (is_neutraal_kw or not ind_u["is_neutraal"])
                )

                rang_obj = None
                if enkele_buurt_id is not None and not is_neutraal_kw and th_score is not None and n_th_beschikbaar > 0:
                    rang_obj = self._bereken_thema_rang(
                        enkele_buurt_id=enkele_buurt_id,
                        eigen_score=th_score,
                        eigen_dekking=n_th_eigen,
                        th_rang_indicatoren=th_rang_indicatoren,
                        alle_landbuurten=alle_landbuurten_in_ref,
                        ref_per_indicator=ref_per_indicator,
                        buurt_waarden_in_ref=buurt_waarden_in_ref,
                    )

                themas_uit.append(
                    {
                        "thema_id": th["thema_id"],
                        "thema_naam": th["thema_naam"],
                        "is_neutraal": is_neutraal_kw,
                        "klasse": th_klasse,
                        "score": round(th_score, 2) if th_score is not None else None,
                        "klasse_kleur": th_kleur,
                        "duiding": klasse_duiding(th_klasse, neutraal=is_neutraal_kw),
                        "aantal_indicatoren_met_score": n_th_eigen,
                        "aantal_indicatoren_totaal": sum(len(o["indicatoren"]) for o in onderdelen_uit),
                        "rang": rang_obj,
                        "onderdelen": onderdelen_uit,
                    }
                )

            kw_score = pk.gemiddelde_score(kw_paren)
            kw_klasse = pk.rond_klasse(kw_score) if kw_score is not None else None
            kwadranten_uit.append(
                {
                    "kwadrant_id": kw["kwadrant_id"],
                    "kwadrant_naam": kw["kwadrant_naam"],
                    "kwadrant_kleur": kw["kwadrant_kleur"],
                    "is_neutraal": is_neutraal_kw,
                    "klasse": kw_klasse,
                    "score": round(kw_score, 2) if kw_score is not None else None,
                    "klasse_kleur": palet_kw[kw_klasse - 1] if kw_klasse else GEEN_DATA_KLEUR,
                    "duiding": klasse_duiding(kw_klasse, neutraal=is_neutraal_kw),
                    "themas": themas_uit,
                }
            )

        sterke_kanten = self._selecteer_top_onderdelen(kandidaat_onderdelen, sterk=True)
        aandachtspunten = self._selecteer_top_onderdelen(kandidaat_onderdelen, sterk=False)
        return kwadranten_uit, sterke_kanten, aandachtspunten

    def _bereken_thema_rang(
        self,
        enkele_buurt_id: str,
        eigen_score: float,
        eigen_dekking: int,
        th_rang_indicatoren: list[tuple[str, bool, float]],
        alle_landbuurten: list[str],
        ref_per_indicator: dict[str, list[float]],
        buurt_waarden_in_ref: dict[tuple[str, str], float],
    ) -> dict[str, Any] | None:
        min_dekking = max(1, math.ceil(THEMA_RANG_DEKKING_FRACTIE * len(th_rang_indicatoren)))
        if eigen_dekking < min_dekking:
            return None

        scores: list[float] = [eigen_score]
        for bid in alle_landbuurten:
            if bid == enkele_buurt_id:
                continue
            paren_b: list[tuple[int | None, float]] = []
            for uid, hoger_beter, gewicht in th_rang_indicatoren:
                val = buurt_waarden_in_ref.get((bid, uid))
                if val is None:
                    continue
                k = pk.klasse(val, ref_per_indicator[uid], hoger_beter=hoger_beter)
                if k is not None:
                    paren_b.append((k, gewicht))
            if len(paren_b) >= min_dekking:
                sc_b = pk.gemiddelde_score(paren_b)
                if sc_b is not None:
                    scores.append(sc_b)

        if len(scores) < MIN_REFERENTIE_BUURTEN:
            return None
        positie = 1 + sum(1 for sc in scores if sc > eigen_score + 1e-9)
        return {
            "positie": positie,
            "totaal_met_score": len(scores),
            "min_indicatoren_vereist": min_dekking,
        }

    def _selecteer_top_onderdelen(
        self, kandidaten: list[dict[str, Any]], sterk: bool, limiet: int = 3
    ) -> list[dict[str, Any]]:
        if sterk:
            gefilterd = [k for k in kandidaten if k["klasse"] >= 6]
            gefilterd.sort(key=lambda k: (-float(k["score"]), k["onderdeel_naam"]))
        else:
            gefilterd = [k for k in kandidaten if k["klasse"] <= 3]
            gefilterd.sort(key=lambda k: (float(k["score"]), k["onderdeel_naam"]))

        uit: list[dict[str, Any]] = []
        for item in gefilterd[:limiet]:
            inds = item.get("_norm_indicatoren") or []
            voorbeeld = None
            if inds:
                if sterk:
                    beste = max(inds, key=lambda i: (float(i["score"]), int(i["n_referentie"])))
                else:
                    beste = min(inds, key=lambda i: (float(i["score"]), -int(i["n_referentie"])))
                voorbeeld = {
                    "naam": beste["naam"],
                    "waarde": beste["waarde"],
                    "ref_gemiddelde": beste["ref_gemiddelde"],
                    "eenheid": beste["eenheid"],
                    "jaar": beste["jaar"],
                    "klasse": beste["klasse"],
                }
            uit.append(
                {
                    "onderdeel_id": item["onderdeel_id"],
                    "onderdeel_naam": item["onderdeel_naam"],
                    "thema_id": item["thema_id"],
                    "thema_naam": item["thema_naam"],
                    "kwadrant_naam": item["kwadrant_naam"],
                    "klasse": item["klasse"],
                    "score": round(float(item["score"]), 2),
                    "klasse_kleur": item["klasse_kleur"],
                    "duiding": item["duiding"],
                    "aantal_indicatoren_met_score": item["aantal_indicatoren_met_score"],
                    "voorbeeld_indicator": voorbeeld,
                }
            )
        return uit
