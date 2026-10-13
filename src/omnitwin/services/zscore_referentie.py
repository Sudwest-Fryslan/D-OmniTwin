"""
Z-score-referentie (#66, #155)
==============================
Eén plek voor de parameters van de Z-score-referentiegroep. De berekening zelf
staat in SQL (db/schema/08_zscore_referentie.sql):

- zscore_referentie_waarden(...)  de referentieset, één waarde per gebied en indicator
- zscore_referentie_stats(...)    gemiddelde, standaarddeviatie en n per indicator
- zscore_gebieden(...)            Z-scores van gebieden t.o.v. die referentie
- zscore(waarde, gem, sd, n)      de formule
- is_waterbuurt(naam, metadata)   de ene definitie van waterbuurt (#155)

Methodiek: docs/3-data-engineering/zscore_methodiek.md
"""

from typing import Any

from omnitwin.fouten import GebruikersFout
from omnitwin.services import kleine_aantallen as ka

# Standaardwaarden (gelijk aan de DEFAULTs van de SQL-functies)
# 'zelfde_jaar': referentie = waarden in het jaar van de meest recente waarde van het
#   doelgebied (zonder doelgebied: meest recente jaar van de indicator). Zo werkten het
#   executive-rapport en Kompas top-buurten vóór #66.
# 'recentst_per_gebied': per gebied de meest recente waarde, ongeacht het jaar. Zo werkten
#   multi-gebied, thema-analyse, deelgebied en benchmark vóór #66.
# ⚠️ Zie docs/3-data-engineering/zscore_methodiek.md voor de afwijkingen t.o.v. de oude code.
JAARLOGICA_STANDAARD = "zelfde_jaar"
JAARLOGICA_OPTIES = ("zelfde_jaar", "recentst_per_gebied")
SCENARIO_STANDAARD = "current"

# Minimum-n bij 'zelfde_jaar' (#155): hebben minder gebieden een waarde in het jaar van
# het doelgebied, dan valt de referentie terug op 'recentst_per_gebied' en geeft
# zscore_gebieden referentie_terugval = true. Vijf is een pragmatische ondergrens: met
# minder gebieden zegt een steekproef-sd weinig en bepaalt één gebied het gemiddelde.
# 0 = nooit terugvallen. Niet te verwarren met de n-drempel voor kleine aantallen
# (waarnemingen per waarde, #325); beide staan in services/kleine_aantallen.py.
MIN_N_STANDAARD = ka.MIN_GEBIEDEN_REFERENTIE

# Referentiegroep: 'gemeente' = gebiedstype + gemeente (standaard), 'fryslan' = gebiedstype in de
# provincie organisatie.benchmark_provincie (#324; zonder instelling: alle gebieden van dat type)
REFERENTIE_STANDAARD = "gemeente"

# Gebiedstype van CBS-buurten (gebiedstypes.code), voor routes zonder doelgebied
CBS_BUURT_CODE = "CBS_BUURT"

# SQL-fragmenten met named parameters, voor gebruik in sqlalchemy.text()
SQL_ZSCORE_GEBIEDEN = """public.zscore_gebieden(
    CAST(:zs_gebied_ids AS varchar[]), CAST(:zs_gebiedstype_id AS uuid),
    CAST(:zs_gemeente_code AS varchar), CAST(:zs_jaarlogica AS text),
    CAST(:zs_scenario_id AS varchar), CAST(:zs_indicator_uuids AS uuid[]),
    CAST(:zs_min_n AS integer),
    CAST(:zs_provincie AS varchar))"""

SQL_REFERENTIE_STATS = """public.zscore_referentie_stats(
    CAST(:zs_gebiedstype_id AS uuid), CAST(:zs_gemeente_code AS varchar),
    CAST(:zs_jaarlogica AS text), CAST(:zs_scenario_id AS varchar),
    CAST(:zs_indicator_uuids AS uuid[]), CAST(:zs_min_n AS integer),
    CAST(:zs_provincie AS varchar))"""

