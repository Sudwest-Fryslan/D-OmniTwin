"""
Kompas Service Layer
Business logic voor multi-kompas configuratie systeem
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin import polariteit
from omnitwin.services import labelklasse as lk
from omnitwin.services import percentielklasse as pk
from omnitwin.services.color_scale_service import ColorScaleService
from omnitwin.services.zscore_referentie import (
    CBS_BUURT_CODE,
    SCENARIO_STANDAARD,
    SQL_REFERENTIE_STATS,
    SQL_REFERENTIE_WAARDEN,
    SQL_ZSCORE_GEBIEDEN,
    referentie_params,
)

GEEN_DATA_KLEUR = "#94A3B8"  # zelfde grijs als elders in het Kompas


class KompasService:
    """Service voor Kompas hiërarchie en data queries"""

    def __init__(self, db: Session):
        self.db = db
        self.scoring = KompasScoringService()

    def get_configuraties(self) -> list[dict[str, Any]]:
        """
        Haal alle actieve configuraties op met statistieken

        Returns: List van configuratie dicts met counts
        """
        query = text("""
            SELECT
                s.id, s.naam, s.beschrijving, s.is_standaard, s.is_actief, s.icoon,
                s.aantal_themas, s.aantal_onderdelen, s.aantal_indicatoren, s.aantal_scoring_regels,
                kc.classificatie
            FROM v_kompas_config_stats s
            JOIN kompas_configuraties kc ON kc.id = s.id
            ORDER BY s.is_standaard DESC, s.naam
        """)

        result = self.db.execute(query)
        return [dict(row._mapping) for row in result]

    def get_standaard_config_id(self) -> int:
        """Haal ID op van standaard configuratie"""
        query = text("""
            SELECT id FROM kompas_configuraties
            WHERE is_standaard = TRUE AND is_actief = TRUE
            LIMIT 1
        """)

        result = self.db.execute(query).fetchone()
        return result[0] if result else 1

    def get_classificatie(self, config_id: int) -> str:
        """Classificatie van een kompasprofiel: zscore (standaard), percentiel_8 (#255) of label_ae (#256)."""
        row = self.db.execute(
            text("SELECT classificatie FROM kompas_configuraties WHERE id = :config_id"),
            {"config_id": config_id},
        ).fetchone()
        return pk.normaliseer_classificatie(row[0] if row else None)

    def get_hierarchie(self, config_id: int) -> dict[str, Any]:
        """
        Build complete hiërarchie tree voor D3.js sunburst

        Args:
            config_id: ID van kompas configuratie

        Returns: Dict met config info + hierarchie tree
        """
        # Haal config info op
        config_query = text("""
            SELECT id, naam, icoon
            FROM kompas_configuraties
            WHERE id = :config_id AND is_actief = TRUE
        """)
        config_row = self.db.execute(config_query, {"config_id": config_id}).fetchone()

        if not config_row:
            return None

        # Haal hiërarchie data op
        hierarchy_query = text("""
            SELECT
                titel_id, titel_naam, titel_kleur,
                thema_id, thema_naam,
                onderdeel_id, onderdeel_naam,
                indicator_uuid, indicator_naam,
                is_actueel, weging
            FROM v_kompas_hierarchie
            WHERE config_id = :config_id
            ORDER BY titel_id, thema_id, onderdeel_id, indicator_naam
        """)

        rows = self.db.execute(hierarchy_query, {"config_id": config_id}).fetchall()

        # Build tree
        tree = self._build_tree_from_rows(rows)

        # Count total indicators
        indicator_count = len([r for r in rows if r.indicator_uuid])

        return {
            "config_id": config_row.id,
            "config_naam": config_row.naam,
            "config_icoon": config_row.icoon,
            "hierarchie": tree,
            "total_indicators": indicator_count,
            "last_updated": datetime.now(),
        }

    def get_gebied_kompas(self, config_id: int, gebied_id: str) -> dict[str, Any] | None:
        """
        Haal kompas data voor één gebied op (met waarden + kleuren)

        Args:
            config_id: ID van kompas configuratie
            gebied_id: UUID van gebied

        Returns: Dict met hierarchie + waarden ingevuld
        """
        # Check of gebied bestaat
        gebied_query = text("""
            SELECT id, naam, gebiedstype_id, gemeente_code,
                   public.is_waterbuurt(naam, metadata) AS is_waterbuurt
            FROM gebieden WHERE id = :gebied_id LIMIT 1
        """)
        gebied_row = self.db.execute(gebied_query, {"gebied_id": gebied_id}).fetchone()

        if not gebied_row:
            return None

        # Haal basis hiërarchie op
        hierarchie_data = self.get_hierarchie(config_id)
        if not hierarchie_data:
            return None

        # Haal ALLE indicatoren op die in dit kompas zitten
        # LEFT JOIN LATERAL voor meest recente jaar (MAX) per indicator
        data_query = text("""
            SELECT
                i.uuid as indicator_uuid,
                i.naam as indicator_naam,
                i.ontologische_beschrijving,
                gd.waarde,
                gd.jaar,
                COALESCE(sr.score_type, i.score_type) as score_type,
                sr.inverse,
                sr.thresholds,
                COALESCE(sr.eenheid, i.eenheid) AS eenheid
            FROM kompas_indicator_mapping kim
            JOIN indicatoren i ON kim.indicator_uuid = i.uuid
            LEFT JOIN LATERAL (
                -- kleine aantallen (#325): een waarde op te weinig waarnemingen telt als geen data
                SELECT CASE WHEN is_kleine_aantallen(n) THEN NULL ELSE waarde END AS waarde, jaar
                FROM gebied_data
                WHERE indicator_uuid = i.uuid
                  AND gebied_id = :gebied_id
                  AND COALESCE(scenario_id, 'current') = :scenario_id
                  AND jaar IS NOT NULL
                ORDER BY jaar DESC
                LIMIT 1
            ) gd ON true
            LEFT JOIN kompas_indicator_scoring_regels sr
                ON i.uuid = sr.indicator_uuid
                AND sr.config_id = :config_id
            WHERE kim.config_id = :config_id AND i.is_actief = true
        """)

        data_rows = self.db.execute(
            data_query, {"config_id": config_id, "gebied_id": gebied_id, "scenario_id": SCENARIO_STANDAARD}
        ).fetchall()

        # Converteer naar dict voor makkelijke lookup
        # Indicatoren zonder data krijgen None als waarde
        data_map = {}
        for row in data_rows:
            # FIX: Check of thresholds al een list is of nog een string
            thresholds = None
            if row.thresholds:
                if isinstance(row.thresholds, str):
                    thresholds = json.loads(row.thresholds)
                else:
                    thresholds = row.thresholds

            data_map[str(row.indicator_uuid)] = {
                "waarde": float(row.waarde) if row.waarde is not None else None,
                "score_type": row.score_type,
                "inverse": row.inverse,
                "thresholds": thresholds,
                "eenheid": row.eenheid,
                "ontologische_beschrijving": row.ontologische_beschrijving,
            }

        # Percentiel-drempels per indicator binnen de referentiegroep van dit gebied (#66).
        # Een waterbuurt wordt niet met de referentiegroep vergeleken (#155): geen
        # drempels, dus grijze kleuring, en een melding.
        melding = None
        if gebied_row.is_waterbuurt:
            bulk_thresholds = {}
            melding = (
                "Dit gebied is een waterbuurt. Waterbuurten worden niet vergeleken "
                "met de referentiegroep; de kleuring vervalt."
            )
        else:
            bulk_thresholds = self._get_bulk_percentiles(gebied_row.gebiedstype_id, gebied_row.gemeente_code)

        # Enrich hierarchie met waarden en kleuren
        enriched_tree = self._enrich_tree_with_values(
            hierarchie_data["hierarchie"], data_map, bulk_thresholds=bulk_thresholds
        )

        # Bereken coverage
        total_indicators = hierarchie_data["total_indicators"]
        coverage_pct = (len(data_map) / total_indicators * 100) if total_indicators > 0 else 0

        # #255: percentielklassen per indicator en geaggregeerd per onderdeel/thema/kwadrant
        classificatie = self.get_classificatie(config_id)
        klassen_legenda = None
        label_melding = None
        if classificatie == "percentiel_8":
            enriched_tree, klassen_legenda = self._percentielklassen_in_boom(config_id, [gebied_id], enriched_tree)
        elif classificatie == lk.CLASSIFICATIE:
            enriched_tree, klassen_legenda, label_melding = self._labels_in_boom(config_id, [gebied_id], enriched_tree)

        return {
            "gebied_id": gebied_id,
            "gebied_naam": gebied_row.naam,
            "config_id": config_id,
            "config_naam": hierarchie_data["config_naam"],
            "classificatie": classificatie,
            "klassen_legenda": klassen_legenda,
            "label_melding": label_melding,
            "hierarchie": enriched_tree,
            "coverage_percentage": round(coverage_pct, 1),
            "is_waterbuurt": bool(gebied_row.is_waterbuurt),
            "melding": melding,
            "laatste_update": datetime.now(),
        }

    # ── Percentielklasse (#255) ─────────────────────────────────────────────

    def get_selectie_kompas(self, config_id: int, gebied_ids: list[str]) -> dict[str, Any] | None:
        """
        Percentielklassen over een selectie van gebieden (#255): per indicator en per
        onderdeel/thema/kwadrant één klasse, met dezelfde aggregatieregel als voor één
        gebied (gewogen gemiddelde over alle gebied x indicator-paren). Alleen voor
        profielen met classificatie percentiel_8, of labels A-E bij label_ae (#256);
        anders zonder klassen.
        """
        hierarchie_data = self.get_hierarchie(config_id)
        if not hierarchie_data:
            return None
        classificatie = self.get_classificatie(config_id)
        boom = hierarchie_data["hierarchie"]
        legenda = None
        melding = None
        if classificatie == "percentiel_8":
            boom, legenda = self._percentielklassen_in_boom(config_id, gebied_ids, boom)
        elif classificatie == lk.CLASSIFICATIE:
            boom, legenda, melding = self._labels_in_boom(config_id, gebied_ids, boom)
        return {
            "config_id": config_id,
            "classificatie": classificatie,
            "gebied_ids": list(gebied_ids),
            "klassen_legenda": legenda,
            "label_melding": melding,
            "hierarchie": boom,
        }

    def _percentielklassen(self, config_id: int, gebied_ids: list[str], labels: bool = False):
        """
        Per indicator de (klasse, gewicht)-paren over de gebieden, en per indicator
        het aantal gebieden waarvan de waarde onderdrukt is (n onder de drempel).
        Gewicht = aantal gebieden met data in de referentiegroep. Een waterbuurt
        krijgt geen klasse (#155).

        labels (#256): labelscore 1..5 (5 = A) in plaats van de klasse 1..8: drempels uit
        indicator_labels als die er zijn, anders kwintielen in dezelfde referentiegroep.
        Geeft dan ook de bron per indicator ('drempels' of 'kwintiel').
        """
        rows = self.db.execute(
            text("""
            SELECT g.id AS gebied_id, g.gebiedstype_id, g.gemeente_code,
                   public.is_waterbuurt(g.naam, g.metadata) AS is_waterbuurt,
                   i.uuid::text AS indicator_uuid, gd.waarde, gd.jaar,
                   COALESCE(sr.score_type, i.score_type) AS score_type, sr.inverse
            FROM gebieden g
            CROSS JOIN (SELECT DISTINCT indicator_uuid FROM kompas_indicator_mapping
                        WHERE config_id = :config_id) kim
            JOIN indicatoren i ON i.uuid = kim.indicator_uuid AND i.is_actief = true
            LEFT JOIN LATERAL (
                SELECT waarde, jaar FROM gebied_data
                WHERE indicator_uuid = i.uuid AND gebied_id = g.id
                  AND COALESCE(scenario_id, 'current') = :scenario_id AND jaar IS NOT NULL
                ORDER BY jaar DESC LIMIT 1
            ) gd ON true
            LEFT JOIN kompas_indicator_scoring_regels sr
                ON sr.indicator_uuid = i.uuid AND sr.config_id = :config_id
            WHERE g.id = ANY(CAST(:gebied_ids AS varchar[]))
        """),
            {"config_id": config_id, "gebied_ids": list(gebied_ids), "scenario_id": SCENARIO_STANDAARD},
        ).fetchall()

        met_waarde = [r for r in rows if r.waarde is not None and not r.is_waterbuurt]
        uuids = sorted({r.indicator_uuid for r in met_waarde})
        onderdrukt = pk.onderdrukte_waarden(self.db, gebied_ids, uuids)
        referentie: dict = {}
        for gt in {r.gebiedstype_id for r in met_waarde}:
            gemeenten = {r.gemeente_code for r in met_waarde if r.gebiedstype_id == gt}
            for (gm, u), waarden in pk.referentie_waarden(self.db, gt, gemeenten, uuids).items():
                referentie[(gt, gm, u)] = waarden

        drempels = lk.drempels_uit_db(self.db, uuids) if labels else {}
        paren: dict[str, list] = {}
        n_onderdrukt: dict[str, int] = {}
        bron: dict[str, str] = {}
        for r in met_waarde:
            if (r.gebied_id, r.indicator_uuid, r.jaar) in onderdrukt:
                n_onderdrukt[r.indicator_uuid] = n_onderdrukt.get(r.indicator_uuid, 0) + 1
                continue
            ref = referentie.get((r.gebiedstype_id, r.gemeente_code, r.indicator_uuid), [])
            hoger_beter = pk.hoger_is_beter(r.score_type, r.inverse)
            if labels:
                k, bron[r.indicator_uuid] = lk.label_score(
                    float(r.waarde), ref, hoger_beter, drempels.get(r.indicator_uuid)
                )
                # met drempels telt het gebied ook mee zonder referentie (gewicht minimaal 1)
                paren.setdefault(r.indicator_uuid, []).append((k, max(len(ref), 1)))
            else:
                k = pk.klasse(float(r.waarde), ref, hoger_beter)
                paren.setdefault(r.indicator_uuid, []).append((k, len(ref)))
        if labels:
            return paren, n_onderdrukt, bron
        return paren, n_onderdrukt

    def _percentielklassen_in_boom(self, config_id: int, gebied_ids: list[str], boom: dict):
        """Zet klasse, klasse_kleur (en bij indicatoren color) in de boom; geeft (boom, legenda)."""
        paren, n_onderdrukt = self._percentielklassen(config_id, gebied_ids)
        color_service = ColorScaleService(self.db)
        kleuren = pk.palet(color_service)
        neutraal = pk.palet(color_service, neutraal=True)
        return pk.annoteer_boom(boom, paren, n_onderdrukt, kleuren, GEEN_DATA_KLEUR, neutraal), pk.legenda(kleuren)

    def _labels_in_boom(self, config_id: int, gebied_ids: list[str], boom: dict):
        """
        Labels A-E (#256): label, klasse (score 5 = A .. 1 = E) en klasse_kleur op elke node,
        label_bron op de indicatoren. Geeft (boom, legenda, melding); melding = voorlopige
        drempels (kwintielen) zolang een indicator met label geen drempels heeft.
        """
        paren, n_onderdrukt, bron = self._percentielklassen(config_id, gebied_ids, labels=True)
        color_service = ColorScaleService(self.db)
        kleuren = lk.palet(color_service)
        neutraal = pk.palet(color_service, neutraal=True, klassen=lk.KLASSEN)
        boom = lk.annoteer_boom(boom, paren, n_onderdrukt, kleuren, GEEN_DATA_KLEUR, bron, neutraal)
        voorlopig = not bron or lk.BRON_KWINTIEL in bron.values()
        return boom, lk.legenda(kleuren, voorlopig), (lk.MELDING_VOORLOPIG if voorlopig else None)

    def _get_bulk_percentiles(self, gebiedstype_id, gemeente_code: str | None = None) -> dict[str, list[float]]:
        """
        Bereken 12.5% stap thresholds voor alle indicatoren, over dezelfde
        referentiegroep als de Z-scores (#66): gebiedstype + gemeente, meest
        recente waarde per gebied, waterbuurten uitgesloten.
        Gebruikt PostgreSQL PERCENTILE_CONT voor performance
        """
        # We willen 7 split points voor 8 bins: 12.5, 25, 37.5, 50, 62.5, 75, 87.5
        query = text(f"""
            SELECT
                rw.indicator_uuid,
                PERCENTILE_CONT(ARRAY[0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875])
                WITHIN GROUP (ORDER BY rw.waarde) as thresholds
            FROM {SQL_REFERENTIE_WAARDEN} rw
            GROUP BY rw.indicator_uuid
        """)

        results = self.db.execute(query, referentie_params(gebiedstype_id, gemeente_code)).fetchall()

        # Convert to dict
        threshold_map = {}
        for row in results:
            if row.thresholds:
                threshold_map[str(row.indicator_uuid)] = list(row.thresholds)
        return threshold_map

    def get_indicator_path(self, config_id: int, indicator_uuid: str) -> dict[str, Any] | None:
        """
        Haal hiërarchie pad op voor specifieke indicator (breadcrumb)

        Returns: {"path": ["Titel", "Thema", "Onderdeel", "Indicator"], ...}
        """
        query = text("""
            SELECT
                titel_naam, thema_naam, onderdeel_naam, indicator_naam,
                titel_kleur, is_actueel, weging
            FROM v_kompas_hierarchie
            WHERE config_id = :config_id AND indicator_uuid = :uuid::uuid
            LIMIT 1
        """)

        row = self.db.execute(query, {"config_id": config_id, "uuid": indicator_uuid}).fetchone()

        if not row:
            return None

        path = [row.titel_naam, row.thema_naam, row.onderdeel_naam, row.indicator_naam]

        return {
            "config_id": config_id,
            "indicator_uuid": indicator_uuid,
            "path": path,
            "full_path_string": " > ".join(path),
            "indicator_details": dict(row._mapping),
        }

    def get_indicator_history(self, config_id: int, gebied_id: str, indicator_uuid: str) -> dict[str, Any] | None:
        """
        Haal historische data op voor een indicator in een gebied (voor time-series chart)

        Args:
            config_id: ID van kompas configuratie (voor verificatie/context)
            gebied_id: UUID van gebied
            indicator_uuid: UUID van indicator

        Returns: Dict met indicator info en list van history points
        """
        # 1. Haal indicator metadata inclusief Data Lineage (Sprint 22 Track C)
        meta_query = text("""
            SELECT
                i.naam, i.eenheid, i.bron, i.omschrijving, i.ontologische_beschrijving,
                i.bron_systeem_api, i.bron_tabel_referentie, i.laatste_check_datum,
                i.begingeldigheid, i.eindgeldigheid
            FROM indicatoren i
            WHERE i.uuid = CAST(:uuid AS UUID) AND i.is_actief = true
        """)
        meta = self.db.execute(meta_query, {"uuid": indicator_uuid}).fetchone()

        if not meta:
            return None

        # 2. Haal data points (gebied_data) - gebruik jaar
        history_query = text("""
            SELECT
                jaar,
                waarde,
                bron,
                updated_at
            FROM gebied_data
            WHERE indicator_uuid = CAST(:uuid AS UUID)
              AND gebied_id = :gebied_id
              AND jaar IS NOT NULL
              AND COALESCE(scenario_id, 'current') = 'current'
            ORDER BY jaar ASC
        """)

        history_rows = self.db.execute(history_query, {"uuid": indicator_uuid, "gebied_id": gebied_id}).fetchall()

        # Format history
        history = []
        for row in history_rows:
            history.append(
                {
                    "jaar": row.jaar,
                    "waarde": float(row.waarde),
                    "bron": row.bron or meta.bron,
                    "datum": row.updated_at.strftime("%Y-%m-%d") if row.updated_at else None,
                }
            )

        # 3. Haal gebied naam
        gebied_query = text("SELECT naam FROM gebieden WHERE id = :id")
        gebied = self.db.execute(gebied_query, {"id": gebied_id}).fetchone()

        bron_url = self._resolve_source_url(meta.bron_systeem_api, meta.bron_tabel_referentie)

        return {
            "bron": meta.bron,
            "bron_systeem_api": meta.bron_systeem_api,
            "bron_tabel_referentie": meta.bron_tabel_referentie,
            "bron_url": bron_url,
            "laatste_check_datum": meta.laatste_check_datum.strftime("%d-%m-%Y") if meta.laatste_check_datum else None,
            "definitie": meta.omschrijving or meta.ontologische_beschrijving or "Geen beschrijving beschikbaar.",
            "ontologische_beschrijving": meta.ontologische_beschrijving,
            "eenheid": meta.eenheid,
            "indicator": {
                "uuid": indicator_uuid,
                "naam": meta.naam,
                "eenheid": meta.eenheid,
                "bron": meta.bron,
                "bron_systeem_api": meta.bron_systeem_api,
                "bron_tabel_referentie": meta.bron_tabel_referentie,
                "bron_url": bron_url,
            },
            "gebied": {"id": gebied_id, "naam": gebied.naam if gebied else "Onbekend"},
            "history": history,
        }

    def _resolve_source_url(self, bron_systeem: str | None, bron_ref: str | None) -> str | None:
        """Genereert de externe URL naar de officiële catalogus/dataset voor data lineage."""
        if not bron_systeem or not bron_ref:
            return None
        s = bron_systeem.upper()
        if s == "CBS_ODATA":
            return f"https://opendata.cbs.nl/#/CBS/nl/dataset/{bron_ref}/table"
        elif s == "RIVM_STATLINE":
            return (
                f"https://opendata.cbs.nl/#/CBS/nl/dataset/{bron_ref}/table"
                if "NED" in bron_ref.upper()
                else "https://www.volksgezondheidenzorg.info/"
            )
        elif s == "BAG_API":
            return "https://bag.basisregistraties.overheid.nl/"
        elif s == "POLITIE_DATA":
            return f"https://opendata.cbs.nl/#/CBS/nl/dataset/{bron_ref}/table"
        elif s == "OV_API":
            return "https://openov.nl/"
        return None

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    def _build_tree_from_rows(self, rows: list) -> dict[str, Any]:
        """
        Build geneste hiërarchie tree van flat database rows

        Returns: KompasNode compatible dict
        """
        if not rows:
            return {"name": "Root", "children": []}

        # Group by titel
        titels = {}
        for row in rows:
            if not row.titel_id:
                continue

            titel_id = row.titel_id
            if titel_id not in titels:
                titels[titel_id] = {"name": row.titel_naam, "type": "titel", "color": row.titel_kleur, "children": {}}

            # Group by thema binnen titel
            if row.thema_id:
                thema_id = row.thema_id
                if thema_id not in titels[titel_id]["children"]:
                    titels[titel_id]["children"][thema_id] = {"name": row.thema_naam, "type": "thema", "children": {}}

                # Group by onderdeel binnen thema
                if row.onderdeel_id:
                    onderdeel_id = row.onderdeel_id
                    if onderdeel_id not in titels[titel_id]["children"][thema_id]["children"]:
                        titels[titel_id]["children"][thema_id]["children"][onderdeel_id] = {
                            "name": row.onderdeel_naam,
                            "type": "onderdeel",
                            "children": [],
                        }

                    # Add indicator
                    if row.indicator_uuid:
                        titels[titel_id]["children"][thema_id]["children"][onderdeel_id]["children"].append(
                            {
                                "name": row.indicator_naam,
                                "type": "indicator",
                                "uuid": str(row.indicator_uuid),
                                "value": None,  # Wordt later ingevuld
                                "color": None,
                            }
                        )

        # Convert nested dicts to lists
        root_children = []
        for titel in titels.values():
            titel_node = {"name": titel["name"], "type": titel["type"], "color": titel["color"], "children": []}

            for thema in titel["children"].values():
                thema_node = {"name": thema["name"], "type": thema["type"], "children": []}

                for onderdeel in thema["children"].values():
                    # Children zijn al een list van indicators
                    thema_node["children"].append(onderdeel)

                titel_node["children"].append(thema_node)

            root_children.append(titel_node)

        return {"name": "Root", "type": "root", "children": root_children}

    def _enrich_tree_with_values(
        self,
        tree: dict,
        data_map: dict[str, dict],
        bulk_thresholds: dict[str, list[float]] = None,
        current_titel: str = None,
    ) -> dict:
        """
        Recursively voeg waarden en kleuren toe aan tree nodes

        Args:
            tree: Hiërarchie tree dict
            data_map: Dict[indicator_uuid] -> {waarde, score_type, ...}
            bulk_thresholds: Map van indicator uuid naar 7 percentile values
            current_titel: Naam van de huidige hoofdtitel (context)

        Returns: Enriched tree
        """
        enriched = tree.copy()

        # Track titel context
        if enriched.get("type") == "titel":
            current_titel = enriched.get("name")

        # Pass context down via temporary private prop
        enriched["_context_titel"] = current_titel

        # Als dit een indicator is, vul waarde + kleur in
        if enriched.get("type") == "indicator" and enriched.get("uuid"):
            uuid = enriched["uuid"]
            if uuid in data_map:
                data = data_map[uuid]
                waarde = data["waarde"]

                # Altijd eenheid tonen (ook bij NULL)
                enriched["eenheid"] = data.get("eenheid")
                enriched["ontologische_beschrijving"] = data.get("ontologische_beschrijving")

                if waarde is not None:
                    # Indicator heeft data
                    enriched["value"] = waarde

                    # Haal percentiel thresholds uit bulk cache
                    thresholds = bulk_thresholds.get(uuid) if bulk_thresholds else None

                    # Bereken kleur via scoring service
                    enriched["color"] = self.scoring.get_color_for_value(
                        value=waarde,
                        score_type=data.get("score_type") or "positive_ascending",
                        thresholds=thresholds,  # Use percentiles!
                        inverse=data.get("inverse", False),
                        context=current_titel,
                    )
                else:
                    enriched["value"] = None
                    enriched["color"] = "#94A3B8"  # Grijs voor geen data
            else:
                enriched["value"] = None
                enriched["color"] = "#94A3B8"
                enriched["eenheid"] = None

        # Recursief voor children
        if "children" in enriched and enriched["children"]:
            enriched["children"] = [
                self._enrich_tree_with_values(child, data_map, bulk_thresholds, current_titel)
                for child in enriched["children"]
            ]

        return enriched

    def get_benchmark(self, config_id: int, groepen: list[dict], gemeente_code: str = None) -> dict[str, Any] | None:
        """
        Sprint 18 Track C: Berekent per groep (woonplaats) het gemiddelde per indicator,
        plus het gemeentegemiddelde als referentie.

        Args:
            config_id: ID van kompas configuratie
            groepen: [{"naam": "Makkum", "buurt_ids": ["BU...", ...]}, ...]
            gemeente_code: optioneel, voor gemeentegemiddelde

        Returns: Dict met groepen, referentie, en indicator metadata
        """
        if not groepen:
            return None

        # 1. Haal alle indicator UUIDs op die in dit kompas zitten
        indicator_query = text("""
            SELECT
                i.uuid, i.naam, COALESCE(sr.eenheid, i.eenheid) as eenheid,
                COALESCE(sr.score_type, i.score_type) AS score_type, sr.inverse,
                kt.naam AS kwadrant
            FROM kompas_indicator_mapping kim
            JOIN indicatoren i ON kim.indicator_uuid = i.uuid
            LEFT JOIN kompas_indicator_scoring_regels sr
                ON i.uuid = sr.indicator_uuid AND sr.config_id = :config_id
            LEFT JOIN kompas_onderdelen ko ON ko.id = kim.onderdeel_id
            LEFT JOIN kompas_themas kth ON kth.id = ko.thema_id
            LEFT JOIN kompas_titels kt ON kt.id = kth.titel_id
            WHERE kim.config_id = :config_id AND i.is_actief = true
        """)
        indicator_rows = self.db.execute(indicator_query, {"config_id": config_id}).fetchall()

        if not indicator_rows:
            return None

        # Metadata per indicator
        indicator_meta = {}
        indicator_uuids = []
        for row in indicator_rows:
            uid = str(row.uuid)
            indicator_uuids.append(uid)
            indicator_meta[uid] = {
                "naam": row.naam,
                "eenheid": row.eenheid or "",
                # Polariteit voor de kleur van de afwijking (#323)
                "richting": pk.richting(row.score_type, row.inverse, row.kwadrant),
            }

        # 2. Per groep: haal gemiddelde waarden op
        result_groepen = []
        for groep in groepen:
            buurt_ids = groep.get("buurt_ids", [])
            if not buurt_ids:
                continue

            # Query: gemiddelde waarde per indicator voor deze buurt-set
            avg_query = text("""
                SELECT
                    gd.indicator_uuid,
                    AVG(gd.waarde) as gem_waarde
                FROM gebied_data gd
                WHERE gd.indicator_uuid = ANY(CAST(:uuids AS uuid[]))
                  AND gd.gebied_id = ANY(:buurt_ids)
                  AND gd.waarde IS NOT NULL
                  AND COALESCE(gd.scenario_id, 'current') = 'current'
                  AND gd.jaar = (
                      SELECT MAX(gd2.jaar) FROM gebied_data gd2
                      WHERE gd2.indicator_uuid = gd.indicator_uuid
                        AND gd2.gebied_id = ANY(:buurt_ids2)
                        AND COALESCE(gd2.scenario_id, 'current') = 'current'
                  )
                GROUP BY gd.indicator_uuid
            """)

            avg_rows = self.db.execute(
                avg_query, {"uuids": indicator_uuids, "buurt_ids": buurt_ids, "buurt_ids2": buurt_ids}
            ).fetchall()

            indicatoren = {}
            for row in avg_rows:
                indicatoren[str(row.indicator_uuid)] = round(float(row.gem_waarde), 2)

            result_groepen.append(
                {"naam": groep.get("naam", "Onbekend"), "aantal_buurten": len(buurt_ids), "indicatoren": indicatoren}
            )

        # 3. Referentie: gemeentegemiddelde
        referentie = None
        if gemeente_code:
            # Centrale referentie (#66): CBS-buurten van de gemeente, waterbuurten uitgesloten
            ref_query = text(f"""
                SELECT rs.indicator_uuid, rs.gemiddelde as gem_waarde
                FROM {SQL_REFERENTIE_STATS} rs
            """)

            buurt_type_id = self._gebiedstype_id_voor_code(CBS_BUURT_CODE)
            ref_rows = (
                self.db.execute(
                    ref_query,
                    referentie_params(
                        buurt_type_id,
                        gemeente_code,
                        indicator_uuids=indicator_uuids,
                    ),
                ).fetchall()
                if buurt_type_id
                else []
            )

            ref_indicatoren = {}
            for row in ref_rows:
                ref_indicatoren[str(row.indicator_uuid)] = round(float(row.gem_waarde), 2)

            # Haal gemeentenaam op
            naam_query = text("SELECT naam FROM gemeenten WHERE code = :code")
            naam_res = self.db.execute(naam_query, {"code": gemeente_code}).fetchone()

            referentie = {
                "naam": naam_res.naam if naam_res else f"Gemeente {gemeente_code}",
                "indicatoren": ref_indicatoren,
            }

        return {
            "config_id": config_id,
            "groepen": result_groepen,
            "referentie": referentie,
            "indicator_meta": indicator_meta,
        }

    def _gebiedstype_id_voor_code(self, code: str) -> str | None:
        """Gebiedstype-id op code (bijv. CBS_BUURT); None als het type niet bestaat."""
        row = self.db.execute(text("SELECT id FROM gebiedstypes WHERE code = :code"), {"code": code}).fetchone()
        return str(row.id) if row else None

    def get_top_afwijkende_buurten(
        self, indicator_uuid: str, limit: int = 3, gebied_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Bereken Z-scores voor alle CBS-buurten en retourneer Top N positief + Top N negatief.

        Args:
            indicator_uuid: UUID van de indicator
            limit: Aantal buurten per richting (default 3)
            gebied_id: Optioneel, UUID van het gebied om de buurten te filteren op de gemeente van dit gebied

        Returns: Dict met top_positief en top_negatief lijsten, of None
        """

        # 1. Referentiegroep (#66): gebiedstype + gemeente van gebied_id; zonder
        #    gebied_id alle CBS-buurten (alle gemeenten). Waterbuurten uitgesloten.
        gem_res = None
        gebiedstype_id = None
        if gebied_id:
            gem_query = text("SELECT gemeente_code, gebiedstype_id FROM gebieden WHERE id = :gebied_id")
            gem_res = self.db.execute(gem_query, {"gebied_id": gebied_id}).fetchone()
            if gem_res:
                gebiedstype_id = gem_res.gebiedstype_id
        if not gebiedstype_id:
            gebiedstype_id = self._gebiedstype_id_voor_code(CBS_BUURT_CODE)
        if not gebiedstype_id:
            return None
        gemeente_code = gem_res.gemeente_code if gem_res and gem_res.gemeente_code else None

        query = text(f"""
            SELECT
                g.id as buurt_id,
                g.naam as buurt_naam,
                zs.waarde,
                zs.jaar,
                zs.gemiddelde,
                zs.z_score
            FROM {SQL_ZSCORE_GEBIEDEN} zs
            JOIN gebieden g ON zs.gebied_id = g.id
            WHERE zs.z_score IS NOT NULL
            ORDER BY ABS(zs.z_score) DESC, g.naam
        """)

        rows = self.db.execute(
            query, referentie_params(gebiedstype_id, gemeente_code, gebied_ids=None, indicator_uuids=[indicator_uuid])
        ).fetchall()
        if not rows:
            return None

        # Haal indicator metadata op
        meta_query = text("""
            SELECT i.naam, COALESCE(sr.eenheid, i.eenheid) as eenheid
            FROM indicatoren i
            LEFT JOIN kompas_indicator_scoring_regels sr ON i.uuid = sr.indicator_uuid
            WHERE i.uuid = :uuid AND i.is_actief = true
            LIMIT 1
        """)
        meta = self.db.execute(meta_query, {"uuid": indicator_uuid}).fetchone()

        positief = []
        negatief = []

        for row in rows:
            entry = {
                "buurt_id": row.buurt_id,
                "buurt_naam": row.buurt_naam,
                "waarde": round(float(row.waarde), 2),
                "z_score": round(float(row.z_score), 2),
            }
            if row.z_score > 0 and len(positief) < limit:
                positief.append(entry)
            elif row.z_score < 0 and len(negatief) < limit:
                negatief.append(entry)

            if len(positief) >= limit and len(negatief) >= limit:
                break

        # 2. Return payload with context
        context_naam = "Alle gemeenten"
        if gebied_id and gem_res and gem_res.gemeente_code:
            # We already have gemeente_code, let's get the naam of that gemeente
            naam_query = text("SELECT naam FROM gemeenten WHERE code = :code")
            naam_res = self.db.execute(naam_query, {"code": gem_res.gemeente_code}).fetchone()
            if naam_res:
                context_naam = naam_res.naam

        return {
            "indicator_naam": meta.naam if meta else "",
            "eenheid": (meta.eenheid or "") if meta else "",
            "referentie_gemiddelde": round(float(rows[0].gemiddelde), 2) if rows else 0,
            "context_naam": context_naam,
            "top_positief": positief,
            "top_negatief": negatief,
        }


class KompasScoringService:
    """Service voor kleurberekening op basis van scoring regels"""

    # 8-bin Scales
    PALETTE_NORMAL = ["#D73027", "#F46D43", "#FDAE61", "#FEE08B", "#D9EF8B", "#A6D96A", "#66BD63", "#1A9850"]

    # Blue scale (Dark -> Light) for Samenstelling
    # Dark Blue (#08306B) -> Light Blue (#F7FBFF)
    PALETTE_BLUE = ["#08306B", "#08519C", "#2171B5", "#4292C6", "#6BAED6", "#9ECAE1", "#C6DBEF", "#DEEBF7"]

    COLOR_MAP = {"green": "#22C55E", "yellow": "#FBBF24", "orange": "#F97316", "red": "#EF4444", "gray": "#94A3B8"}

    def get_color_for_value(
        self,
        value: float,
        score_type: str = "positive_ascending",
        thresholds: list[float] | None = None,
        inverse: bool = False,
        context: str | None = None,
    ) -> str:
        """
        Bepaal kleur obv percentiel thresholds (8 bins).
        """
        # 1. Determine Palette
        palette = self.PALETTE_NORMAL
        if context and "samenstelling" in context.lower():
            palette = self.PALETTE_BLUE

        # 2. Threshold Binning (Percentiles)
        if thresholds and len(thresholds) == 7:
            # Bug #46 fix: Maak drempels uniek om clipping bij scheve datasets (veel 0-waarden) te voorkomen
            unique_thresholds = sorted(list(set(thresholds)))

            bin_idx = 0
            for t in unique_thresholds:
                if value > t:
                    bin_idx += 1
                else:
                    break

            # Proportioneel schalen naar het 8-kleurenpalet als er minder unieke drempels zijn
            if len(unique_thresholds) < 7 and len(unique_thresholds) > 0:
                scale_factor = 7 / len(unique_thresholds)
                bin_idx = round(bin_idx * scale_factor)

            # Zekeringscheck
            bin_idx = min(7, max(0, bin_idx))

            # Lager is beter: omkeren (één regel, omnitwin.polariteit, #120)
            should_reverse = polariteit.lager_is_beter(score_type, inverse)
            if should_reverse:
                bin_idx = 7 - bin_idx

            return palette[bin_idx]

        # 3. Fallback: Interpolation (Legacy or no data)
        return self.COLOR_MAP["gray"]

    def _interpolate_hex(self, hex1: str, hex2: str, t: float) -> str:
        # Legacy method kept for compatibility if needed, but unused in new logic
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"

    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        if max_val == min_val:
            return 0.5
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
