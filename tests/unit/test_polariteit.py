"""
Unit test: één polariteitscodering (#120).

Kaart (kleurschaal), Kompas, percentielklassen, rapporten en chat leiden de richting af
met dezelfde regel (omnitwin.polariteit.uit_oud). Voorheen las de kaart '-/+' als
"hoger is beter" en de rapporten als "lager is beter".
"""

from pathlib import Path

import pytest

from omnitwin import polariteit as pol
from omnitwin.services import chat_datavraag as dv
from omnitwin.services import percentielklasse as pk
from omnitwin.services.kompas_service import KompasScoringService
from omnitwin.services.report_service import ReportDataService

pytestmark = pytest.mark.unit

V046 = Path(__file__).resolve().parents[2] / "db" / "migraties" / "V046__polariteit.sql"
V048 = Path(__file__).resolve().parents[2] / "db" / "migraties" / "V048__polariteit_kompas_audit.sql"
V049 = Path(__file__).resolve().parents[2] / "db" / "migraties" / "V049__polariteit_angst_depressie.sql"
V050 = Path(__file__).resolve().parents[2] / "db" / "migraties" / "V050__groep2_kompas_en_ao.sql"
V051 = Path(__file__).resolve().parents[2] / "db" / "migraties" / "V051__cbs_armoede_2024.sql"

# (score_type, interpretatie_logica) -> polariteit
GEVALLEN = [
    ("+/+", "pos_is_pos", pol.HOGER_IS_BETER),
    ("+=+", None, pol.HOGER_IS_BETER),
    ("+/-", "-/+", pol.LAGER_IS_BETER),
    ("-/+", None, pol.LAGER_IS_BETER),  # SWF-monitor: omkeren (#342)
    ("-/-", None, pol.LAGER_IS_BETER),
    ("-=-", None, pol.LAGER_IS_BETER),  # energielabel e.d.: lager getal = beter
    ("+/+", "neutraal", pol.NEUTRAAL),
    ("+/+", "N/A", pol.NEUTRAAL),
    (None, "-/+", pol.LAGER_IS_BETER),
    (None, None, pol.HOGER_IS_BETER),
    ("", "pos_is_pos", pol.HOGER_IS_BETER),
    ("positive_ascending", None, pol.HOGER_IS_BETER),
    ("positive_descending", None, pol.LAGER_IS_BETER),
    ("lager_is_beter", None, pol.LAGER_IS_BETER),
]


@pytest.mark.parametrize("score_type,logica,verwacht", GEVALLEN)
def test_uit_oud(score_type, logica, verwacht):
    assert pol.uit_oud(score_type, logica) == verwacht


@pytest.mark.parametrize("score_type", ["+/+", "+/-", "-/+", "-/-", "-=-", "+=+", None])
def test_alle_plekken_zelfde_richting(score_type):
    """Kaart/percentiel, Kompas-kleur, rapport en chat zeggen hetzelfde over één score_type."""
    lager = pol.uit_oud(score_type) == pol.LAGER_IS_BETER
    assert pk.hoger_is_beter(score_type) is not lager
    assert pol.lager_is_beter(score_type) is lager
    assert (dv.richting(score_type, None) == pol.LAGER_IS_BETER) is lager

    impact = ReportDataService._determine_impact(None, 1.5, score_type)
    assert impact == ("bovengemiddeld negatief" if lager else "bovengemiddeld positief")

    drempels = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    kompas = KompasScoringService()
    hoog = kompas.get_color_for_value(100.0, score_type=score_type, thresholds=drempels)
    laag = kompas.get_color_for_value(0.0, score_type=score_type, thresholds=drempels)
    assert (hoog, laag) == (("#D73027", "#1A9850") if lager else ("#1A9850", "#D73027"))


def test_score_type_van():
    assert pol.score_type_van(pol.LAGER_IS_BETER) == "+/-"
    assert pol.score_type_van(pol.HOGER_IS_BETER) == "+/+"
    assert pol.score_type_van(pol.NEUTRAAL) == "+/+"


def test_migratie_heeft_codelijst_en_dezelfde_regel():
    """V046: check-constraint met precies de codelijst, en de SQL-regel noemt dezelfde codes."""
    sql = V046.read_text(encoding="utf-8")
    assert "CHECK (polariteit IN ('hoger_is_beter', 'lager_is_beter', 'neutraal'))" in sql
    assert "('neutraal', 'n/a')" in sql and "('+/+', '+=+')" in sql
    assert "public." not in sql  # schema volgt het search_path (#137)
    assert set(pol.POLARITEITEN) == {"hoger_is_beter", "lager_is_beter", "neutraal"}


