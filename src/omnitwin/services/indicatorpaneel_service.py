"""
Indicatorpaneel en CSV-export (#258)
====================================
Eén indicator, bekeken voor een selectie gebieden: beschrijving, eenheid, bron/jaargang/licentie,
de waarde per gebied, het gemeentegemiddelde en dezelfde gegevens als CSV.

Onderdrukking (n onder de drempel, `percentielklasse.N_DREMPEL`): de waarde gaat niet naar buiten,
niet in JSON en niet in de CSV. Het gebied staat er wel, met `waarde` leeg en status `onderdrukt`.
Daarom bouwt de server de CSV (en niet de browser uit de kaartdata): paneel en export lezen
dezelfde rijen, met dezelfde onderdrukking.

Gemeentegemiddelde: het ongewogen gemiddelde van de referentiegroep van de Z-score en de
percentielklasse (`zscore_referentie_waarden`, #66): zelfde gebiedstype, zelfde gemeente, zelfde
jaar, zonder waterbuurten en zonder onderdrukte waarden. Ongewogen: elk gebied telt één keer,
ongeacht het aantal inwoners. Dat is iets anders dan de waarde van de gemeente als geheel.

Bron, jaargang en licentie komen uit de registratie van de dataset (DCAT-beschrijving in
`laden.datasets`, via `gebied_data.levering_id`), anders uit `gebied_data.bron` of `indicatoren.bron`.
"""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import text

from omnitwin.fouten import GebruikersFout
from omnitwin.services import percentielklasse as pk

MAX_GEBIEDEN = 2000
GEBIED_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")

CSV_KOLOMMEN = ["gebied-code", "gebied-naam", "indicator", "jaar", "waarde", "eenheid", "bron", "status"]

# Licentie-URI's die vaak voorkomen, als korte naam; een onbekende URI blijft staan
LICENTIES = {
    "http://creativecommons.org/licenses/by/4.0/": "CC BY 4.0",
    "https://creativecommons.org/licenses/by/4.0/": "CC BY 4.0",
    "http://creativecommons.org/publicdomain/zero/1.0/": "CC0 1.0",
    "https://creativecommons.org/publicdomain/zero/1.0/": "CC0 1.0",
    "http://creativecommons.org/publicdomain/mark/1.0/": "Publiek domein",
    "https://creativecommons.org/publicdomain/mark/1.0/": "Publiek domein",
}


# ── Invoer ───────────────────────────────────────────────────────────────────

def lees_gebied_ids(waarde: Optional[str]) -> List[str]:
    """Kommagescheiden gebied-id's, ontdubbeld met behoud van volgorde."""
    if not waarde:
        return []
    ids: List[str] = []
    for deel in waarde.split(","):
        deel = deel.strip()
        if not deel:
            continue
        if not GEBIED_ID.match(deel):
            raise GebruikersFout("Ongeldige gebied-id in gebied_ids.")
        if deel not in ids:
            ids.append(deel)
    if len(ids) > MAX_GEBIEDEN:
        raise GebruikersFout(f"Te veel gebieden: maximaal {MAX_GEBIEDEN}.")
    return ids


# ── Opmaak ───────────────────────────────────────────────────────────────────

def getal_nl(waarde: Any, decimalen: int = 6) -> str:
    """Getal met decimale komma, zonder duizendtalscheiding of exponent; None = leeg."""
    if waarde is None:
        return ""
    d = waarde if isinstance(waarde, Decimal) else Decimal(repr(round(float(waarde), decimalen)))
    tekst = format(d, "f")
    if "." in tekst:
        tekst = tekst.rstrip("0").rstrip(".")
    if tekst in ("-0", ""):
        tekst = "0"
    return tekst.replace(".", ",")


