"""
Report Service Layer
====================
Verantwoordelijk voor Data Aggregatie (Fase 1 van Rapportagemodule).
Berekent Z-scores, gemiddelden en filtert de belangrijkste uitschieters
om een strakke JSON payload voor de LLM (Fase 2) of frontend te genereren.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List
import json

class ReportDataService:
    """Service class voor Rapportage data aggregatie & pre-processing"""
    
    def __init__(self, db: Session):
        self.db = db

    def generate_report_payload(self, gebied_id: str) -> Dict[str, Any]:
        """
        Berekent Z-scores en genereert een geaggregeerde payload voor een gebied.
        Filtert op de meest significante afwijkingen.
        """
        # 1. Haal gebied metadata op (voor referentie kader)
        gebied_query = text("""
            SELECT g.id, g.naam, g.gemeente_code, gt.id as gebiedstype_id, gt.naam as gebiedstype_naam, gem.naam as gemeente_naam
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            LEFT JOIN gemeenten gem ON g.gemeente_code = gem.code
            WHERE g.id = :gebied_id
        """)
        gebied_info = self.db.execute(gebied_query, {"gebied_id": gebied_id}).fetchone()
        
        if not gebied_info:
            raise ValueError(f"Gebied met ID {gebied_id} niet gevonden.")
        
        gebied_dict = dict(gebied_info._mapping)
        gemeente_code = gebied_dict.get('gemeente_code')
        gemeente_naam = gebied_dict.get('gemeente_naam')
        gebiedstype_id = gebied_dict.get('gebiedstype_id')

        # 2. Bereken statistieken (Z-scores) t.o.v. zelfde gebiedstype binnen zelfde gemeente
        # Als er geen gemeente_code is (bijv. landelijk niveau), berekenen we t.o.v. alle gebieden van dat type.
        z_score_query = text("""
            WITH target_data AS (
                -- Haal per indicator het meest recente datapunt op voor DIT actuele gebied
                SELECT indicator_uuid, waarde, jaar
                FROM (
                    SELECT indicator_uuid, waarde, jaar,
                           ROW_NUMBER() OVER(PARTITION BY indicator_uuid ORDER BY jaar DESC) as rn
                    FROM gebied_data
                    WHERE gebied_id = :gebied_id
                ) t
                WHERE rn = 1
            ),
            referentie_stats AS (
                -- Bereken gemiddelde en standaarddeviatie voor the referentie groep,
                -- maar ALLEEN voor exact hetzelfde jaar als het actuele datapunt van het target gebied.
                SELECT 
                    gd.indicator_uuid,
                    AVG(gd.waarde) as avg_waarde,
                    STDDEV_SAMP(gd.waarde) as std_waarde
                FROM gebied_data gd
                JOIN gebieden g ON gd.gebied_id = g.id
                JOIN target_data td ON gd.indicator_uuid = td.indicator_uuid AND gd.jaar = td.jaar
                WHERE g.gebiedstype_id = :gebiedstype_id
                """ + (" AND g.gemeente_code = :gemeente_code" if gemeente_code else "") + """
                GROUP BY gd.indicator_uuid
            )
            SELECT 
                i.naam as indicator_naam,
                i.omschrijving,
                -- We halen de hoofdtitel (het kwadrant) op via de hiërarchie configuratie
                COALESCE(vkh.titel_naam, i.categorie, 'Overig') as kwadrant,
                i.eenheid,
                COALESCE(i.score_type, '+/+') as score_type,
                td.waarde as gebied_waarde,
                td.jaar as meetjaar,
                rs.avg_waarde as referentie_gemiddelde,
                -- Voorkom division by zero, null std_waarde gebeurt bij N=1
                CASE 
                    WHEN rs.std_waarde > 0 THEN (td.waarde - rs.avg_waarde) / rs.std_waarde 
                    ELSE 0 
                END as z_score
            FROM target_data td
            JOIN indicatoren i ON td.indicator_uuid = i.uuid
            JOIN referentie_stats rs ON td.indicator_uuid = rs.indicator_uuid
            JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
        """)
        
        params = {"gebied_id": gebied_id, "gebiedstype_id": gebiedstype_id}
        if gemeente_code:
            params["gemeente_code"] = gemeente_code
            
        result = self.db.execute(z_score_query, params)
        indicators = [dict(row._mapping) for row in result]

        # 3. Filtering: Selecteer alleen 'significante' indicatoren
        # Bijv: |Z-score| > 1.0 (meer dan 1 standaarddeviatie afwijking)
        # Sorteer op absolute Z-score impact
        significante_indicatoren = [
            ind for ind in indicators 
            if abs(float(ind['z_score'])) >= 1.0
        ]
        
        # Sorteer van sterkst afwijkend naar minst afwijkend
        significante_indicatoren.sort(key=lambda x: abs(float(x['z_score'])), reverse=True)
        
        # Groepeer per kwadrant voor LLM structuur
        domains_dict = {}
        for ind in significante_indicatoren:
            cat = ind['kwadrant'] or 'Overig'
            if cat not in domains_dict:
                domains_dict[cat] = []
                
            # Bepaal 'trend' of sentiment o.b.v. score_type
            z = float(ind['z_score'])
            score_type = ind['score_type']
            impact = "neutraal"
            score_uitleg = "neutraal"
            
            # De gebruiker gaf aan dat voor (+/-) geldt: "een lage waarde is positief, hoge waarde is negatief".
            # Dit betekent dat '+/-', net als '-/-' en '-/+', de regel 'lager is beter' volgen.
            # Alleen '+/+' betekent 'hoger is beter'.
            if score_type == '+/+':
                impact = "bovengemiddeld positief" if z > 0 else "ondergemiddeld negatief"
                score_uitleg = "Hogere waarde is beter"
            elif score_type in ['-/-', '-/+', '+/-']:
                impact = "bovengemiddeld negatief" if z > 0 else "ondergemiddeld positief"
                score_uitleg = "Lagere waarde is beter"
                
            domains_dict[cat].append({
                "indicator": ind['indicator_naam'],
                "omschrijving": ind['omschrijving'] if ind['omschrijving'] else "",
                "meetjaar": ind['meetjaar'],
                "waarde": round(float(ind['gebied_waarde']), 2),
                "gemiddelde": round(float(ind['referentie_gemiddelde']), 2),
                "z_score": round(z, 2),
                "score_type": score_type,
                "score_uitleg": score_uitleg,
                "eenheid": ind['eenheid'] or "",
                "impact": impact
            })

        referentie_str = f"Gemeente {gemeente_naam}" if gemeente_naam else (f"Gemeente {gemeente_code}" if gemeente_code else f"Alle {gebied_dict['gebiedstype_naam']}(en)")

        # 4. JSON Payload constructie
        payload = {
            "gebied_id": gebied_id,
            "referentie_groep": referentie_str,
            "aantal_indicatoren": len(indicators),
            "metadata": {
                "gebied": gebied_dict['naam'],
                "gebiedstype": gebied_dict['gebiedstype_naam'],
                "referentie_kader": referentie_str
            },
            "significante_domeinen": domains_dict,
            "totaal_uitschieters": len(significante_indicatoren)
        }
        
        return payload

    def generate_benchmark_payload(
        self,
        gebied_id_a: str,
        mode: str,                          # 'gebieden' | 'gemeente' | 'fryslan'
        gebieden_b: list = None,            # max 5, alleen bij mode='gebieden'
        referentie_gemeente: str = None     # alleen bij mode='gemeente'
    ) -> Dict[str, Any]:
        """
        Vergelijkt Gebied A met een referentie (specifieke gebieden, gemeente-gemiddelde of Fryslân-gemiddelde).
        Berekent de delta per indicator.
        """
        if gebieden_b is None:
            gebieden_b = []

        # Validatie
        if mode == 'gebieden' and len(gebieden_b) == 0:
            raise ValueError("Modus 'gebieden' vereist minstens 1 vergelijkingsgebied.")
        if mode == 'gebieden' and len(gebieden_b) > 5:
            raise ValueError("Maximaal 5 vergelijkingsgebieden toegestaan.")
        if mode == 'gemeente' and not referentie_gemeente:
            raise ValueError("Modus 'gemeente' vereist een gemeente_code.")

        # 1. Haal metadata Gebied A op
        gebied_a_query = text("""
            SELECT g.id, g.naam, gt.id as gebiedstype_id, gt.naam as gebiedstype_naam
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.id = :gebied_id
        """)
        gebied_a_info = self.db.execute(gebied_a_query, {"gebied_id": gebied_id_a}).fetchone()
        if not gebied_a_info:
            raise ValueError(f"Gebied A met ID {gebied_id_a} niet gevonden.")
        gebied_a_dict = dict(gebied_a_info._mapping)

        # 2. Haal waarden voor Gebied A op (meest recente per indicator)
        waarden_a_query = text("""
            SELECT gd.indicator_uuid, gd.waarde, gd.jaar,
                   i.naam as indicator_naam, i.eenheid, i.omschrijving,
                   COALESCE(i.score_type, '+/+') as score_type,
                   COALESCE(vkh.titel_naam, i.categorie, 'Overig') as kwadrant
            FROM (
                SELECT indicator_uuid, waarde, jaar,
                       ROW_NUMBER() OVER(PARTITION BY indicator_uuid ORDER BY jaar DESC) as rn
                FROM gebied_data
                WHERE gebied_id = :gebied_id_a
            ) gd
            JOIN indicatoren i ON gd.indicator_uuid = i.uuid
            LEFT JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            WHERE gd.rn = 1
        """)
        resultaat_a = self.db.execute(waarden_a_query, {"gebied_id_a": gebied_id_a})
        indicatoren_a = {str(r._mapping['indicator_uuid']): dict(r._mapping) for r in resultaat_a}

        if not indicatoren_a:
            raise ValueError(f"Geen data beschikbaar voor gebied {gebied_id_a}.")

        # 3. Bereken referentiewaarden per modus
        if mode == 'gebieden':
            # Gemiddelde van specifieke gebieden
            ref_query = text("""
                SELECT gd.indicator_uuid, AVG(gd.waarde) as ref_waarde, COUNT(DISTINCT gd.gebied_id) as n
                FROM (
                    SELECT indicator_uuid, waarde, gebied_id,
                           ROW_NUMBER() OVER(PARTITION BY indicator_uuid, gebied_id ORDER BY jaar DESC) as rn
                    FROM gebied_data
                    WHERE gebied_id = ANY(:gebieden_b)
                ) gd
                WHERE gd.rn = 1
                GROUP BY gd.indicator_uuid
            """)
            ref_result = self.db.execute(ref_query, {"gebieden_b": gebieden_b})
            referentie_label = f"{len(gebieden_b)} gebied{'en' if len(gebieden_b) > 1 else ''}"

        elif mode == 'gemeente':
            # Gemiddelde van alle buurten in een gemeente
            gemeente_naam_query = text("SELECT naam FROM gemeenten WHERE code = :code")
            gem_naam = self.db.execute(gemeente_naam_query, {"code": referentie_gemeente}).fetchone()
            gemeente_label = gem_naam[0] if gem_naam else referentie_gemeente

            ref_query = text("""
                SELECT gd.indicator_uuid, AVG(gd.waarde) as ref_waarde, COUNT(DISTINCT gd.gebied_id) as n
                FROM (
                    SELECT gd2.indicator_uuid, gd2.waarde, gd2.gebied_id,
                           ROW_NUMBER() OVER(PARTITION BY gd2.indicator_uuid, gd2.gebied_id ORDER BY gd2.jaar DESC) as rn
                    FROM gebied_data gd2
                    JOIN gebieden g ON gd2.gebied_id = g.id
                    WHERE g.gemeente_code = :gemeente_code
                      AND g.gebiedstype_id = :gebiedstype_id
                ) gd
                WHERE gd.rn = 1
                GROUP BY gd.indicator_uuid
            """)
            ref_result = self.db.execute(ref_query, {
                "gemeente_code": referentie_gemeente,
                "gebiedstype_id": gebied_a_dict['gebiedstype_id']
            })
            referentie_label = f"⌀ Gemeente {gemeente_label}"

        elif mode == 'fryslan':
            # Gemiddelde van ALLE buurten (geheel Fryslân)
            ref_query = text("""
                SELECT gd.indicator_uuid, AVG(gd.waarde) as ref_waarde, COUNT(DISTINCT gd.gebied_id) as n
                FROM (
                    SELECT gd2.indicator_uuid, gd2.waarde, gd2.gebied_id,
                           ROW_NUMBER() OVER(PARTITION BY gd2.indicator_uuid, gd2.gebied_id ORDER BY gd2.jaar DESC) as rn
                    FROM gebied_data gd2
                    JOIN gebieden g ON gd2.gebied_id = g.id
                    WHERE g.gebiedstype_id = :gebiedstype_id
                ) gd
                WHERE gd.rn = 1
                GROUP BY gd.indicator_uuid
            """)
            ref_result = self.db.execute(ref_query, {
                "gebiedstype_id": gebied_a_dict['gebiedstype_id']
            })
            referentie_label = "⌀ Provincie Fryslân"

        else:
            raise ValueError(f"Onbekende modus: {mode}")

        # 4. Match referentie met Gebied A en bereken delta's
        ref_dict = {str(r._mapping['indicator_uuid']): dict(r._mapping) for r in ref_result}

        vergelijking = []
        for uuid, ind_a in indicatoren_a.items():
            if uuid not in ref_dict:
                continue
            ref = ref_dict[uuid]
            waarde_a = float(ind_a['waarde'])
            ref_waarde = float(ref['ref_waarde'])
            delta = waarde_a - ref_waarde
            score_type = ind_a['score_type']

            # Bepaal impact op basis van score_type
            if score_type == '+/+':
                impact = "bovengemiddeld positief" if delta > 0 else "ondergemiddeld negatief"
            else:
                impact = "bovengemiddeld negatief" if delta > 0 else "ondergemiddeld positief"

            vergelijking.append({
                "indicator": ind_a['indicator_naam'],
                "kwadrant": ind_a['kwadrant'] or 'Overig',
                "eenheid": ind_a['eenheid'] or '',
                "omschrijving": ind_a['omschrijving'] or '',
                "waarde_a": round(waarde_a, 2),
                "referentie_waarde": round(ref_waarde, 2),
                "delta": round(delta, 2),
                "delta_pct": round((delta / ref_waarde * 100), 2) if ref_waarde != 0 else 0.0,
                "score_type": score_type,
                "impact": impact,
                "n_gebieden": int(ref['n'])
            })

        # Sorteer op absolute delta (sterkste afwijking eerst)
        vergelijking.sort(key=lambda x: abs(x['delta']), reverse=True)

        return {
            "gebied_a": {"id": gebied_id_a, "naam": gebied_a_dict['naam']},
            "referentie_label": referentie_label,
            "mode": mode,
            "vergelijking": vergelijking,
            "totaal_indicatoren": len(vergelijking)
        }

    def generate_executive_payload(self, gebied_id: str) -> Dict[str, Any]:
        """
        Compacte executive samenvatting: top 3 kansen en top 3 risico's.
        Hergebruikt de bestaande generate_report_payload method.
        """
        full_payload = self.generate_report_payload(gebied_id)

        # Verzamel alle significante indicatoren
        alle_indicatoren = []
        for domain, indicators in full_payload.get("significante_domeinen", {}).items():
            for ind in indicators:
                ind['kwadrant'] = domain
                alle_indicatoren.append(ind)

        # Splits op impact: positief = kansen, negatief = risico's
        kansen = [i for i in alle_indicatoren if 'positief' in i.get('impact', '')]
        risicos = [i for i in alle_indicatoren if 'negatief' in i.get('impact', '')]

        # Sorteer op absolute z_score en pak top 3
        kansen.sort(key=lambda x: abs(x['z_score']), reverse=True)
        risicos.sort(key=lambda x: abs(x['z_score']), reverse=True)

        return {
            "gebied_id": gebied_id,
            "metadata": full_payload.get("metadata", {}),
            "referentie_groep": full_payload.get("referentie_groep", ""),
            "top_kansen": kansen[:3],
            "top_risicos": risicos[:3],
            "totaal_uitschieters": full_payload.get("totaal_uitschieters", 0),
            "aantal_indicatoren": full_payload.get("aantal_indicatoren", 0)
        }

    # ─── Multi-Gebiedsdossier (Zones-analyse) ────────────────────────────────

    def _get_zscore_kleur(self, z_score_abs: float, is_negatief_impact: bool) -> str:
        """Bepaal kleur op basis van absolute z-score. Colorblind-safe divergerend palet."""
        if z_score_abs < 0.5:
            return "#8c96a0"   # neutraal grijs — in lijn
        elif z_score_abs < 1.0:
            return "#d4b483"   # warm zand — licht afwijkend
        elif z_score_abs < 1.5:
            return "#c17c3e"   # donker zand/brons — matig afwijkend
        elif z_score_abs < 2.0:
            return "#2b6ca3"   # blauw — sterk afwijkend
        else:
            return "#1a3d5c"   # donkerblauw — extreem afwijkend

    def _determine_impact(self, z_score: float, score_type: str) -> str:
        """Bepaal de impact-tekst op basis van z-score en score_type."""
        if score_type == '+/+':
            return "bovengemiddeld positief" if z_score > 0 else "ondergemiddeld negatief"
        else:  # -/-, -/+, +/-
            return "bovengemiddeld negatief" if z_score > 0 else "ondergemiddeld positief"

    def generate_multi_gebied_payload(
        self,
        gebied_ids: List[str],
        referentie: str = 'gemeente',
        gemeente_code: str = '1900',
        deelgebied_naam: str = None,
        thema: str = None
    ) -> Dict[str, Any]:
        """
        Multi-Gebiedsdossier: Berekent per buurt de top 3 indicatoren met de sterkste
        z-score afwijking en aggregeert per thema.

        Args:
            gebied_ids: Lijst van CBS buurt-IDs (bijv. 44 buurten)
            referentie: 'gemeente' of 'fryslan'
            gemeente_code: Gemeentecode voor referentie (default SWF = '1900')
            deelgebied_naam: Optioneel label voor rapportheader
            thema: Optioneel thema-filter (bijv. 'Kwaliteit van Leven')
        """
        if not gebied_ids:
            raise ValueError("Minimaal 1 gebied_id is vereist.")

        # 1. Bepaal gebiedstype (CBS Buurt)
        gebiedstype_query = text("""
            SELECT gt.id as gebiedstype_id
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.id = :sample_id
            LIMIT 1
        """)
        gt_row = self.db.execute(gebiedstype_query, {"sample_id": gebied_ids[0]}).fetchone()
        if not gt_row:
            raise ValueError(f"Gebied {gebied_ids[0]} niet gevonden.")
        gebiedstype_id = str(gt_row._mapping['gebiedstype_id'])

        # 2. Bouw referentie-filter
        referentie_filter = "g2.gebiedstype_id = :gebiedstype_id"
        params: Dict[str, Any] = {
            "gebied_ids": gebied_ids,
            "gebiedstype_id": gebiedstype_id
        }
        if referentie == 'gemeente':
            referentie_filter += " AND g2.gemeente_code = :gemeente_code"
            params["gemeente_code"] = gemeente_code

        # 2b. Filter water-buurten uit de selectie
        water_filter_query = text("""
            SELECT g.id FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
        """)
        water_result = self.db.execute(water_filter_query, {"gebied_ids": gebied_ids})
        gefilterde_ids = [str(r._mapping['id']) for r in water_result]
        if not gefilterde_ids:
            raise ValueError("Alle geselecteerde gebieden zijn water-buurten.")
        params["gebied_ids"] = gefilterde_ids

        # 2c. Optioneel thema-filter
        thema_filter_clause = ""
        if thema and thema != 'alle':
            thema_filter_clause = "WHERE thema = :thema_filter"
            params["thema_filter"] = thema

        # 3. Bereken z-scores voor ALLE buurten × ALLE indicatoren
        #    Top 3 per buurt via ROW_NUMBER i.p.v. DISTINCT ON
        z_score_query = text(f"""
            WITH target_data AS (
                -- Meest recente waarde per buurt per indicator
                SELECT indicator_uuid, gebied_id, waarde, jaar
                FROM (
                    SELECT indicator_uuid, gebied_id, waarde, jaar,
                           ROW_NUMBER() OVER(PARTITION BY gebied_id, indicator_uuid ORDER BY jaar DESC) AS rn
                    FROM gebied_data
                    WHERE gebied_id = ANY(:gebied_ids)
                ) sub
                WHERE rn = 1
            ),
            referentie_stats AS (
                -- Referentiestatistieken (gem + std + min + max per indicator)
                SELECT gd2.indicator_uuid,
                       AVG(gd2.waarde)         AS avg_waarde,
                       STDDEV_SAMP(gd2.waarde) AS std_waarde,
                       MIN(gd2.waarde)         AS min_waarde,
                       MAX(gd2.waarde)         AS max_waarde
                FROM (
                    SELECT gd3.indicator_uuid, gd3.waarde, gd3.gebied_id,
                           ROW_NUMBER() OVER(PARTITION BY gd3.indicator_uuid, gd3.gebied_id ORDER BY gd3.jaar DESC) AS rn
                    FROM gebied_data gd3
                    JOIN gebieden g2 ON gd3.gebied_id = g2.id
                    WHERE {referentie_filter}
                ) gd2
                WHERE gd2.rn = 1
                GROUP BY gd2.indicator_uuid
                HAVING STDDEV_SAMP(gd2.waarde) > 0
            ),
            alle_zscores AS (
                SELECT
                    td.gebied_id,
                    g.naam                          AS buurt_naam,
                    i.naam                          AS indicator_naam,
                    i.eenheid                       AS eenheid,
                    COALESCE(vkh.titel_naam, i.categorie, 'Overig') AS thema,
                    COALESCE(i.score_type, '+/+')   AS score_type,
                    td.waarde,
                    rs.avg_waarde,
                    rs.std_waarde,
                    rs.min_waarde,
                    rs.max_waarde,
                    (td.waarde - rs.avg_waarde) / rs.std_waarde AS z_score
                FROM target_data td
                JOIN gebieden g        ON td.gebied_id = g.id
                JOIN indicatoren i     ON td.indicator_uuid = i.uuid
                JOIN v_kompas_hierarchie vkh
                                       ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
                JOIN referentie_stats rs ON td.indicator_uuid = rs.indicator_uuid
            ),
            gefilterde_zscores AS (
                -- Optioneel thema-filter
                SELECT * FROM alle_zscores
                {thema_filter_clause}
            ),
            top_per_buurt AS (
                -- Per buurt: top 3 indicatoren met de GROOTSTE absolute z-score
                SELECT *,
                    ROW_NUMBER() OVER(PARTITION BY gebied_id ORDER BY ABS(z_score) DESC) AS rang
                FROM gefilterde_zscores
            )
            SELECT * FROM top_per_buurt WHERE rang <= 3 ORDER BY gebied_id, rang
        """)

        result = self.db.execute(z_score_query, params)
        rows = [dict(r._mapping) for r in result]

        # 4. Bouw buurten_analyse met geneste top_3 structuur
        #    Groepeer per buurt_id, rn=1 bepaalt de hoofdrij + kleur
        from collections import OrderedDict
        buurt_groups: Dict[str, Dict[str, Any]] = OrderedDict()

        for row in rows:
            z = float(row['z_score'])
            z_abs = abs(z)
            score_type = row['score_type']
            impact = self._determine_impact(z, score_type)
            is_negatief = 'negatief' in impact
            kleur = self._get_zscore_kleur(z_abs, is_negatief)
            rang = int(row['rang'])

            entry = {
                "indicator_naam": row['indicator_naam'],
                "eenheid": row.get('eenheid') or '',
                "thema": row['thema'],
                "score_type": score_type,
                "z_score": round(z, 2),
                "z_score_abs": round(z_abs, 2),
                "impact": impact,
                "kleur_hex": kleur,
                "waarde": round(float(row['waarde']), 2),
                "ref_gemiddelde": round(float(row['avg_waarde']), 2),
                "ref_min": round(float(row['min_waarde']), 2),
                "ref_max": round(float(row['max_waarde']), 2)
            }

            bid = row['gebied_id']
            if bid not in buurt_groups:
                # Eerste (rang=1) rij wordt de hoofdrij
                buurt_groups[bid] = {
                    "buurt_id": bid,
                    "buurt_naam": row['buurt_naam'],
                    "max_z_score": round(z, 2),
                    "max_z_score_abs": round(z_abs, 2),
                    "indicator_naam": row['indicator_naam'],
                    "eenheid": row.get('eenheid') or '',
                    "thema": row['thema'],
                    "score_type": score_type,
                    "impact": impact,
                    "kleur_hex": kleur,
                    "waarde": round(float(row['waarde']), 2),
                    "ref_gemiddelde": round(float(row['avg_waarde']), 2),
                    "ref_min": round(float(row['min_waarde']), 2),
                    "ref_max": round(float(row['max_waarde']), 2),
                    "top_3": [entry]
                }
            else:
                buurt_groups[bid]["top_3"].append(entry)

        buurten_analyse = list(buurt_groups.values())
        # Sorteer op sterkste afwijking (primaire rij)
        buurten_analyse.sort(key=lambda x: x['max_z_score_abs'], reverse=True)

        # 5. Bereken thema-aggregaat
        # Gebruik ALLE z-scores (niet alleen top per buurt) voor thema-gemiddelde
        thema_agg_filter = ""
        if thema and thema != 'alle':
            thema_agg_filter = f"AND COALESCE(vkh.titel_naam, i.categorie, 'Overig') = :thema_filter"

        thema_query = text(f"""
            WITH target_data AS (
                SELECT indicator_uuid, gebied_id, waarde, jaar
                FROM (
                    SELECT indicator_uuid, gebied_id, waarde, jaar,
                           ROW_NUMBER() OVER(PARTITION BY gebied_id, indicator_uuid ORDER BY jaar DESC) AS rn
                    FROM gebied_data
                    WHERE gebied_id = ANY(:gebied_ids)
                ) sub WHERE rn = 1
            ),
            referentie_stats AS (
                SELECT gd2.indicator_uuid,
                       AVG(gd2.waarde) AS avg_waarde,
                       STDDEV_SAMP(gd2.waarde) AS std_waarde
                FROM (
                    SELECT gd3.indicator_uuid, gd3.waarde, gd3.gebied_id,
                           ROW_NUMBER() OVER(PARTITION BY gd3.indicator_uuid, gd3.gebied_id ORDER BY gd3.jaar DESC) AS rn
                    FROM gebied_data gd3
                    JOIN gebieden g2 ON gd3.gebied_id = g2.id
                    WHERE {referentie_filter}
                ) gd2 WHERE gd2.rn = 1
                GROUP BY gd2.indicator_uuid
                HAVING STDDEV_SAMP(gd2.waarde) > 0
            )
            SELECT
                COALESCE(vkh.titel_naam, i.categorie, 'Overig') AS thema,
                AVG((td.waarde - rs.avg_waarde) / rs.std_waarde) AS gem_zscore,
                COUNT(*) FILTER (WHERE ABS((td.waarde - rs.avg_waarde) / rs.std_waarde) >= 1.0) AS n_uitschieters,
                COUNT(*) AS n_datapunten
            FROM target_data td
            JOIN indicatoren i ON td.indicator_uuid = i.uuid
            JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            JOIN referentie_stats rs ON td.indicator_uuid = rs.indicator_uuid
            WHERE 1=1 {thema_agg_filter}
            GROUP BY COALESCE(vkh.titel_naam, i.categorie, 'Overig')
            ORDER BY ABS(AVG((td.waarde - rs.avg_waarde) / rs.std_waarde)) DESC
        """)

        thema_result = self.db.execute(thema_query, params)
        thema_aggregaat = {}
        for row in thema_result:
            r = dict(row._mapping)
            thema_aggregaat[r['thema']] = {
                "gem_zscore": round(float(r['gem_zscore']), 2),
                "n_uitschieters": int(r['n_uitschieters']),
                "n_datapunten": int(r['n_datapunten'])
            }

        # 6. Label
        if referentie == 'gemeente':
            gem_naam_row = self.db.execute(
                text("SELECT naam FROM gemeenten WHERE code = :code"),
                {"code": gemeente_code}
            ).fetchone()
            referentie_label = f"⌀ Gemeente {gem_naam_row[0]}" if gem_naam_row else f"⌀ Gemeente {gemeente_code}"
        else:
            referentie_label = "⌀ Provincie Fryslân"

        return {
            "deelgebied_naam": deelgebied_naam or f"{len(gebied_ids)} buurten",
            "referentie_label": referentie_label,
            "referentie_modus": referentie,
            "totaal_buurten": len(gebied_ids),
            "buurten_met_data": len(buurten_analyse),
            "buurten_analyse": buurten_analyse,
            "thema_aggregaat": thema_aggregaat,
            "top_uitschieters": buurten_analyse[:10]
        }

    def generate_multi_gebied_geojson(
        self,
        gebied_ids: List[str],
        referentie: str = 'gemeente',
        gemeente_code: str = '1900',
        thema: str = None
    ) -> Dict[str, Any]:
        """
        Genereert een GeoJSON FeatureCollection met per buurt:
        - Geometrie (WGS84)
        - Max z-score indicator + top_3 array
        - Kleurcodering
        Bedoeld voor de D3 SVG choropleth op de rapportpagina.
        """
        # Haal de analyse-data op (inclusief thema-filter)
        payload = self.generate_multi_gebied_payload(
            gebied_ids=gebied_ids,
            referentie=referentie,
            gemeente_code=gemeente_code,
            thema=thema
        )
        
        # Maak een lookup van buurt_id → analyse-data (1 per buurt, met geneste top_3)
        analyse_lookup = {b['buurt_id']: b for b in payload['buurten_analyse']}

        # Haal geometrieën op (als GeoJSON) — filter water-buurten
        geom_query = text("""
            SELECT g.id, g.naam,
                   ST_AsGeoJSON(ST_Transform(g.geom, 4326))::json AS geometry
            FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND g.geom IS NOT NULL
              AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
        """)
        geom_result = self.db.execute(geom_query, {"gebied_ids": gebied_ids})

        features = []
        for row in geom_result:
            r = dict(row._mapping)
            buurt_id = r['id']
            analyse = analyse_lookup.get(buurt_id, {})

            feature = {
                "type": "Feature",
                "geometry": r['geometry'],
                "properties": {
                    "buurt_id": buurt_id,
                    "buurt_naam": r['naam'],
                    "max_z_score": analyse.get('max_z_score', 0),
                    "max_z_score_abs": analyse.get('max_z_score_abs', 0),
                    "indicator_naam": analyse.get('indicator_naam', ''),
                    "thema": analyse.get('thema', ''),
                    "impact": analyse.get('impact', ''),
                    "kleur_hex": analyse.get('kleur_hex', '#6b7280'),
                    "top_3": analyse.get('top_3', [])
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "metadata": {
                "referentie_label": payload['referentie_label'],
                "totaal_buurten": payload['totaal_buurten']
            },
            "features": features
        }

    def generate_thema_analyse_payload(
        self,
        gebied_ids: List[str],
        referentie: str = 'gemeente',
        gemeente_code: str = '1900',
        deelgebied_naam: str = None,
        categorie: str = None,
        thema_naam: str = None,
        onderdeel_naam: str = None
    ) -> Dict[str, Any]:
        """
        Thema-Analyse: Berekent alle indicatoren binnen de hiërarchie-selectie
        en groepeert deze per buurt.
        """
        if not gebied_ids:
            raise ValueError("Minimaal 1 gebied_id is vereist.")

        # 1. Bepaal gebiedstype
        gebiedstype_query = text("""
            SELECT gt.id as gebiedstype_id
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.id = :sample_id
            LIMIT 1
        """)
        gt_row = self.db.execute(gebiedstype_query, {"sample_id": gebied_ids[0]}).fetchone()
        if not gt_row:
            raise ValueError(f"Gebied {gebied_ids[0]} niet gevonden.")
        gebiedstype_id = str(gt_row._mapping['gebiedstype_id'])

        # 2. Bouw referentie-filter
        referentie_filter = "g2.gebiedstype_id = :gebiedstype_id"
        params: Dict[str, Any] = {
            "gebied_ids": gebied_ids,
            "gebiedstype_id": gebiedstype_id
        }
        if referentie == 'gemeente':
            referentie_filter += " AND g2.gemeente_code = :gemeente_code"
            params["gemeente_code"] = gemeente_code

        # 2b. Filter water-buurten uit
        water_filter_query = text("""
            SELECT g.id FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
        """)
        water_result = self.db.execute(water_filter_query, {"gebied_ids": gebied_ids})
        gefilterde_ids = [str(r._mapping['id']) for r in water_result]
        if not gefilterde_ids:
            raise ValueError("Alle geselecteerde gebieden zijn water-buurten.")
        params["gebied_ids"] = gefilterde_ids

        # 2c. Bouw thema filter clause
        filters = []
        if categorie:
            filters.append("titel_naam = :categorie")
            params["categorie"] = categorie
        if thema_naam:
            filters.append("thema_naam = :thema_naam")
            params["thema_naam"] = thema_naam
        if onderdeel_naam:
            filters.append("onderdeel_naam = :onderdeel_naam")
            params["onderdeel_naam"] = onderdeel_naam
        
        thema_filter_clause = "WHERE " + " AND ".join(filters) if filters else ""

        # 3. Bereken z-scores
        z_score_query = text(f"""
            WITH target_data AS (
                SELECT indicator_uuid, gebied_id, waarde, jaar
                FROM (
                    SELECT indicator_uuid, gebied_id, waarde, jaar,
                           ROW_NUMBER() OVER(PARTITION BY gebied_id, indicator_uuid ORDER BY jaar DESC) AS rn
                    FROM gebied_data
                    WHERE gebied_id = ANY(:gebied_ids)
                ) sub
                WHERE rn = 1
            ),
            referentie_stats AS (
                SELECT gd2.indicator_uuid,
                       AVG(gd2.waarde)         AS avg_waarde,
                       STDDEV_SAMP(gd2.waarde) AS std_waarde,
                       MIN(gd2.waarde)         AS min_waarde,
                       MAX(gd2.waarde)         AS max_waarde
                FROM (
                    SELECT gd3.indicator_uuid, gd3.waarde, gd3.gebied_id,
                           ROW_NUMBER() OVER(PARTITION BY gd3.indicator_uuid, gd3.gebied_id ORDER BY gd3.jaar DESC) AS rn
                    FROM gebied_data gd3
                    JOIN gebieden g2 ON gd3.gebied_id = g2.id
                    WHERE {referentie_filter}
                ) gd2
                WHERE gd2.rn = 1
                GROUP BY gd2.indicator_uuid
                HAVING STDDEV_SAMP(gd2.waarde) > 0
            ),
            alle_zscores AS (
                SELECT
                    td.gebied_id,
                    g.naam                          AS buurt_naam,
                    i.naam                          AS indicator_naam,
                    i.eenheid                       AS eenheid,
                    vkh.titel_naam                  AS titel_naam,
                    vkh.thema_naam                  AS thema_naam,
                    vkh.onderdeel_naam              AS onderdeel_naam,
                    COALESCE(i.score_type, '+/+')   AS score_type,
                    td.waarde,
                    rs.avg_waarde,
                    rs.std_waarde,
                    rs.min_waarde,
                    rs.max_waarde,
                    (td.waarde - rs.avg_waarde) / rs.std_waarde AS z_score
                FROM target_data td
                JOIN gebieden g        ON td.gebied_id = g.id
                JOIN indicatoren i     ON td.indicator_uuid = i.uuid
                JOIN v_kompas_hierarchie vkh
                                       ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
                JOIN referentie_stats rs ON td.indicator_uuid = rs.indicator_uuid
            ),
            gefilterde_zscores AS (
                SELECT * FROM alle_zscores
                {thema_filter_clause}
            )
            SELECT * FROM gefilterde_zscores 
            ORDER BY gebied_id, ABS(z_score) DESC
        """)

        result = self.db.execute(z_score_query, params)
        rows = [dict(r._mapping) for r in result]

        # 4. Groepeer per buurt
        from collections import OrderedDict
        buurt_groups: Dict[str, Dict[str, Any]] = OrderedDict()

        for row in rows:
            z = float(row['z_score'])
            z_abs = abs(z)
            score_type = row['score_type']
            impact = self._determine_impact(z, score_type)
            is_negatief = 'negatief' in impact
            kleur = self._get_zscore_kleur(z_abs, is_negatief)

            entry = {
                "indicator_naam": row['indicator_naam'],
                "eenheid": row.get('eenheid') or '',
                "thema": row.get('thema_naam') or row.get('titel_naam') or 'Overig',
                "onderdeel": row.get('onderdeel_naam') or '',
                "score_type": score_type,
                "z_score": round(z, 2),
                "z_score_abs": round(z_abs, 2),
                "impact": impact,
                "kleur_hex": kleur,
                "waarde": round(float(row['waarde']), 2),
                "ref_gemiddelde": round(float(row['avg_waarde']), 2),
                "ref_min": round(float(row['min_waarde']), 2),
                "ref_max": round(float(row['max_waarde']), 2)
            }

            bid = row['gebied_id']
            if bid not in buurt_groups:
                buurt_groups[bid] = {
                    "buurt_id": bid,
                    "buurt_naam": row['buurt_naam'],
                    "max_z_score": round(z, 2),
                    "max_z_score_abs": round(z_abs, 2),
                    "indicatoren": [entry]
                }
            else:
                buurt_groups[bid]["indicatoren"].append(entry)
                # Update max if this is higher (although SQL is ordered so first is max)
                if z_abs > buurt_groups[bid]["max_z_score_abs"]:
                    buurt_groups[bid]["max_z_score"] = round(z, 2)
                    buurt_groups[bid]["max_z_score_abs"] = round(z_abs, 2)

        buurten_analyse = list(buurt_groups.values())
        buurten_analyse.sort(key=lambda x: x['max_z_score_abs'], reverse=True)

        # 5. Label
        if referentie == 'gemeente':
            gem_naam_row = self.db.execute(
                text("SELECT naam FROM gemeenten WHERE code = :code"),
                {"code": gemeente_code}
            ).fetchone()
            referentie_label = f"⌀ Gemeente {gem_naam_row[0]}" if gem_naam_row else f"⌀ Gemeente {gemeente_code}"
        else:
            referentie_label = "⌀ Provincie Fryslân"

        # 6. Beschrijving
        filter_parts = []
        if categorie: filter_parts.append(categorie)
        if thema_naam: filter_parts.append(thema_naam)
        if onderdeel_naam: filter_parts.append(onderdeel_naam)
        filter_beschrijving = " › ".join(filter_parts) if filter_parts else "Alle indicatoren"

        return {
            "rapport_type": "thema-analyse",
            "filter_beschrijving": filter_beschrijving,
            "deelgebied_naam": deelgebied_naam or f"{len(gebied_ids)} buurten",
            "referentie_label": referentie_label,
            "referentie_modus": referentie,
            "totaal_buurten": len(gebied_ids),
            "buurten_met_data": len(buurten_analyse),
            "buurten_analyse": buurten_analyse
        }

    def generate_thema_analyse_geojson(
        self,
        gebied_ids: List[str],
        referentie: str = 'gemeente',
        gemeente_code: str = '1900',
        categorie: str = None,
        thema_naam: str = None,
        onderdeel_naam: str = None
    ) -> Dict[str, Any]:
        """
        Genereert een GeoJSON FeatureCollection voor de Thema-Analyse.
        Geometrie bevat alle indicatoren. Kleuring op basis van max z-score of gem_zscore.
        We gebruiken de payload method en verrijken met geometry.
        """
        payload = self.generate_thema_analyse_payload(
            gebied_ids=gebied_ids,
            referentie=referentie,
            gemeente_code=gemeente_code,
            categorie=categorie,
            thema_naam=thema_naam,
            onderdeel_naam=onderdeel_naam
        )
        
        analyse_lookup = {b['buurt_id']: b for b in payload['buurten_analyse']}

        geom_query = text("""
            SELECT g.id, g.naam,
                   ST_AsGeoJSON(ST_Transform(g.geom, 4326))::json AS geometry
            FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND g.geom IS NOT NULL
              AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
        """)
        geom_result = self.db.execute(geom_query, {"gebied_ids": gebied_ids})

        features = []
        for row in geom_result:
            r = dict(row._mapping)
            buurt_id = r['id']
            analyse = analyse_lookup.get(buurt_id, {})

            feature = {
                "type": "Feature",
                "geometry": r['geometry'],
                "properties": {
                    "buurt_id": buurt_id,
                    "buurt_naam": r['naam'],
                    "max_z_score": analyse.get('max_z_score', 0),
                    "max_z_score_abs": analyse.get('max_z_score_abs', 0),
                    "indicatoren": analyse.get('indicatoren', [])
                }
            }
            # Kleur bepalen voor de map: we nemen de kleur van de hoogste uitschieter (al gesorteerd op 0 in array)
            if feature["properties"]["indicatoren"]:
                feature["properties"]["kleur_hex"] = feature["properties"]["indicatoren"][0]["kleur_hex"]
            else:
                feature["properties"]["kleur_hex"] = '#6b7280'

            features.append(feature)

        return {
            "type": "FeatureCollection",
            "metadata": {
                "referentie_label": payload['referentie_label'],
                "totaal_buurten": payload['totaal_buurten'],
                "filter_beschrijving": payload['filter_beschrijving']
            },
            "features": features
        }

