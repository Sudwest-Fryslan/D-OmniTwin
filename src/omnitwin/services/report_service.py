"""
Report Service Layer
====================
Verantwoordelijk voor Data Aggregatie (Fase 1 van Rapportagemodule).
Berekent Z-scores, gemiddelden en filtert de belangrijkste uitschieters
om een strakke JSON payload voor de LLM (Fase 2) of frontend te genereren.
"""

import html
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin import polariteit
from omnitwin.fouten import GebruikersFout
from omnitwin.services.organisatie import eigen_gemeente_code, lees_organisatie
from omnitwin.services.zscore_referentie import (
    MIN_N_STANDAARD,
    SQL_ZSCORE_GEBIEDEN,
    bereken_zscore,
    methodiek_beschrijving,
    referentie_params,
)


def provincie_referentie_label(provincie: str | None, aantal: int) -> str:
    """Label van de referentie 'provincie' (#324), met het aantal gebieden uit de data."""
    if provincie:
        return f"⌀ Provincie {provincie} ({aantal} gebieden)"
    return f"⌀ Alle gebieden ({aantal})"


class ReportDataService:
    """Service class voor Rapportage data aggregatie & pre-processing"""

    def __init__(self, db: Session):
        self.db = db

    def _provincie_referentie(self, gebiedstype_id) -> tuple:
        """
        Referentie 'provincie' (modus 'fryslan', #324): de provincie uit de instelling
        organisatie.benchmark_provincie, en het label met het aantal gebieden van dit
        type in die provincie (zonder waterbuurten). Zonder instelling: alle gebieden.
        Geeft (provincie of None, label).
        """
        provincie = (lees_organisatie(self.db) or {}).get("benchmark_provincie") or None
        aantal = (
            self.db.execute(
                text("""
            SELECT COUNT(*) FROM gebieden g
            WHERE g.gebiedstype_id = CAST(:gt AS uuid)
              AND NOT public.is_waterbuurt(g.naam, g.metadata)
              AND (CAST(:provincie AS varchar) IS NULL OR EXISTS (
                    SELECT 1 FROM gemeenten gm
                    WHERE gm.code = g.gemeente_code AND gm.provincie = CAST(:provincie AS varchar)))
        """),
                {"gt": str(gebiedstype_id), "provincie": provincie},
            ).scalar()
            or 0
        )
        return provincie, provincie_referentie_label(provincie, int(aantal))

    def generate_report_payload(self, gebied_id: str) -> dict[str, Any]:
        """
        Berekent Z-scores en genereert een geaggregeerde payload voor een gebied.
        Filtert op de meest significante afwijkingen.
        """
        # 1. Haal gebied metadata op (voor referentie kader)
        gebied_query = text("""
            SELECT g.id, g.naam, g.gemeente_code, gt.id as gebiedstype_id, gt.naam as gebiedstype_naam, gem.naam as gemeente_naam,
                   public.is_waterbuurt(g.naam, g.metadata) as is_waterbuurt
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            LEFT JOIN gemeenten gem ON g.gemeente_code = gem.code
            WHERE g.id = :gebied_id
        """)
        gebied_info = self.db.execute(gebied_query, {"gebied_id": gebied_id}).fetchone()

        if not gebied_info:
            raise GebruikersFout(f"Gebied met ID {gebied_id} niet gevonden.")

        gebied_dict = dict(gebied_info._mapping)
        gemeente_code = gebied_dict.get("gemeente_code")
        gemeente_naam = gebied_dict.get("gemeente_naam")
        gebiedstype_id = gebied_dict.get("gebiedstype_id")
        referentie_str = (
            f"Gemeente {gemeente_naam}"
            if gemeente_naam
            else (f"Gemeente {gemeente_code}" if gemeente_code else f"Alle {gebied_dict['gebiedstype_naam']}(en)")
        )
        metadata = {
            "gebied": gebied_dict["naam"],
            "gebiedstype": gebied_dict["gebiedstype_naam"],
            "referentie_kader": referentie_str,
        }

        # Waterbuurt als doelgebied: geen Z-scores, net als multi-gebied, thema-analyse
        # en deelgebied (#155). Eén definitie: is_waterbuurt() in 08_zscore_referentie.sql.
        if gebied_dict.get("is_waterbuurt"):
            return {
                "gebied_id": gebied_id,
                "referentie_groep": referentie_str,
                "aantal_indicatoren": 0,
                "metadata": metadata,
                "significante_domeinen": {},
                "totaal_uitschieters": 0,
                "is_waterbuurt": True,
                "meldingen": [
                    "Dit gebied is een waterbuurt. Waterbuurten worden niet vergeleken met "
                    "de referentiegroep; er zijn geen Z-scores."
                ],
                "methodiek": methodiek_beschrijving(),
            }

        # 2. Z-scores t.o.v. zelfde gebiedstype binnen zelfde gemeente, in hetzelfde jaar als de
        #    meest recente waarde van dit gebied (centrale referentie, jaarlogica zelfde_jaar, #66).
        # Zonder gemeente_code (bijv. landelijk niveau) t.o.v. alle gebieden van dat type.
        z_score_query = text(f"""
            SELECT
                i.naam as indicator_naam,
                i.omschrijving,
                -- We halen de hoofdtitel (het kwadrant) op via de hiërarchie configuratie
                COALESCE(vkh.titel_naam, i.categorie, 'Overig') as kwadrant,
                i.eenheid,
                COALESCE(i.score_type, '+/+') as score_type,
                zs.waarde as gebied_waarde,
                zs.jaar as meetjaar,
                zs.gemiddelde as referentie_gemiddelde,
                -- Geen spreiding (n < 2 of sd = 0): z = 0, telt niet als uitschieter
                COALESCE(zs.z_score, 0) as z_score,
                zs.n as referentie_n,
                zs.referentie_terugval
            FROM {SQL_ZSCORE_GEBIEDEN} zs
            JOIN indicatoren i ON zs.indicator_uuid = i.uuid
            JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
        """)

        params = referentie_params(gebiedstype_id, gemeente_code or None, gebied_ids=[gebied_id])

        result = self.db.execute(z_score_query, params)
        indicators = [dict(row._mapping) for row in result]

        # 3. Filtering: Selecteer alleen 'significante' indicatoren
        # Bijv: |Z-score| > 1.0 (meer dan 1 standaarddeviatie afwijking)
        # Sorteer op absolute Z-score impact
        significante_indicatoren = [ind for ind in indicators if abs(float(ind["z_score"])) >= 1.0]

        # Sorteer van sterkst afwijkend naar minst afwijkend
        significante_indicatoren.sort(key=lambda x: abs(float(x["z_score"])), reverse=True)

        # Groepeer per kwadrant voor LLM structuur
        domains_dict = {}
        for ind in significante_indicatoren:
            cat = ind["kwadrant"] or "Overig"
            if cat not in domains_dict:
                domains_dict[cat] = []

            # Bepaal 'trend' of sentiment o.b.v. score_type
            z = float(ind["z_score"])
            score_type = ind["score_type"]
            impact = "neutraal"
            score_uitleg = "neutraal"

            # Eén regel voor de richting (omnitwin.polariteit, #120)
            richting = polariteit.uit_oud(score_type)
            if richting == polariteit.HOGER_IS_BETER:
                impact = "bovengemiddeld positief" if z > 0 else "ondergemiddeld negatief"
                score_uitleg = "Hogere waarde is beter"
            elif richting == polariteit.LAGER_IS_BETER:
                impact = "bovengemiddeld negatief" if z > 0 else "ondergemiddeld positief"
                score_uitleg = "Lagere waarde is beter"

            domains_dict[cat].append(
                {
                    "indicator": ind["indicator_naam"],
                    "omschrijving": ind["omschrijving"] if ind["omschrijving"] else "",
                    "meetjaar": ind["meetjaar"],
                    "waarde": round(float(ind["gebied_waarde"]), 2),
                    "gemiddelde": round(float(ind["referentie_gemiddelde"]), 2),
                    "z_score": round(z, 2),
                    "score_type": score_type,
                    "score_uitleg": score_uitleg,
                    "eenheid": ind["eenheid"] or "",
                    "impact": impact,
                    "n_referentie": ind["referentie_n"],
                    "referentie_terugval": bool(ind["referentie_terugval"]),
                }
            )

        # Minimum-n (#155): melding als de referentie is teruggevallen op de meest
        # recente waarde per gebied (te weinig gebieden met een waarde in hetzelfde jaar)
        meldingen = []
        terugval = sorted({ind["indicator_naam"] for ind in indicators if ind.get("referentie_terugval")})
        if terugval:
            meldingen.append(
                f"Bij {len(terugval)} indicator(en) hadden minder dan {MIN_N_STANDAARD} gebieden "
                f"een waarde in hetzelfde jaar als dit gebied. Daar is vergeleken met de meest "
                f"recente waarde per gebied: {', '.join(terugval)}."
            )

        # 4. JSON Payload constructie
        payload = {
            "gebied_id": gebied_id,
            "referentie_groep": referentie_str,
            "aantal_indicatoren": len(indicators),
            "metadata": metadata,
            "significante_domeinen": domains_dict,
            "totaal_uitschieters": len(significante_indicatoren),
            "is_waterbuurt": False,
            "referentie_terugval_indicatoren": terugval,
            "meldingen": meldingen,
            "methodiek": methodiek_beschrijving(),
        }

        return payload

    def generate_benchmark_payload(
        self,
        gebied_id_a: str,
        mode: str,  # 'gebieden' | 'gemeente' | 'fryslan'
        gebieden_b: list = None,  # max 5, alleen bij mode='gebieden'
        referentie_gemeente: str = None,  # alleen bij mode='gemeente'
    ) -> dict[str, Any]:
        """
        Vergelijkt Gebied A met een referentie (specifieke gebieden, gemeente-gemiddelde of Fryslân-gemiddelde).
        Berekent de delta per indicator.
        """
        if gebieden_b is None:
            gebieden_b = []

        # Validatie
        if mode == "gebieden" and len(gebieden_b) == 0:
            raise GebruikersFout("Modus 'gebieden' vereist minstens 1 vergelijkingsgebied.")
        if mode == "gebieden" and len(gebieden_b) > 5:
            raise GebruikersFout("Maximaal 5 vergelijkingsgebieden toegestaan.")
        if mode == "gemeente" and not referentie_gemeente:
            raise GebruikersFout("Modus 'gemeente' vereist een gemeente_code.")

        # 1. Haal metadata Gebied A op
        gebied_a_query = text("""
            SELECT g.id, g.naam, gt.id as gebiedstype_id, gt.naam as gebiedstype_naam
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.id = :gebied_id
        """)
        gebied_a_info = self.db.execute(gebied_a_query, {"gebied_id": gebied_id_a}).fetchone()
        if not gebied_a_info:
            raise GebruikersFout(f"Gebied A met ID {gebied_id_a} niet gevonden.")
        gebied_a_dict = dict(gebied_a_info._mapping)

        # 2. Haal waarden voor Gebied A op (meest recente per indicator)
        waarden_a_query = text("""
            SELECT gd.indicator_uuid, gd.waarde, gd.jaar,
                   i.naam as indicator_naam, i.eenheid, i.omschrijving,
                   COALESCE(i.score_type, '+/+') as score_type,
                   COALESCE(vkh.titel_naam, i.categorie, 'Overig') as kwadrant
            FROM (
                SELECT indicator_uuid, waarde, jaar, n,
                       ROW_NUMBER() OVER(PARTITION BY indicator_uuid ORDER BY jaar DESC) as rn
                FROM gebied_data
                WHERE gebied_id = :gebied_id_a
                  AND COALESCE(scenario_id, 'current') = 'current'
                  AND jaar IS NOT NULL
            ) gd
            JOIN indicatoren i ON gd.indicator_uuid = i.uuid
            LEFT JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            -- kleine aantallen (#325): een waarde op te weinig waarnemingen niet tonen
            WHERE gd.rn = 1 AND i.is_actief = true AND NOT is_kleine_aantallen(gd.n)
""")
        resultaat_a = self.db.execute(waarden_a_query, {"gebied_id_a": gebied_id_a})
        indicatoren_a = {str(r._mapping["indicator_uuid"]): dict(r._mapping) for r in resultaat_a}

        if not indicatoren_a:
            raise GebruikersFout(f"Geen data beschikbaar voor gebied {gebied_id_a}.")

        # 3. Bereken referentiewaarden per modus
        if mode == "gebieden":
            # Gemiddelde van specifieke gebieden
            ref_query = text("""
                SELECT gd.indicator_uuid, AVG(gd.waarde) as ref_waarde, COUNT(DISTINCT gd.gebied_id) as n
                FROM (
                    SELECT indicator_uuid, waarde, gebied_id, n,
                           ROW_NUMBER() OVER(PARTITION BY indicator_uuid, gebied_id ORDER BY jaar DESC) as rn
                    FROM gebied_data
                    WHERE gebied_id = ANY(:gebieden_b)
                      AND COALESCE(scenario_id, 'current') = 'current'
                      AND jaar IS NOT NULL
                ) gd
                WHERE gd.rn = 1 AND NOT is_kleine_aantallen(gd.n)
                GROUP BY gd.indicator_uuid
            """)
            ref_result = self.db.execute(ref_query, {"gebieden_b": gebieden_b})
            referentie_label = f"{len(gebieden_b)} gebied{'en' if len(gebieden_b) > 1 else ''}"

        elif mode == "gemeente":
            # Gemiddelde van alle buurten in een gemeente (centrale referentie, #66)
            gemeente_naam_query = text("SELECT naam FROM gemeenten WHERE code = :code")
            gem_naam = self.db.execute(gemeente_naam_query, {"code": referentie_gemeente}).fetchone()
            gemeente_label = gem_naam[0] if gem_naam else referentie_gemeente

            # Referentie in hetzelfde jaar als de waarde van gebied A (jaarlogica zelfde_jaar)
            ref_query = text(f"""
                SELECT zs.indicator_uuid, zs.gemiddelde as ref_waarde, zs.n
                FROM {SQL_ZSCORE_GEBIEDEN} zs
            """)
            ref_result = self.db.execute(
                ref_query,
                referentie_params(gebied_a_dict["gebiedstype_id"], referentie_gemeente, gebied_ids=[gebied_id_a]),
            )
            referentie_label = f"⌀ Gemeente {gemeente_label}"

        elif mode == "fryslan":
            # Gemiddelde van de buurten in de benchmarkprovincie van de organisatie (#66, #324)
            provincie, referentie_label = self._provincie_referentie(gebied_a_dict["gebiedstype_id"])
            ref_query = text(f"""
                SELECT zs.indicator_uuid, zs.gemiddelde as ref_waarde, zs.n
                FROM {SQL_ZSCORE_GEBIEDEN} zs
            """)
            ref_result = self.db.execute(
                ref_query,
                referentie_params(gebied_a_dict["gebiedstype_id"], None, gebied_ids=[gebied_id_a], provincie=provincie),
            )

        else:
            raise GebruikersFout(f"Onbekende modus: {mode}")

        # 4. Match referentie met Gebied A en bereken delta's
        ref_dict = {str(r._mapping["indicator_uuid"]): dict(r._mapping) for r in ref_result}

        vergelijking = []
        for uuid, ind_a in indicatoren_a.items():
            if uuid not in ref_dict:
                continue
            ref = ref_dict[uuid]
            waarde_a = float(ind_a["waarde"])
            ref_waarde = float(ref["ref_waarde"])
            delta = waarde_a - ref_waarde
            score_type = ind_a["score_type"]

            # Bepaal impact op basis van de polariteit (#120)
            if polariteit.uit_oud(score_type) == polariteit.HOGER_IS_BETER:
                impact = "bovengemiddeld positief" if delta > 0 else "ondergemiddeld negatief"
            else:
                impact = "bovengemiddeld negatief" if delta > 0 else "ondergemiddeld positief"

            vergelijking.append(
                {
                    "indicator": ind_a["indicator_naam"],
                    "kwadrant": ind_a["kwadrant"] or "Overig",
                    "eenheid": ind_a["eenheid"] or "",
                    "omschrijving": ind_a["omschrijving"] or "",
                    "waarde_a": round(waarde_a, 2),
                    "referentie_waarde": round(ref_waarde, 2),
                    "delta": round(delta, 2),
                    "delta_pct": round((delta / ref_waarde * 100), 2) if ref_waarde != 0 else 0.0,
                    "score_type": score_type,
                    "impact": impact,
                    "n_gebieden": int(ref["n"]),
                }
            )

        # Sorteer op absolute delta (sterkste afwijking eerst)
        vergelijking.sort(key=lambda x: abs(x["delta"]), reverse=True)

        return {
            "gebied_a": {"id": gebied_id_a, "naam": gebied_a_dict["naam"]},
            "referentie_label": referentie_label,
            "mode": mode,
            "vergelijking": vergelijking,
            "totaal_indicatoren": len(vergelijking),
        }

    def generate_executive_payload(self, gebied_id: str) -> dict[str, Any]:
        """
        Compacte executive samenvatting: top 3 kansen en top 3 risico's.
        Hergebruikt de bestaande generate_report_payload method.
        """
        full_payload = self.generate_report_payload(gebied_id)

        # Verzamel alle significante indicatoren
        alle_indicatoren = []
        for domain, indicators in full_payload.get("significante_domeinen", {}).items():
            for ind in indicators:
                ind["kwadrant"] = domain
                alle_indicatoren.append(ind)

        # Splits op impact: positief = kansen, negatief = risico's
        kansen = [i for i in alle_indicatoren if "positief" in i.get("impact", "")]
        risicos = [i for i in alle_indicatoren if "negatief" in i.get("impact", "")]

        # Sorteer op absolute z_score en pak top 3
        kansen.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        risicos.sort(key=lambda x: abs(x["z_score"]), reverse=True)

        return {
            "gebied_id": gebied_id,
            "metadata": full_payload.get("metadata", {}),
            "referentie_groep": full_payload.get("referentie_groep", ""),
            "top_kansen": kansen[:3],
            "top_risicos": risicos[:3],
            "totaal_uitschieters": full_payload.get("totaal_uitschieters", 0),
            "aantal_indicatoren": full_payload.get("aantal_indicatoren", 0),
            "is_waterbuurt": full_payload.get("is_waterbuurt", False),
            "meldingen": full_payload.get("meldingen", []),
        }

    # ─── Multi-Gebiedsdossier (Zones-analyse) ────────────────────────────────

    def _get_zscore_kleur(self, z_score_abs: float, is_negatief_impact: bool) -> str:
        """Bepaal kleur op basis van absolute z-score. Colorblind-safe divergerend palet."""
        if z_score_abs < 0.5:
            return "#8c96a0"  # neutraal grijs — in lijn
        elif z_score_abs < 1.0:
            return "#d4b483"  # warm zand — licht afwijkend
        elif z_score_abs < 1.5:
            return "#c17c3e"  # donker zand/brons — matig afwijkend
        elif z_score_abs < 2.0:
            return "#2b6ca3"  # blauw — sterk afwijkend
        else:
            return "#1a3d5c"  # donkerblauw — extreem afwijkend

    def _determine_impact(self, z_score: float, score_type: str, polariteit_waarde: str | None = None) -> str:
        """Bepaal de impact-tekst op basis van z-score en score_type of polariteit."""
        pol = polariteit_waarde or polariteit.uit_oud(score_type)
        if pol == polariteit.NEUTRAAL:
            return "neutraal"
        if pol == polariteit.HOGER_IS_BETER:
            return "bovengemiddeld positief" if z_score > 0 else "ondergemiddeld negatief"
        else:  # lager is beter (#120)
            return "bovengemiddeld negatief" if z_score > 0 else "ondergemiddeld positief"

    def generate_multi_gebied_payload(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        deelgebied_naam: str = None,
        thema: str = None,
    ) -> dict[str, Any]:
        """
        Multi-Gebiedsdossier: Berekent per buurt de top 3 indicatoren met de sterkste
        z-score afwijking en aggregeert per thema.

        Args:
            gebied_ids: Lijst van CBS buurt-IDs (bijv. 44 buurten)
            referentie: 'gemeente' of 'fryslan'
            gemeente_code: Gemeentecode voor referentie (standaard: die van de eigen organisatie, #231)
            deelgebied_naam: Optioneel label voor rapportheader
            thema: Optioneel thema-filter (bijv. 'Kwaliteit van Leven')
        """
        gemeente_code = gemeente_code or eigen_gemeente_code(self.db)
        if not gebied_ids:
            raise GebruikersFout("Minimaal 1 gebied_id is vereist.")

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
            raise GebruikersFout(f"Gebied {gebied_ids[0]} niet gevonden.")
        gebiedstype_id = str(gt_row._mapping["gebiedstype_id"])

        # 2b. Filter water-buurten uit de selectie
        water_filter_query = text("""
            SELECT g.id FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND NOT public.is_waterbuurt(g.naam, g.metadata)
        """)
        water_result = self.db.execute(water_filter_query, {"gebied_ids": gebied_ids})
        gefilterde_ids = [str(r._mapping["id"]) for r in water_result]
        if not gefilterde_ids:
            raise GebruikersFout("Alle geselecteerde gebieden zijn water-buurten.")

        # 2. Referentiegroep: gebiedstype (+ gemeente bij referentie 'gemeente'), #66;
        #    anders de benchmarkprovincie van de organisatie (#324)
        provincie, provincie_label = (
            (None, None) if referentie == "gemeente" else self._provincie_referentie(gebiedstype_id)
        )
        params: dict[str, Any] = referentie_params(
            gebiedstype_id,
            gemeente_code if referentie == "gemeente" else None,
            gebied_ids=gefilterde_ids,
            provincie=provincie,
        )

        # 2c. Optioneel thema-filter
        thema_filter_clause = ""
        if thema and thema != "alle":
            thema_filter_clause = "WHERE thema = :thema_filter"
            params["thema_filter"] = thema

        # 3. Bereken z-scores voor ALLE buurten × ALLE indicatoren
        #    Top 3 per buurt via ROW_NUMBER i.p.v. DISTINCT ON
        z_score_query = text(f"""
            WITH zscores AS (
                -- Centrale referentie (#66): zscore_gebieden, waterbuurten uitgesloten
                SELECT zs.gebied_id, zs.indicator_uuid, zs.waarde, zs.jaar,
                       zs.gemiddelde        AS avg_waarde,
                       zs.standaarddeviatie AS std_waarde,
                       zs.min_waarde, zs.max_waarde,
                       zs.n                 AS n_ref_buurten,
                       zs.z_score
                FROM {SQL_ZSCORE_GEBIEDEN} zs
                WHERE zs.z_score IS NOT NULL
            ),
            alle_zscores AS (
                SELECT
                    td.gebied_id,
                    td.indicator_uuid,
                    g.naam                          AS buurt_naam,
                    i.naam                          AS indicator_naam,
                    i.eenheid                       AS eenheid,
                    COALESCE(vkh.titel_naam, i.categorie, 'Overig') AS thema,
                    COALESCE(i.score_type, '+/+')   AS score_type,
                    td.waarde,
                    td.avg_waarde,
                    td.std_waarde,
                    td.min_waarde,
                    td.max_waarde,
                    td.z_score AS z_score
                FROM zscores td
                JOIN gebieden g        ON td.gebied_id = g.id
                JOIN indicatoren i     ON td.indicator_uuid = i.uuid
                JOIN v_kompas_hierarchie vkh
                                       ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
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

        buurt_groups: dict[str, dict[str, Any]] = OrderedDict()

        for row in rows:
            z = float(row["z_score"])
            z_abs = abs(z)
            score_type = row["score_type"]
            impact = self._determine_impact(z, score_type)
            is_negatief = "negatief" in impact
            kleur = self._get_zscore_kleur(z_abs, is_negatief)
            rang = int(row["rang"])

            entry = {
                "indicator_uuid": str(row.get("indicator_uuid", "")),
                "indicator_naam": row["indicator_naam"],
                "eenheid": row.get("eenheid") or "",
                "thema": row["thema"],
                "score_type": score_type,
                "z_score": round(z, 2),
                "z_score_abs": round(z_abs, 2),
                "impact": impact,
                "kleur_hex": kleur,
                "waarde": round(float(row["waarde"]), 2),
                "ref_gemiddelde": round(float(row["avg_waarde"]), 2),
                "ref_min": round(float(row["min_waarde"]), 2),
                "ref_max": round(float(row["max_waarde"]), 2),
            }

            bid = row["gebied_id"]
            if bid not in buurt_groups:
                # Eerste (rang=1) rij wordt de hoofdrij
                buurt_groups[bid] = {
                    "buurt_id": bid,
                    "buurt_naam": row["buurt_naam"],
                    "max_z_score": round(z, 2),
                    "max_z_score_abs": round(z_abs, 2),
                    "indicator_naam": row["indicator_naam"],
                    "eenheid": row.get("eenheid") or "",
                    "thema": row["thema"],
                    "score_type": score_type,
                    "impact": impact,
                    "kleur_hex": kleur,
                    "waarde": round(float(row["waarde"]), 2),
                    "ref_gemiddelde": round(float(row["avg_waarde"]), 2),
                    "ref_min": round(float(row["min_waarde"]), 2),
                    "ref_max": round(float(row["max_waarde"]), 2),
                    "top_3": [entry],
                }
            else:
                buurt_groups[bid]["top_3"].append(entry)

        buurten_analyse = list(buurt_groups.values())
        # Sorteer op sterkste afwijking (primaire rij)
        buurten_analyse.sort(key=lambda x: x["max_z_score_abs"], reverse=True)

        # 5. Bereken thema-aggregaat
        # Gebruik ALLE z-scores (niet alleen top per buurt) voor thema-gemiddelde
        thema_agg_filter = ""
        if thema and thema != "alle":
            thema_agg_filter = "AND COALESCE(vkh.titel_naam, i.categorie, 'Overig') = :thema_filter"

        thema_query = text(f"""
            WITH zscores AS (
                -- Centrale referentie (#66): zscore_gebieden, waterbuurten uitgesloten
                SELECT zs.gebied_id, zs.indicator_uuid, zs.waarde, zs.jaar,
                       zs.gemiddelde        AS avg_waarde,
                       zs.standaarddeviatie AS std_waarde,
                       zs.min_waarde, zs.max_waarde,
                       zs.n                 AS n_ref_buurten,
                       zs.z_score
                FROM {SQL_ZSCORE_GEBIEDEN} zs
                WHERE zs.z_score IS NOT NULL
            )
            SELECT
                COALESCE(vkh.titel_naam, i.categorie, 'Overig') AS thema,
                AVG(CASE
                    WHEN COALESCE(i.polariteit, CASE WHEN i.score_type = '+/-' THEN 'lager_is_beter' ELSE 'hoger_is_beter' END) = 'lager_is_beter'
                    THEN -td.z_score
                    ELSE td.z_score
                END) FILTER (
                    WHERE COALESCE(i.polariteit, 'hoger_is_beter') != 'neutraal'
                      AND lower(COALESCE(vkh.titel_naam, '')) NOT LIKE '%samenstelling%'
                ) AS gem_zscore,
                COUNT(*) FILTER (WHERE ABS(td.z_score) >= 1.0) AS n_uitschieters,
                COUNT(*) AS n_datapunten
            FROM zscores td
            JOIN indicatoren i ON td.indicator_uuid = i.uuid
            JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            WHERE 1=1 {thema_agg_filter}
            GROUP BY COALESCE(vkh.titel_naam, i.categorie, 'Overig')
            ORDER BY ABS(COALESCE(AVG(CASE
                    WHEN COALESCE(i.polariteit, CASE WHEN i.score_type = '+/-' THEN 'lager_is_beter' ELSE 'hoger_is_beter' END) = 'lager_is_beter'
                    THEN -td.z_score
                    ELSE td.z_score
                END) FILTER (
                    WHERE COALESCE(i.polariteit, 'hoger_is_beter') != 'neutraal'
                      AND lower(COALESCE(vkh.titel_naam, '')) NOT LIKE '%samenstelling%'
                ), 0)) DESC
        """)

        thema_result = self.db.execute(thema_query, params)
        thema_aggregaat = {}
        for row in thema_result:
            r = dict(row._mapping)
            gem_z = r["gem_zscore"]
            thema_aggregaat[r["thema"]] = {
                "gem_zscore": round(float(gem_z), 2) if gem_z is not None else None,
                "n_uitschieters": int(r["n_uitschieters"]),
                "n_datapunten": int(r["n_datapunten"]),
            }

        # 6. Label
        if referentie == "gemeente":
            gem_naam_row = self.db.execute(
                text("SELECT naam FROM gemeenten WHERE code = :code"), {"code": gemeente_code}
            ).fetchone()
            referentie_label = f"⌀ Gemeente {gem_naam_row[0]}" if gem_naam_row else f"⌀ Gemeente {gemeente_code}"
        else:
            referentie_label = provincie_label

        # 7. Data Lineage & Bronverantwoording
        used_indicator_uuids = list(
            {top["indicator_uuid"] for b in buurten_analyse for top in b.get("top_3", []) if top.get("indicator_uuid")}
        )
        bronverantwoording = self.get_bronverantwoording_for_indicators(used_indicator_uuids)

        return {
            "deelgebied_naam": deelgebied_naam or f"{len(gebied_ids)} buurten",
            "referentie_label": referentie_label,
            "referentie_modus": referentie,
            "totaal_buurten": len(gebied_ids),
            "buurten_met_data": len(buurten_analyse),
            "buurten_analyse": buurten_analyse,
            "thema_aggregaat": thema_aggregaat,
            "top_uitschieters": buurten_analyse[:10],
            "bronverantwoording": bronverantwoording,
        }

    def get_bronverantwoording_for_indicators(self, indicator_uuids: list[str]) -> list[dict[str, Any]]:
        """
        Genereert een gestructureerde lijst met bronverantwoording en peildata.
        """
        if not indicator_uuids:
            return []

        query = text("""
            SELECT
                uuid, naam, bron, bron_systeem_api, bron_tabel_referentie,
                begingeldigheid, eindgeldigheid, laatste_check_datum
            FROM indicatoren
            WHERE uuid = ANY(CAST(:uuids AS uuid[])) AND is_actief = true
            ORDER BY bron, naam
        """)
        rows = self.db.execute(query, {"uuids": indicator_uuids}).fetchall()

        result = []
        for r in rows:
            bron_url = None
            if r.bron_systeem_api and r.bron_tabel_referentie:
                s = r.bron_systeem_api.upper()
                if s == "CBS_ODATA":
                    bron_url = f"https://opendata.cbs.nl/#/CBS/nl/dataset/{r.bron_tabel_referentie}/table"
                elif s == "RIVM_STATLINE":
                    bron_url = (
                        f"https://opendata.cbs.nl/#/CBS/nl/dataset/{r.bron_tabel_referentie}/table"
                        if "NED" in r.bron_tabel_referentie.upper()
                        else "https://www.volksgezondheidenzorg.info/"
                    )
                elif s == "BAG_API":
                    bron_url = "https://bag.basisregistraties.overheid.nl/"
                elif s == "POLITIE_DATA":
                    bron_url = f"https://opendata.cbs.nl/#/CBS/nl/dataset/{r.bron_tabel_referentie}/table"
                elif s == "OV_API":
                    bron_url = "https://openov.nl/"

            peildata_str = ""
            if r.begingeldigheid and r.eindgeldigheid:
                peildata_str = f"{r.begingeldigheid.year} - {r.eindgeldigheid.year}"
            elif r.eindgeldigheid:
                peildata_str = str(r.eindgeldigheid.year)
            elif r.begingeldigheid:
                peildata_str = str(r.begingeldigheid.year)

            result.append(
                {
                    "indicator_uuid": str(r.uuid),
                    "indicator_naam": r.naam,
                    "bron": r.bron or "Centraal Bureau voor de Statistiek (CBS)",
                    "bron_systeem_api": r.bron_systeem_api,
                    "bron_tabel_referentie": r.bron_tabel_referentie,
                    "bron_url": bron_url,
                    "peildata": peildata_str,
                    "laatste_controle": r.laatste_check_datum.strftime("%d-%m-%Y") if r.laatste_check_datum else None,
                }
            )
        return result

    def generate_multi_gebied_geojson(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        thema: str = None,
    ) -> dict[str, Any]:
        """
        Genereert een GeoJSON FeatureCollection met per buurt:
        - Geometrie (WGS84)
        - Max z-score indicator + top_3 array
        - Kleurcodering
        Bedoeld voor de D3 SVG choropleth op de rapportpagina.
        """
        # Haal de analyse-data op (inclusief thema-filter)
        payload = self.generate_multi_gebied_payload(
            gebied_ids=gebied_ids, referentie=referentie, gemeente_code=gemeente_code, thema=thema
        )

        # Maak een lookup van buurt_id → analyse-data (1 per buurt, met geneste top_3)
        analyse_lookup = {b["buurt_id"]: b for b in payload["buurten_analyse"]}

        # Haal geometrieën op (als GeoJSON) — filter water-buurten
        geom_query = text("""
            SELECT g.id, g.naam,
                   ST_AsGeoJSON(ST_Transform(g.geom, 4326))::json AS geometry
            FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND g.geom IS NOT NULL
              AND NOT public.is_waterbuurt(g.naam, g.metadata)
        """)
        geom_result = self.db.execute(geom_query, {"gebied_ids": gebied_ids})

        features = []
        for row in geom_result:
            r = dict(row._mapping)
            buurt_id = r["id"]
            analyse = analyse_lookup.get(buurt_id, {})

            feature = {
                "type": "Feature",
                "geometry": r["geometry"],
                "properties": {
                    "buurt_id": buurt_id,
                    "buurt_naam": r["naam"],
                    "max_z_score": analyse.get("max_z_score", 0),
                    "max_z_score_abs": analyse.get("max_z_score_abs", 0),
                    "indicator_naam": analyse.get("indicator_naam", ""),
                    "thema": analyse.get("thema", ""),
                    "impact": analyse.get("impact", ""),
                    "kleur_hex": analyse.get("kleur_hex", "#6b7280"),
                    "top_3": analyse.get("top_3", []),
                },
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "metadata": {"referentie_label": payload["referentie_label"], "totaal_buurten": payload["totaal_buurten"]},
            "features": features,
        }

    def generate_thema_analyse_payload(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        deelgebied_naam: str = None,
        categorie: str = None,
        thema_naam: str = None,
        onderdeel_naam: str = None,
    ) -> dict[str, Any]:
        """
        Thema-Analyse: Berekent alle indicatoren binnen de hiërarchie-selectie
        en groepeert deze per buurt.
        """
        gemeente_code = gemeente_code or eigen_gemeente_code(self.db)
        if not gebied_ids:
            raise GebruikersFout("Minimaal 1 gebied_id is vereist.")

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
            raise GebruikersFout(f"Gebied {gebied_ids[0]} niet gevonden.")
        gebiedstype_id = str(gt_row._mapping["gebiedstype_id"])

        # 2b. Filter water-buurten uit
        water_filter_query = text("""
            SELECT g.id FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND NOT public.is_waterbuurt(g.naam, g.metadata)
        """)
        water_result = self.db.execute(water_filter_query, {"gebied_ids": gebied_ids})
        gefilterde_ids = [str(r._mapping["id"]) for r in water_result]
        if not gefilterde_ids:
            raise GebruikersFout("Alle geselecteerde gebieden zijn water-buurten.")

        # 2. Referentiegroep: gebiedstype (+ gemeente bij referentie 'gemeente'), #66;
        #    anders de benchmarkprovincie van de organisatie (#324)
        provincie, provincie_label = (
            (None, None) if referentie == "gemeente" else self._provincie_referentie(gebiedstype_id)
        )
        params: dict[str, Any] = referentie_params(
            gebiedstype_id,
            gemeente_code if referentie == "gemeente" else None,
            gebied_ids=gefilterde_ids,
            provincie=provincie,
        )

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
            WITH zscores AS (
                -- Centrale referentie (#66): zscore_gebieden, waterbuurten uitgesloten
                SELECT zs.gebied_id, zs.indicator_uuid, zs.waarde, zs.jaar,
                       zs.gemiddelde        AS avg_waarde,
                       zs.standaarddeviatie AS std_waarde,
                       zs.min_waarde, zs.max_waarde,
                       zs.n                 AS n_ref_buurten,
                       zs.z_score
                FROM {SQL_ZSCORE_GEBIEDEN} zs
                WHERE zs.z_score IS NOT NULL
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
                    td.avg_waarde,
                    td.std_waarde,
                    td.min_waarde,
                    td.max_waarde,
                    td.z_score AS z_score
                FROM zscores td
                JOIN gebieden g        ON td.gebied_id = g.id
                JOIN indicatoren i     ON td.indicator_uuid = i.uuid
                JOIN v_kompas_hierarchie vkh
                                       ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
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

        buurt_groups: dict[str, dict[str, Any]] = OrderedDict()

        for row in rows:
            z = float(row["z_score"])
            z_abs = abs(z)
            score_type = row["score_type"]
            impact = self._determine_impact(z, score_type)
            is_negatief = "negatief" in impact
            kleur = self._get_zscore_kleur(z_abs, is_negatief)

            entry = {
                "indicator_naam": row["indicator_naam"],
                "eenheid": row.get("eenheid") or "",
                "thema": row.get("thema_naam") or row.get("titel_naam") or "Overig",
                "onderdeel": row.get("onderdeel_naam") or "",
                "score_type": score_type,
                "z_score": round(z, 2),
                "z_score_abs": round(z_abs, 2),
                "impact": impact,
                "kleur_hex": kleur,
                "waarde": round(float(row["waarde"]), 2),
                "ref_gemiddelde": round(float(row["avg_waarde"]), 2),
                "ref_min": round(float(row["min_waarde"]), 2),
                "ref_max": round(float(row["max_waarde"]), 2),
            }

            bid = row["gebied_id"]
            if bid not in buurt_groups:
                buurt_groups[bid] = {
                    "buurt_id": bid,
                    "buurt_naam": row["buurt_naam"],
                    "max_z_score": round(z, 2),
                    "max_z_score_abs": round(z_abs, 2),
                    "indicatoren": [entry],
                }
            else:
                buurt_groups[bid]["indicatoren"].append(entry)
                # Update max if this is higher (although SQL is ordered so first is max)
                if z_abs > buurt_groups[bid]["max_z_score_abs"]:
                    buurt_groups[bid]["max_z_score"] = round(z, 2)
                    buurt_groups[bid]["max_z_score_abs"] = round(z_abs, 2)

        buurten_analyse = list(buurt_groups.values())
        buurten_analyse.sort(key=lambda x: x["max_z_score_abs"], reverse=True)

        # 5. Label
        if referentie == "gemeente":
            gem_naam_row = self.db.execute(
                text("SELECT naam FROM gemeenten WHERE code = :code"), {"code": gemeente_code}
            ).fetchone()
            referentie_label = f"⌀ Gemeente {gem_naam_row[0]}" if gem_naam_row else f"⌀ Gemeente {gemeente_code}"
        else:
            referentie_label = provincie_label

        # 6. Beschrijving
        filter_parts = []
        if categorie:
            filter_parts.append(categorie)
        if thema_naam:
            filter_parts.append(thema_naam)
        if onderdeel_naam:
            filter_parts.append(onderdeel_naam)
        filter_beschrijving = " › ".join(filter_parts) if filter_parts else "Alle indicatoren"

        return {
            "rapport_type": "thema-analyse",
            "filter_beschrijving": filter_beschrijving,
            "deelgebied_naam": deelgebied_naam or f"{len(gebied_ids)} buurten",
            "referentie_label": referentie_label,
            "referentie_modus": referentie,
            "totaal_buurten": len(gebied_ids),
            "buurten_met_data": len(buurten_analyse),
            "buurten_analyse": buurten_analyse,
        }

    def generate_thema_analyse_geojson(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        categorie: str = None,
        thema_naam: str = None,
        onderdeel_naam: str = None,
    ) -> dict[str, Any]:
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
            onderdeel_naam=onderdeel_naam,
        )

        analyse_lookup = {b["buurt_id"]: b for b in payload["buurten_analyse"]}

        geom_query = text("""
            SELECT g.id, g.naam,
                   ST_AsGeoJSON(ST_Transform(g.geom, 4326))::json AS geometry
            FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND g.geom IS NOT NULL
              AND NOT public.is_waterbuurt(g.naam, g.metadata)
        """)
        geom_result = self.db.execute(geom_query, {"gebied_ids": gebied_ids})

        features = []
        for row in geom_result:
            r = dict(row._mapping)
            buurt_id = r["id"]
            analyse = analyse_lookup.get(buurt_id, {})

            feature = {
                "type": "Feature",
                "geometry": r["geometry"],
                "properties": {
                    "buurt_id": buurt_id,
                    "buurt_naam": r["naam"],
                    "max_z_score": analyse.get("max_z_score", 0),
                    "max_z_score_abs": analyse.get("max_z_score_abs", 0),
                    "indicatoren": analyse.get("indicatoren", []),
                },
            }
            # Kleur bepalen voor de map: we nemen de kleur van de hoogste uitschieter (al gesorteerd op 0 in array)
            if feature["properties"]["indicatoren"]:
                feature["properties"]["kleur_hex"] = feature["properties"]["indicatoren"][0]["kleur_hex"]
            else:
                feature["properties"]["kleur_hex"] = "#6b7280"

            features.append(feature)

        return {
            "type": "FeatureCollection",
            "metadata": {
                "referentie_label": payload["referentie_label"],
                "totaal_buurten": payload["totaal_buurten"],
                "filter_beschrijving": payload["filter_beschrijving"],
            },
            "features": features,
        }

    # ─── Sjabloon F: Woonplaats- & Deelgebiedsanalyse ─────────────────────────

    def generate_deelgebied_payload(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        deelgebied_naam: str | None = None,
    ) -> dict[str, Any]:
        """
        Sjabloon F: Woonplaats- & Deelgebiedsanalyse.
        Berekent een gewogen stads-/deelgebiedsgemiddelde op basis van inwoneraantallen,
        geaggregeerd per thema met Top 10 uitschieters (aandachtspunten en kansen),
        buurt-drilldowns en methodologische verantwoording.

        Args:
            gebied_ids: Lijst van CBS buurt-IDs (bijv. alle buurten van een woonplaats)
            referentie: 'gemeente' of 'fryslan'
            gemeente_code: Gemeentecode voor referentie (indien None afgeleid uit DB)
            deelgebied_naam: Label van het geselecteerde deelgebied / woonplaats (bijv. 'Sneek')
        """
        if not gebied_ids:
            raise GebruikersFout("Minimaal 1 gebied_id is vereist.")

        from collections import defaultdict

        # 1. Bepaal geselecteerde buurten, filter waterbuurten en haal gemeente/type op
        gebieden_query = text("""
            SELECT g.id, g.naam, g.gemeente_code, g.gebiedstype_id,
                   public.is_waterbuurt(g.naam, g.metadata) AS is_water
            FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
        """)
        geb_rows = [dict(r._mapping) for r in self.db.execute(gebieden_query, {"gebied_ids": gebied_ids}).fetchall()]
        if not geb_rows:
            raise GebruikersFout("Geen van de opgegeven gebieden is gevonden in de database.")

        waterbuurten = [{"id": str(g["id"]), "naam": str(g["naam"])} for g in geb_rows if g.get("is_water")]
        actieve_buurten = [g for g in geb_rows if not g.get("is_water")]

        if not actieve_buurten:
            raise GebruikersFout(
                "Alle geselecteerde gebieden zijn water-buurten en worden conform projectstandaard uitgesloten van analyse."
            )

        first_buurt = actieve_buurten[0]
        gebiedstype_id = str(first_buurt["gebiedstype_id"])
        if not gemeente_code:
            gemeente_code = first_buurt.get("gemeente_code") or eigen_gemeente_code(self.db)
            gemeente_code = str(gemeente_code) if gemeente_code else None

        # Gemeente naam ophalen voor duiding
        gem_row = self.db.execute(
            text("SELECT naam FROM gemeenten WHERE code = :code"), {"code": gemeente_code}
        ).fetchone()
        gemeente_naam = gem_row[0] if gem_row else gemeente_code

        # 2. Referentiegroep: gebiedstype (+ gemeente bij referentie 'gemeente'), #66
        provincie = None
        if referentie == "gemeente":
            referentie_label = f"⌀ Gemeente {gemeente_naam}"
        else:
            provincie, referentie_label = self._provincie_referentie(gebiedstype_id)

        actieve_ids = [str(b["id"]) for b in actieve_buurten]
        params: dict[str, Any] = referentie_params(
            gebiedstype_id,
            gemeente_code if referentie == "gemeente" else None,
            gebied_ids=actieve_ids,
            provincie=provincie,
        )

        # 3. Inwoneraantallen ophalen voor gewogen aggregatie
        inwoners_query = text("""
            SELECT gd.gebied_id, gd.waarde AS inwoners
            FROM gebied_data gd
            JOIN indicatoren i ON gd.indicator_uuid = i.uuid
            WHERE gd.gebied_id = ANY(:gebied_ids)
              AND i.naam = 'Inwoners'
              AND COALESCE(gd.scenario_id, 'current') = 'current'
              AND gd.jaar = (
                  SELECT MAX(gd2.jaar)
                  FROM gebied_data gd2
                  WHERE gd2.gebied_id = gd.gebied_id
                    AND gd2.indicator_uuid = gd.indicator_uuid
                    AND COALESCE(gd2.scenario_id, 'current') = 'current'
              )
        """)
        inw_rows = self.db.execute(inwoners_query, {"gebied_ids": actieve_ids}).fetchall()
        inw_map = {
            str(r._mapping["gebied_id"]): float(r._mapping["inwoners"])
            for r in inw_rows
            if r._mapping["inwoners"] is not None
        }

        inwoners_per_buurt: dict[str, dict[str, Any]] = {}
        fallback_buurten: list[dict[str, str]] = []
        nul_inwoners_buurten: list[dict[str, str]] = []
        totaal_inwoners = 0.0

        for b in actieve_buurten:
            bid = str(b["id"])
            bnaam = str(b["naam"])
            if bid in inw_map:
                inw_val = inw_map[bid]
                if inw_val <= 0:
                    nul_inwoners_buurten.append({"id": bid, "naam": bnaam})
                    gew = 0.0
                else:
                    gew = inw_val
                    totaal_inwoners += inw_val
                inwoners_per_buurt[bid] = {
                    "id": bid,
                    "naam": bnaam,
                    "inwoners": inw_val,
                    "gewicht": gew,
                    "is_fallback": False,
                }
            else:
                fallback_buurten.append({"id": bid, "naam": bnaam})
                inwoners_per_buurt[bid] = {"id": bid, "naam": bnaam, "inwoners": 0, "gewicht": 1.0, "is_fallback": True}

        # Fallback als ALLE buurten 0 inwoners of fallback hebben
        positive_weights = sum(b["gewicht"] for b in inwoners_per_buurt.values())
        if positive_weights == 0:
            for bid in inwoners_per_buurt:
                inwoners_per_buurt[bid]["gewicht"] = 1.0

        # 4. Target data en referentiestatistieken ophalen
        query = text(f"""
            WITH zscores AS (
                -- Centrale referentie (#66): zscore_gebieden, waterbuurten uitgesloten
                SELECT zs.gebied_id, zs.indicator_uuid, zs.waarde, zs.jaar,
                       zs.gemiddelde        AS avg_waarde,
                       zs.standaarddeviatie AS std_waarde,
                       zs.min_waarde, zs.max_waarde,
                       zs.n                 AS n_ref_buurten,
                       zs.z_score
                FROM {SQL_ZSCORE_GEBIEDEN} zs
                WHERE zs.z_score IS NOT NULL
            )
            SELECT
                td.indicator_uuid,
                td.gebied_id,
                g.naam                          AS buurt_naam,
                td.waarde,
                td.jaar,
                td.avg_waarde,
                td.std_waarde,
                td.min_waarde,
                td.max_waarde,
                td.n_ref_buurten,
                td.z_score,
                i.naam                          AS indicator_naam,
                i.eenheid                       AS eenheid,
                COALESCE(i.polariteit, CASE WHEN i.score_type = '+/-' THEN 'lager_is_beter' ELSE 'hoger_is_beter' END) AS polariteit,
                COALESCE(i.score_type, '+/+')   AS score_type,
                i.omschrijving,
                i.ontologische_beschrijving,
                i.bron,
                vkh.titel_naam                  AS kwadrant_naam,
                vkh.titel_kleur                 AS kwadrant_kleur,
                vkh.thema_naam                  AS thema_naam,
                vkh.onderdeel_naam              AS onderdeel_naam
            FROM zscores td
            JOIN gebieden g        ON td.gebied_id = g.id
            JOIN indicatoren i     ON td.indicator_uuid = i.uuid
            JOIN v_kompas_hierarchie vkh
                                   ON i.uuid = vkh.indicator_uuid
            JOIN kompas_configuraties kc
                                   ON kc.id = vkh.config_id AND kc.is_standaard = TRUE
            WHERE i.naam != 'Inwoners'
            ORDER BY vkh.titel_naam, vkh.thema_naam, i.naam
        """)

        result_rows = [dict(r._mapping) for r in self.db.execute(query, params).fetchall()]

        # 5. Groepeer per indicator en bereken gewogen gemiddelde + drilldown
        indicator_points = defaultdict(list)
        for r in result_rows:
            indicator_points[str(r["indicator_uuid"])].append(r)

        kwadrant_map = defaultdict(
            lambda: {"kwadrant_naam": "", "kwadrant_kleur": "#3B82F6", "themas": defaultdict(list)}
        )

        used_indicator_uuids = set()

        for uuid_str, pts in indicator_points.items():
            first_pt = pts[0]
            kw_naam = first_pt["kwadrant_naam"] or "Overig"
            kw_kleur = first_pt["kwadrant_kleur"] or "#3B82F6"
            th_naam = first_pt["thema_naam"] or "Overig"

            # Referentie voor het gewogen gemiddelde: die van het meest recente meetjaar
            # onder de buurten. ⚠️ Bij jaarlogica zelfde_jaar kunnen buurten met een ouder
            # meetjaar een andere referentie hebben; hun buurt-Z gebruikt hun eigen jaar.
            ref_pt = max(pts, key=lambda p: p["jaar"])
            avg_waarde = float(ref_pt["avg_waarde"])
            std_waarde = float(ref_pt["std_waarde"])
            n_ref = int(ref_pt["n_ref_buurten"])

            w_sum = 0.0
            sum_val_w = 0.0
            drilldown = []

            for pt in pts:
                bid = str(pt["gebied_id"])
                w_info = inwoners_per_buurt.get(bid, {"gewicht": 1.0, "inwoners": 0})
                gew = float(w_info["gewicht"])
                val = float(pt["waarde"])

                if gew > 0:
                    sum_val_w += val * gew
                    w_sum += gew

                # Buurt-zscore (uit zscore_gebieden) en afwijking t.o.v. referentie
                b_z = float(pt["z_score"])
                b_diff = val - avg_waarde
                b_diff_pct = (b_diff / avg_waarde * 100.0) if avg_waarde != 0 else 0.0

                drilldown.append(
                    {
                        "buurt_id": bid,
                        "buurt_naam": pt["buurt_naam"],
                        "waarde": round(val, 2),
                        "inwoners": int(w_info["inwoners"]),
                        "gewicht": round(gew, 1),
                        "buurt_z_score": round(b_z, 2),
                        "verschil": round(b_diff, 2),
                        "verschil_pct": round(b_diff_pct, 1),
                    }
                )

            if w_sum <= 0:
                continue

            gewogen_waarde = sum_val_w / w_sum
            # Z-score van het gewogen gemiddelde: zelfde formule als SQL zscore()
            z_score = bereken_zscore(gewogen_waarde, avg_waarde, std_waarde, n_ref) or 0.0
            z_abs = abs(z_score)
            verschil = gewogen_waarde - avg_waarde
            verschil_pct = (verschil / avg_waarde * 100.0) if avg_waarde != 0 else 0.0

            score_type = first_pt["score_type"]
            pol = first_pt.get("polariteit") or polariteit.uit_oud(score_type)
            is_neutraal = (kw_naam == "Samenstelling") or (pol == polariteit.NEUTRAAL)
            if is_neutraal:
                impact = "neutraal"
                is_ongunstig = False
            else:
                impact = self._determine_impact(z_score, score_type, pol)
                is_ongunstig = "negatief" in impact
            kleur = self._get_zscore_kleur(z_abs, is_ongunstig)

            # Sorteer drilldown buurten op afwijking van referentie
            drilldown.sort(key=lambda x: abs(x["buurt_z_score"]), reverse=True)

            indicator_item = {
                "indicator_uuid": uuid_str,
                "indicator_naam": first_pt["indicator_naam"],
                "eenheid": first_pt.get("eenheid") or "",
                "polariteit": first_pt.get("polariteit") or polariteit.uit_oud(score_type),
                "score_type": score_type,
                "gewogen_waarde": round(gewogen_waarde, 2),
                "ref_gemiddelde": round(avg_waarde, 2),
                "ref_std": round(std_waarde, 2),
                "ref_min": round(float(ref_pt["min_waarde"]), 2),
                "ref_max": round(float(ref_pt["max_waarde"]), 2),
                "z_score": round(z_score, 2),
                "z_score_abs": round(z_abs, 2),
                "verschil": round(verschil, 2),
                "verschil_pct": round(verschil_pct, 1),
                "impact": impact,
                "is_ongunstig": is_ongunstig,
                "kleur_hex": kleur,
                "omschrijving": first_pt.get("omschrijving") or "",
                "ontologische_beschrijving": first_pt.get("ontologische_beschrijving") or "",
                "bron": first_pt.get("bron") or "",
                "n_buurten_met_data": len(drilldown),
                "buurten_drilldown": drilldown,
            }

            kwadrant_map[kw_naam]["kwadrant_naam"] = kw_naam
            kwadrant_map[kw_naam]["kwadrant_kleur"] = kw_kleur
            kwadrant_map[kw_naam]["themas"][th_naam].append(indicator_item)
            used_indicator_uuids.add(uuid_str)

        # 6. Structureren per kwadrant en thema met Top 10 Aandachtspunten en Top 10 Kansen
        kwadranten_output = []
        kwadranten_volgorde = [
            "Kwaliteit fysieke leefomgeving",
            "Kwaliteit sociale leefomgeving",
            "Kwaliteit van leven",
            "Samenstelling",
        ]

        # Sorteer kwadranten volgens standaard volgorde
        gesorteerde_kw_namen = sorted(
            kwadrant_map.keys(), key=lambda k: kwadranten_volgorde.index(k) if k in kwadranten_volgorde else 99
        )

        for kw_naam in gesorteerde_kw_namen:
            kw_data = kwadrant_map[kw_naam]
            themas_output = []

            alle_kw_indicatoren = []

            for th_naam, ind_list in sorted(kw_data["themas"].items()):
                alle_kw_indicatoren.extend(ind_list)

                # Splits in aandachtspunten (ongunstig) en kansen (gunstig)
                if kw_naam == "Samenstelling":
                    aandachtspunten = []
                    kansen = []
                else:
                    aandachtspunten = [
                        i
                        for i in ind_list
                        if i["is_ongunstig"]
                        and (i.get("polariteit") or polariteit.uit_oud(i.get("score_type"))) != polariteit.NEUTRAAL
                    ]
                    kansen = [
                        i
                        for i in ind_list
                        if not i["is_ongunstig"]
                        and (i.get("polariteit") or polariteit.uit_oud(i.get("score_type"))) != polariteit.NEUTRAAL
                    ]

                # Sorteer op absolute z-score dalend
                aandachtspunten.sort(key=lambda x: x["z_score_abs"], reverse=True)
                kansen.sort(key=lambda x: x["z_score_abs"], reverse=True)

                themas_output.append(
                    {
                        "thema_naam": th_naam,
                        "totaal_indicatoren": len(ind_list),
                        "totaal_aandachtspunten": len(aandachtspunten),
                        "totaal_kansen": len(kansen),
                        "top10_aandachtspunten": aandachtspunten[:10],
                        "top10_kansen": kansen[:10],
                    }
                )

            normatieve_z = []
            if kw_naam != "Samenstelling":
                for ind in alle_kw_indicatoren:
                    pol = ind.get("polariteit") or polariteit.uit_oud(ind.get("score_type"))
                    if pol == polariteit.NEUTRAAL:
                        continue
                    z_val = ind["z_score"]
                    if pol == polariteit.LAGER_IS_BETER:
                        normatieve_z.append(-z_val)
                    else:
                        normatieve_z.append(z_val)

            gem_z = round(sum(normatieve_z) / len(normatieve_z), 2) if normatieve_z else None
            n_ind = len(alle_kw_indicatoren)
            n_uitschieters = sum(1 for i in alle_kw_indicatoren if i["z_score_abs"] >= 1.0)
            if kw_naam == "Samenstelling":
                n_aandacht_sterk = 0
                n_kans_sterk = 0
                totaal_aandacht = 0
                totaal_kans = 0
            else:
                normatieve_indicatoren = [
                    i
                    for i in alle_kw_indicatoren
                    if (i.get("polariteit") or polariteit.uit_oud(i.get("score_type"))) != polariteit.NEUTRAAL
                ]
                n_aandacht_sterk = sum(
                    1 for i in normatieve_indicatoren if i["is_ongunstig"] and i["z_score_abs"] >= 1.0
                )
                n_kans_sterk = sum(
                    1 for i in normatieve_indicatoren if not i["is_ongunstig"] and i["z_score_abs"] >= 1.0
                )
                totaal_aandacht = sum(1 for i in normatieve_indicatoren if i["is_ongunstig"])
                totaal_kans = sum(1 for i in normatieve_indicatoren if not i["is_ongunstig"])

            kwadranten_output.append(
                {
                    "kwadrant_naam": kw_naam,
                    "kwadrant_kleur": kw_data["kwadrant_kleur"],
                    "gem_zscore": gem_z,
                    "n_indicatoren": n_ind,
                    "n_uitschieters": n_uitschieters,
                    "n_aandachtspunten": totaal_aandacht,
                    "n_kansen": totaal_kans,
                    "totaal_aandachtspunten": totaal_aandacht,
                    "totaal_kansen": totaal_kans,
                    "n_aandachtspunten_sterk": n_aandacht_sterk,
                    "n_kansen_sterk": n_kans_sterk,
                    "themas": themas_output,
                }
            )

        # 7. Bronverantwoording
        bronverantwoording = self.get_bronverantwoording_for_indicators(list(used_indicator_uuids))

        # 8. Methodologie object
        methodologie = {
            "aggregatie": "gewogen_gemiddelde",
            "gewicht_bron": "Indicator 'Inwoners' (CBS Kerncijfers Wijken en Buurten)",
            "referentie": referentie_label,
            "referentie_modus": referentie,
            "gemeente_code": gemeente_code,
            "gemeente_naam": gemeente_naam,
            "totaal_geselecteerde_buurten": len(gebied_ids),
            "waterbuurten_uitgesloten": waterbuurten,
            "actieve_buurten_telling": len(actieve_buurten),
            "fallback_buurten": fallback_buurten,
            "nul_inwoners_buurten": nul_inwoners_buurten,
            "totaal_inwoners_gebied": round(totaal_inwoners),
            "z_score_formule": "Z = (W - μ_ref) / σ_ref",
            "z_score_referentie": methodiek_beschrijving(),
            "statistisch_effect": "Het gewogen stadsgemiddelde (W) vlakt extreme pieken en dalen van individuele buurten uit. Hierdoor wijkt de Z-score van de stad structureel minder sterk af dan die van de meest extreme buurten. Dit is statistisch correct (de centrale limietstelling) en geen rekenfout.",
            "scoringtype_disclaimer": "De scoringstypen (+/+, +/-, -/-, -/+) en de resulterende duiding naar aandachtspunt of kans zijn onderdeel van het Kompas-model en nog onderhevig aan methodologische validatie.",
        }

        display_naam = deelgebied_naam or f"{len(actieve_buurten)} buurten"

        return {
            "deelgebied_naam": display_naam,
            "referentie_label": referentie_label,
            "referentie_modus": referentie,
            "gemeente_code": gemeente_code,
            "gemeente_naam": gemeente_naam,
            "totaal_buurten": len(gebied_ids),
            "buurten_met_data": len(actieve_buurten),
            "geselecteerde_buurten": list(inwoners_per_buurt.values()),
            "kwadranten": kwadranten_output,
            "methodologie": methodologie,
            "bronverantwoording": bronverantwoording,
        }

    def generate_deelgebied_svg_kaart(
        self,
        gebied_ids: list[str],
        referentie: str = "gemeente",
        gemeente_code: str | None = None,
        deelgebied_naam: str | None = None,
    ) -> str:
        """
        Genereert een inline SVG choropleet van de geselecteerde buurten,
        ingekleurd op de gewogen gemiddelde Z-score per buurt (over alle kwadranten).

        Returns: SVG string
        """
        import math

        # 1. Haal de analyse-data op zodat we Z-scores per buurt per indicator hebben
        payload = self.generate_deelgebied_payload(
            gebied_ids=gebied_ids, referentie=referentie, gemeente_code=gemeente_code, deelgebied_naam=deelgebied_naam
        )

        # 2. Bepaal max absolute Z-score per buurt (zelfde metric als Multi-Gebiedsdossier)
        buurt_zscores: dict[str, list[float]] = {}
        for kw in payload.get("kwadranten", []):
            for thema in kw.get("themas", []):
                for tab_key in ("top10_aandachtspunten", "top10_kansen"):
                    for ind in thema.get(tab_key, []):
                        for bd in ind.get("buurten_drilldown", []):
                            bid = bd["buurt_id"]
                            if bid not in buurt_zscores:
                                buurt_zscores[bid] = []
                            buurt_zscores[bid].append(abs(bd["buurt_z_score"]))

        buurt_max_z: dict[str, float] = {}
        for bid, scores in buurt_zscores.items():
            buurt_max_z[bid] = max(scores) if scores else 0.0

        # 3. Haal geometrieën op (WGS84 GeoJSON)
        geom_query = text("""
            SELECT g.id, g.naam,
                   ST_AsGeoJSON(ST_Transform(g.geom, 4326))::json AS geometry
            FROM gebieden g
            WHERE g.id = ANY(:gebied_ids)
              AND g.geom IS NOT NULL
              AND NOT public.is_waterbuurt(g.naam, g.metadata)
        """)
        geom_rows = [dict(r._mapping) for r in self.db.execute(geom_query, {"gebied_ids": gebied_ids}).fetchall()]

        if not geom_rows:
            return self._svg_empty_fallback(deelgebied_naam or "Geen data")

        # 4. Verzamel alle coördinaten voor bounding box
        all_coords = []
        features = []
        for row in geom_rows:
            geom = row["geometry"]
            coords_list = self._extract_polygon_coords(geom)
            all_coords.extend(coords_list)
            z_abs = buurt_max_z.get(str(row["id"]), 0.0)
            features.append(
                {
                    "id": str(row["id"]),
                    "naam": row["naam"],
                    "geometry": geom,
                    "z_score_abs": z_abs,
                    "kleur": self._get_zscore_kleur(z_abs, z_abs >= 1.0),
                }
            )

        if not all_coords:
            return self._svg_empty_fallback(deelgebied_naam or "Geen data")

        # 5. Bounding box berekenen
        lons = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        # Padding (5%)
        pad_lon = (max_lon - min_lon) * 0.05 or 0.001
        pad_lat = (max_lat - min_lat) * 0.05 or 0.001
        min_lon -= pad_lon
        max_lon += pad_lon
        min_lat -= pad_lat
        max_lat += pad_lat

        # 6. SVG viewport
        svg_w, svg_h = 400, 320

        def lon_to_x(lon):
            return (lon - min_lon) / (max_lon - min_lon) * svg_w

        def lat_to_y(lat):
            # Pseudo-Mercator, Y geïnverteerd (SVG Y loopt naar beneden)
            def merc(lat_deg):
                return math.log(math.tan(math.pi / 4 + math.radians(lat_deg) / 2))

            y_min = merc(min_lat)
            y_max = merc(max_lat)
            y = merc(lat)
            return svg_h - ((y - y_min) / (y_max - y_min) * svg_h)

        # 7. SVG opbouwen — zelfde kleuren als Multi-Gebiedsdossier (_get_zscore_kleur)
        polygons_svg = []
        for feat in features:
            color = feat["kleur"]
            z_label = f"|Z| {feat['z_score_abs']:.2f}"
            title = f"{feat['naam']} ({z_label})"
            rings = self._geom_to_svg_rings(feat["geometry"], lon_to_x, lat_to_y)
            for ring_points in rings:
                points_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in ring_points)
                polygons_svg.append(
                    f'<polygon points="{points_str}" '
                    f'fill="{color}" stroke="#1a1f2e" stroke-width="0.8" opacity="0.9">'
                    f"<title>{html.escape(title)}</title></polygon>"
                )

        naam_label = deelgebied_naam or payload.get("deelgebied_naam", "")

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}"
  width="{svg_w}" height="{svg_h}" style="background:#0d1117;border-radius:8px;">
  <style>
    polygon {{ transition: opacity 0.2s; cursor: pointer; }}
    polygon:hover {{ opacity: 1; stroke-width: 1.6; stroke: #60a5fa; }}
    text {{ font-family: Inter, system-ui, sans-serif; }}
  </style>
  {"".join(polygons_svg)}
  <text x="8" y="16" fill="#9ca3af" font-size="11">{html.escape(naam_label)}</text>
  <!-- legenda — zelfde als Multi-Gebiedsdossier -->
  <g transform="translate(8, {svg_h - 18})">
    <rect x="0" y="0" width="10" height="10" fill="#8c96a0" rx="1.5"/>
    <text x="14" y="9" fill="#6b7280" font-size="7">In lijn</text>
    <rect x="48" y="0" width="10" height="10" fill="#d4b483" rx="1.5"/>
    <text x="62" y="9" fill="#6b7280" font-size="7">Licht</text>
    <rect x="90" y="0" width="10" height="10" fill="#c17c3e" rx="1.5"/>
    <text x="104" y="9" fill="#6b7280" font-size="7">Matig</text>
    <rect x="132" y="0" width="10" height="10" fill="#2b6ca3" rx="1.5"/>
    <text x="146" y="9" fill="#6b7280" font-size="7">Sterk</text>
    <rect x="174" y="0" width="10" height="10" fill="#1a3d5c" rx="1.5"/>
    <text x="188" y="9" fill="#6b7280" font-size="7">Extreem</text>
  </g>
</svg>'''

        return svg

    def _extract_polygon_coords(self, geojson: dict) -> list[list[float]]:
        """Extraheert alle [lon, lat] coördinaten uit een GeoJSON Polygon/MultiPolygon."""
        coords = []
        geom_type = geojson.get("type", "")
        if geom_type == "Polygon":
            for ring in geojson.get("coordinates", []):
                coords.extend(ring)
        elif geom_type == "MultiPolygon":
            for polygon in geojson.get("coordinates", []):
                for ring in polygon:
                    coords.extend(ring)
        return coords

    def _geom_to_svg_rings(self, geojson: dict, lon_to_x, lat_to_y) -> list[list[tuple]]:
        """Converteert GeoJSON Polygon/MultiPolygon naar lijsten van (x, y) punten voor SVG."""
        rings = []
        geom_type = geojson.get("type", "")
        if geom_type == "Polygon":
            for ring in geojson.get("coordinates", []):
                rings.append([(lon_to_x(c[0]), lat_to_y(c[1])) for c in ring])
        elif geom_type == "MultiPolygon":
            for polygon in geojson.get("coordinates", []):
                for ring in polygon:
                    rings.append([(lon_to_x(c[0]), lat_to_y(c[1])) for c in ring])
        return rings

    def _svg_empty_fallback(self, label: str) -> str:
        """Geeft een fallback SVG terug als er geen geometrieën beschikbaar zijn."""
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 320"
  width="400" height="320" style="background:#0d1117;border-radius:8px;">
  <text x="200" y="155" fill="#6b7280" font-size="13" text-anchor="middle"
    font-family="Inter, system-ui, sans-serif">Geen kaartdata beschikbaar</text>
  <text x="200" y="175" fill="#4b5563" font-size="11" text-anchor="middle"
    font-family="Inter, system-ui, sans-serif">{html.escape(label)}</text>
</svg>"""