def test_migratie_v048_polariteit_kompas_audit():
    """V048 (#441): corrigeert verkeerde polariteit en typfout 'Veilgheid' zonder public.-prefix."""
    sql = V048.read_text(encoding="utf-8")
    assert "SET polariteit = 'lager_is_beter'" in sql
    assert "SET polariteit = 'neutraal'" in sql
    assert "SET naam = 'Veiligheid'" in sql
    assert "a4780646-844e-4221-b07a-b4f4ade25059" in sql  # Roken
    assert "0432fef2-83f2-4405-a457-08b89945ca86" in sql  # Obesitas
    assert "3c2d0ca0-3a6d-4f53-809f-f82fa9b9fd22" in sql  # Gemiddeld energielabel (score 1..9)
    assert "0ed37b61-f13d-446b-b108-70bb09af98e0" in sql  # Huisarts (afstand km)
    assert "public." not in sql  # schema volgt het search_path (#137)
    root = V048.resolve().parents[2]
    for rel in (
        "db/stuurdata/kompas_hierarchie.csv",
        "db/stuurdata/indicatoren_seed.json",
        "usecases/swf-kompasprofiel/data/kompasprofiel_volledig_kompas.json",
    ):
        assert "Veilgheid" not in (root / rel).read_text(encoding="utf-8"), rel


def test_migratie_v049_polariteit_angst_depressie():
    """V049 (#498): hernoemt 'Gezondheid' naar 'Hoog risico op angststoornis of depressie' met 'lager_is_beter' en RIVM-metadata."""
    sql = V049.read_text(encoding="utf-8")
    assert "polariteit = 'lager_is_beter'" in sql
    assert "SET naam = 'Hoog risico op angststoornis of depressie'" in sql
    assert "311a6449-b145-4678-b51e-ac4e342dd1bf" in sql
    assert "eenheid = '%'" in sql
    assert "Kessler-10" in sql
    assert "ontologische_beschrijving" in sql
    assert "public." not in sql  # schema volgt search_path (#137)

    root = V049.resolve().parents[2]
    ind_csv = (root / "db/stuurdata/indicatoren.csv").read_text(encoding="utf-8")
    assert "311a6449-b145-4678-b51e-ac4e342dd1bf,Hoog risico op angststoornis of depressie,%,,-/+" in ind_csv

    kompas_csv = (root / "db/stuurdata/kompas_hierarchie.csv").read_text(encoding="utf-8")
    assert "Hoog risico op angststoornis of depressie" in kompas_csv

    kompas_json = (root / "usecases/swf-kompasprofiel/data/kompasprofiel_volledig_kompas.json").read_text(
        encoding="utf-8"
    )
    assert "Hoog risico op angststoornis of depressie" in kompas_json

    seed_json = (root / "db/stuurdata/indicatoren_seed.json").read_text(encoding="utf-8")
    assert '"naam": "Hoog risico op angststoornis of depressie"' in seed_json
    assert '"naam": "Gezondheid"' not in seed_json

    syn_json = (root / "db/stuurdata/synoniemen.json").read_text(encoding="utf-8")
    assert "mentale gezondheid" in syn_json
    assert "Gezondheid" not in syn_json


def test_migratie_v050_groep2_kompas_en_ao():
    """V050 (#507): voegt Arbeidsongeschiktheid (AO) toe en koppelt AO + Netto arbeidsparticipatie in Kompas."""
    sql = V050.read_text(encoding="utf-8")
    assert "polariteit" in sql and "'lager_is_beter'" in sql
    assert "8d4c7f51-e8e8-5576-af88-650cee66e899" in sql  # Arbeidsongeschiktheid (AO)
    assert "b07f74eb-5117-4705-802c-597ba830d016" in sql  # Netto arbeidsparticipatie
    assert "public." not in sql  # schema volgt search_path (#137)

    root = V050.resolve().parents[2]
    kompas_csv = (root / "db/stuurdata/kompas_hierarchie.csv").read_text(encoding="utf-8")
    assert "Rondkomen,Werk,Netto arbeidsparticipatie,J," in kompas_csv
    assert "Rondkomen,Werk,Arbeidsongeschiktheid (AO),J," in kompas_csv

    syn_json = (root / "db/stuurdata/synoniemen.json").read_text(encoding="utf-8")
    assert "Arbeidsongeschiktheid (AO)" in syn_json


def test_migratie_v051_cbs_armoede_2024():
    """V051 (#507): voegt nieuwe CBS-armoede-indicatoren (vanaf 2024) toe onder Rondkomen > Armoede."""
    sql = V051.read_text(encoding="utf-8")
    assert "polariteit" in sql and "'lager_is_beter'" in sql
    assert "61b9c64b-9fc9-528c-ab91-fd39597c4080" in sql  # Personen in armoede
    assert "66ff2a84-d859-5b72-b308-ef6fce09d820" in sql  # Personen tot 25% boven armoedegrens
    assert "public." not in sql  # schema volgt search_path (#137)

    root = V051.resolve().parents[2]
    kompas_csv = (root / "db/stuurdata/kompas_hierarchie.csv").read_text(encoding="utf-8")
    assert "Rondkomen,Armoede,Personen in armoede,J," in kompas_csv
    assert "Rondkomen,Armoede,Personen tot 25% boven armoedegrens,J," in kompas_csv

    syn_json = (root / "db/stuurdata/synoniemen.json").read_text(encoding="utf-8")
    assert "Personen in armoede" in syn_json
    assert "Personen tot 25% boven armoedegrens" in syn_json