def veilige_tekst(waarde: Any) -> str:
    """Tekst voor een CSV-cel: geen formule in een spreadsheet (CSV-injectie)."""
    if waarde is None:
        return ""
    tekst = str(waarde)
    if tekst[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + tekst
    return tekst


def licentie_naam(uri: Optional[str]) -> Optional[str]:
    if not uri:
        return None
    return LICENTIES.get(uri.strip(), uri.strip())


def _tekst(waarde: Any) -> Optional[str]:
    """DCAT-veld als tekst: string, {'@id'|'@value'|'foaf:name'|'vcard:fn'} of lijst."""
    if waarde is None:
        return None
    if isinstance(waarde, str):
        return waarde.strip() or None
    if isinstance(waarde, list):
        return _tekst(waarde[0]) if waarde else None
    if isinstance(waarde, dict):
        for sleutel in ("foaf:name", "vcard:fn", "@value", "@id"):
            if waarde.get(sleutel):
                return _tekst(waarde[sleutel])
    return None


def uitgever_naam(waarde: Any) -> Optional[str]:
    """Uitgever als leesbare naam: een URI wordt de domeinnaam (https://www.rivm.nl/ -> rivm.nl)."""
    tekst = _tekst(waarde)
    if tekst and re.match(r"^https?://", tekst):
        from urllib.parse import urlsplit
        host = urlsplit(tekst).hostname or tekst
        return host[4:] if host.startswith("www.") else host
    return tekst


def gemiddelde(waarden: Sequence[float]) -> Optional[float]:
    return sum(waarden) / len(waarden) if waarden else None


def bron_label(bron: Dict[str, Any]) -> str:
    """Korte bronvermelding voor een CSV-regel: titel (uitgever), licentie."""
    deel = bron.get("titel") or bron.get("bron") or ""
    if bron.get("uitgever") and bron["uitgever"] not in deel:
        deel = f"{deel} ({bron['uitgever']})" if deel else bron["uitgever"]
    if bron.get("licentie"):
        deel = f"{deel}, {bron['licentie']}" if deel else bron["licentie"]
    return deel


def maak_csv(paneel: Dict[str, Any]) -> str:
    """CSV (UTF-8 met BOM, puntkomma, decimale komma) van een paneel uit `IndicatorpaneelService.paneel`."""
    ind = paneel["indicator"]
    bronnen = {b["sleutel"]: b for b in paneel["bronnen"]}
    uit = io.StringIO()
    w = csv.writer(uit, delimiter=";", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(CSV_KOLOMMEN)
    for g in paneel["gebieden"]:
        bron = bronnen.get(g.get("bronSleutel"))
        w.writerow([
            veilige_tekst(g["id"]), veilige_tekst(g["naam"]), veilige_tekst(ind["naam"]),
            g["jaar"] if g["jaar"] is not None else "", getal_nl(g["waarde"]),
            veilige_tekst(ind.get("eenheid")), veilige_tekst(bron_label(bron) if bron else ""), g["status"],
        ])
    for gm in paneel["gemeentegemiddelden"]:
        w.writerow([
            veilige_tekst(gm["gemeenteCode"]),
            veilige_tekst(f"Gemiddelde {gm['gemeenteNaam']} ({gm['aantalGebieden']} gebieden)"),
            veilige_tekst(ind["naam"]), gm["jaar"] if gm["jaar"] is not None else "",
            getal_nl(gm["waarde"]), veilige_tekst(ind.get("eenheid")), "", "gemeentegemiddelde",
        ])
    return "﻿" + uit.getvalue()


def csv_bestandsnaam(paneel: Dict[str, Any], datum: str) -> str:
    code = paneel["indicator"].get("code") or "indicator"
    code = re.sub(r"[^A-Za-z0-9_-]+", "-", code).strip("-") or "indicator"
    return f"indicator-{code}-{datum}.csv"


# ── Database ─────────────────────────────────────────────────────────────────

_SQL_INDICATOR = text("""
    SELECT uuid::text AS uuid, naam, code, omschrijving, ontologische_beschrijving, eenheid,
           COALESCE(score_type, '+/+') AS score_type, bron
    FROM indicatoren WHERE uuid = CAST(:ind AS uuid)
""")

# Waarde per gebied: in het gekozen jaar, of de recentste (scenario current)
_SQL_WAARDEN = text("""
    SELECT g.id, g.naam, g.gemeente_code, g.gebiedstype_id::text AS gebiedstype_id,
           public.is_waterbuurt(g.naam, g.metadata) AS is_waterbuurt,
           w.waarde, w.jaar, w.n, w.bron, w.levering_id::text AS levering_id
    FROM gebieden g
    LEFT JOIN LATERAL (
        SELECT gd.waarde, gd.jaar, gd.n, gd.bron, gd.levering_id
        FROM gebied_data gd
        WHERE gd.gebied_id = g.id AND gd.indicator_uuid = CAST(:ind AS uuid)
          AND COALESCE(gd.scenario_id, 'current') = 'current'
          AND (CAST(:jaar AS integer) IS NULL OR gd.jaar = CAST(:jaar AS integer))
        ORDER BY gd.jaar DESC NULLS LAST, gd.datum DESC NULLS LAST
        LIMIT 1
    ) w ON true
    WHERE (CAST(:ids AS varchar[]) IS NOT NULL AND g.id = ANY(CAST(:ids AS varchar[])))
       OR (CAST(:ids AS varchar[]) IS NULL AND g.gebiedstype_id = CAST(:gt AS uuid)
           AND (CAST(:gm AS varchar) IS NULL OR g.gemeente_code = CAST(:gm AS varchar)))
    ORDER BY g.naam
""")

# Bronnen van de indicator: per dataset (of losse bronvermelding) de jaargangen
_SQL_BRONNEN = text("""
    SELECT lv.dataset_id, ds.beschrijving, gd.bron, array_agg(DISTINCT gd.jaar ORDER BY gd.jaar) AS jaren
    FROM gebied_data gd
    LEFT JOIN laden.leveringen lv ON lv.id = gd.levering_id
    LEFT JOIN laden.datasets ds ON ds.id = lv.dataset_id
    WHERE gd.indicator_uuid = CAST(:ind AS uuid)
      AND COALESCE(gd.scenario_id, 'current') = 'current'
      AND gd.jaar IS NOT NULL
    GROUP BY lv.dataset_id, ds.beschrijving, gd.bron
    ORDER BY max(gd.jaar) DESC
    LIMIT 20
""")

_SQL_RECENTSTE_JAAR = text("""
    SELECT max(gd.jaar) FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
    WHERE gd.indicator_uuid = CAST(:ind AS uuid) AND g.gebiedstype_id = CAST(:gt AS uuid)
      AND g.gemeente_code = CAST(:gm AS varchar) AND COALESCE(gd.scenario_id, 'current') = 'current'
""")

_SQL_GEMEENTEN = text("SELECT code, naam FROM gemeenten WHERE code = ANY(CAST(:codes AS varchar[]))")


class IndicatorpaneelService:
    def __init__(self, db):
        self.db = db

    def _indicator(self, indicator_uuid: str) -> Dict[str, Any]:
        rij = self.db.execute(_SQL_INDICATOR, {"ind": indicator_uuid}).mappings().first()
        if rij is None:
            raise GebruikersFout("Onbekende indicator.")
        return {
            "uuid": rij["uuid"], "naam": rij["naam"], "code": rij["code"],
            "beschrijving": rij["omschrijving"] or rij["ontologische_beschrijving"],
            "eenheid": rij["eenheid"], "scoreType": rij["score_type"], "bron": rij["bron"],
        }

    def _bronnen(self, indicator_uuid: str, indicator_bron: Optional[str]) -> List[Dict[str, Any]]:
        bronnen = []
        for r in self.db.execute(_SQL_BRONNEN, {"ind": indicator_uuid}).mappings():
            b = r["beschrijving"] or {}
            sleutel = f"dataset:{r['dataset_id']}" if r["dataset_id"] else f"bron:{r['bron'] or indicator_bron or ''}"
            bestaand = next((x for x in bronnen if x["sleutel"] == sleutel), None)
            jaren = [j for j in (r["jaren"] or []) if j is not None]
            if bestaand:
                bestaand["jaargangen"] = sorted(set(bestaand["jaargangen"]) | set(jaren))
                continue
            bronnen.append({
                "sleutel": sleutel,
                "dataset": r["dataset_id"],
                "titel": _tekst(b.get("dct:title")),
                "uitgever": uitgever_naam(b.get("dct:publisher")),
                "licentie": licentie_naam(_tekst(b.get("dct:license"))),
                "licentieUri": _tekst(b.get("dct:license")),
                "bron": r["bron"] or indicator_bron,
                "jaargangen": jaren,
            })
        if not bronnen and indicator_bron:
            bronnen.append({"sleutel": f"bron:{indicator_bron}", "dataset": None, "titel": None, "uitgever": None,
                            "licentie": None, "licentieUri": None, "bron": indicator_bron, "jaargangen": []})
        return bronnen

    def _bron_sleutel(self, r, datasets: Dict[str, Optional[str]], indicator_bron: Optional[str]) -> Optional[str]:
        if r["levering_id"] and datasets.get(r["levering_id"]):
            return f"dataset:{datasets[r['levering_id']]}"
        if r["waarde"] is None:
            return None
        return f"bron:{r['bron'] or indicator_bron or ''}"

    def paneel(
        self,
        indicator_uuid: str,
        gebied_ids: Iterable[str] = (),
        jaar: Optional[int] = None,
        gebiedstype_id: Optional[str] = None,
        gemeente_code: Optional[str] = None,
        drempel: int = pk.N_DREMPEL,
        met_gebieden: bool = True,
    ) -> Dict[str, Any]:
        """Indicator, bronnen, waarde per gebied (onderdrukt: leeg) en gemeentegemiddelden.

        Met gebied_ids: die gebieden. Zonder: alle gebieden van gebiedstype_id (in gemeente_code),
        zoals op de kaart (met_gebieden=False: dan alleen het gemeentegemiddelde); zonder beide alleen
        indicator en bronnen."""
        ids = list(gebied_ids)
        ind = self._indicator(indicator_uuid)
        bronnen = self._bronnen(indicator_uuid, ind["bron"])

        rijen: List[Dict[str, Any]] = []
        if ids or (gebiedstype_id and met_gebieden):
            rijen = [dict(r) for r in self.db.execute(_SQL_WAARDEN, {
                "ind": indicator_uuid, "jaar": jaar, "ids": ids or None,
                "gt": gebiedstype_id, "gm": gemeente_code,
            }).mappings()]
        if ids:  # volgorde van de selectie aanhouden
            volgorde = {g: i for i, g in enumerate(ids)}
            rijen.sort(key=lambda r: volgorde.get(r["id"], len(volgorde)))

        leveringen = sorted({r["levering_id"] for r in rijen if r["levering_id"]})
        datasets: Dict[str, Optional[str]] = {}
        if leveringen:
            datasets = {r[0]: r[1] for r in self.db.execute(text(
                "SELECT id::text, dataset_id FROM laden.leveringen WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": leveringen})}

        gebieden = []
        for r in rijen:
            if r["waarde"] is None:
                status, waarde = "geen-data", None
            elif pk.is_onderdrukt(r["n"], drempel):
                status, waarde = "onderdrukt", None
            else:
                status, waarde = "gemeten", float(r["waarde"])
            gebieden.append({
                "id": r["id"], "naam": r["naam"], "gemeenteCode": r["gemeente_code"],
                "jaar": r["jaar"], "waarde": waarde, "status": status,
                "waterbuurt": bool(r["is_waterbuurt"]),
                "bronSleutel": self._bron_sleutel(r, datasets, ind["bron"]) if status != "geen-data" else None,
            })

        return {
            "indicator": ind,
            "bronnen": bronnen,
            "gebieden": gebieden,
            "gemeentegemiddelden": self._gemeentegemiddelden(indicator_uuid, rijen, jaar, gebiedstype_id,
                                                            gemeente_code, drempel),
            "drempel": drempel,
        }

    def _gemeentegemiddelden(self, indicator_uuid, rijen, jaar, gebiedstype_id, gemeente_code, drempel):
        """Per (gebiedstype, gemeente, jaar) van de getoonde gebieden het ongewogen gemiddelde
        van de referentiegroep. Zonder gebieden: van gebiedstype_id en gemeente_code (of de eigen
        gemeente), in het gekozen of recentste jaar."""
        groepen = set()
        for r in rijen:
            if r["gemeente_code"] and r["gebiedstype_id"] and (r["jaar"] is not None or jaar is not None):
                groepen.add((r["gebiedstype_id"], r["gemeente_code"], jaar if jaar is not None else r["jaar"]))
        if not rijen and gebiedstype_id:
            gm = gemeente_code
            if not gm:
                from omnitwin.services.organisatie import eigen_gemeente_code
                gm = eigen_gemeente_code(self.db)
            if gm:
                groepen.add((gebiedstype_id, gm, jaar))
        if not groepen:
            return []

        namen = {r[0]: r[1] for r in self.db.execute(_SQL_GEMEENTEN, {"codes": sorted({g[1] for g in groepen})})}
        uit = []
        for gt, gm, j in sorted(groepen, key=lambda g: (g[1], g[2] or 0, g[0])):
            if j is None:  # recentste jaar met een waarde in deze gemeente en dit gebiedstype
                j = self.db.execute(_SQL_RECENTSTE_JAAR, {"ind": indicator_uuid, "gt": gt, "gm": gm}).scalar()
                if j is None:
                    continue
            ref = pk.referentie_waarden(self.db, gt, [gm], [indicator_uuid], jaar=j, drempel=drempel)
            waarden = ref.get((gm, indicator_uuid), [])
            uit.append({
                "gemeenteCode": gm, "gemeenteNaam": namen.get(gm, gm), "gebiedstypeId": gt, "jaar": j,
                "waarde": gemiddelde(waarden), "aantalGebieden": len(waarden),
            })
        return uit