SQL_REFERENTIE_WAARDEN = """public.zscore_referentie_waarden(
    CAST(:zs_gebiedstype_id AS uuid), CAST(:zs_gemeente_code AS varchar),
    CAST(:zs_jaarlogica AS text), CAST(:zs_scenario_id AS varchar),
    CAST(:zs_indicator_uuids AS uuid[]), CAST(:zs_min_n AS integer),
    CAST(:zs_provincie AS varchar))"""


def referentie_params(
    gebiedstype_id: Any,
    gemeente_code: str | None = None,
    gebied_ids: list | None = None,
    indicator_uuids: list | None = None,
    jaarlogica: str = JAARLOGICA_STANDAARD,
    scenario_id: str = SCENARIO_STANDAARD,
    min_n: int = MIN_N_STANDAARD,
    provincie: str | None = None,
) -> dict[str, Any]:
    """
    Bind-parameters voor de SQL-fragmenten hierboven.

    gemeente_code None = referentiegroep over alle gemeenten (alleen gebiedstype).
    provincie: alleen gemeenten in die provincie (gemeenten.provincie, #324); None = alle.
    gebied_ids None (bij zscore_gebieden) = alle gebieden van de referentiegroep.
    """
    if jaarlogica not in JAARLOGICA_OPTIES:
        raise GebruikersFout(f"Onbekende jaarlogica '{jaarlogica}', kies uit {JAARLOGICA_OPTIES}")
    return {
        "zs_gebied_ids": list(gebied_ids) if gebied_ids is not None else None,
        "zs_gebiedstype_id": str(gebiedstype_id),
        "zs_gemeente_code": gemeente_code,
        "zs_jaarlogica": jaarlogica,
        "zs_scenario_id": scenario_id,
        "zs_indicator_uuids": [str(u) for u in indicator_uuids] if indicator_uuids is not None else None,
        "zs_min_n": int(min_n),
        "zs_provincie": provincie,
    }


def bereken_zscore(waarde: float, gemiddelde: float, standaarddeviatie: float | None, n: int) -> float | None:
    """
    Python-tegenhanger van SQL zscore(), voor afgeleide waarden die niet in de
    database staan (zoals het gewogen deelgebiedsgemiddelde). None als er geen
    spreiding is: n < 2 of sd = 0. Integratietest borgt gelijkheid met de SQL.
    """
    if waarde is None or gemiddelde is None:
        return None
    if n is None or n < 2 or standaarddeviatie is None or standaarddeviatie <= 0:
        return None
    return (waarde - gemiddelde) / standaarddeviatie


def methodiek_beschrijving(
    jaarlogica: str = JAARLOGICA_STANDAARD, scenario_id: str = SCENARIO_STANDAARD
) -> dict[str, str]:
    """Korte, navolgbare beschrijving voor in rapport-payloads."""
    return {
        "formule": "Z = (waarde - gemiddelde_ref) / sd_ref (steekproef-sd)",
        "referentiegroep": "zelfde gebiedstype (+ gemeente bij referentie 'gemeente'), waterbuurten uitgesloten",
        "jaarlogica": jaarlogica,
        "minimum_n": (
            f"{MIN_N_STANDAARD}: bij minder gebieden met een waarde in hetzelfde jaar "
            "is de referentie de meest recente waarde per gebied (referentie_terugval)"
        ),
        "scenario_id": scenario_id,
        "kleine_aantallen": (
            "een waarde die op minder waarnemingen rust dan de drempel (standaard 10) "
            "telt niet mee in de referentie en krijgt geen Z-score"
        ),
        "randgevallen": "geen Z-score bij n < 2 of sd = 0, of als het gebied een waterbuurt is",
        "documentatie": "docs/3-data-engineering/zscore_methodiek.md",
    }
