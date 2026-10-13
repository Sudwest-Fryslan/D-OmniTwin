"""Unit-tests voor tests/grounding.py (#88): getallen in AI-tekst tegen de brondata."""

import pytest

from tests.grounding import getallen_in_bron, getallen_in_tekst, grounding_melding, lezingen, ongegronde_getallen

pytestmark = pytest.mark.unit

BRON = {
    "metadata": {"gebied": "Workum", "referentie_kader": "Gemeente Súdwest-Fryslân"},
    "significante_domeinen": {
        "Sociaal": [
            {
                "indicator": "Eenzaamheid",
                "omschrijving": "Aandeel 65 jaar en ouder, per 1.000 inwoners",
                "meetjaar": 2024,
                "waarde": 53.95,
                "gemiddelde": 41.27,
                "z_score": -1.83,
                "eenheid": "%",
            },
            {"indicator": "Inwoners", "waarde": 1132.0, "gemiddelde": 0.12, "z_score": 2.4},
        ]
    },
}


@pytest.mark.parametrize(
    "tekst,verwacht",
    [
        ("53,95", {53.95}),
        ("53.95", {53.95}),
        ("1.132", {1132.0, 1.132}),
        ("1,132", {1.132, 1132.0}),
        ("1.132,5", {1132.5}),
        ("12", {12.0}),
    ],
)
def test_lezingen_nederlands_en_engels(tekst, verwacht):
    assert lezingen(tekst) == verwacht


def test_getallen_in_tekst_herkent_percentage_en_negeert_codes():
    gevonden = {raw: (w, pct) for raw, w, pct, _ in getallen_in_tekst("In BU19000002 is 12% eenzaam, de 2e buurt.")}
    assert list(gevonden) == ["12%"]
    assert gevonden["12%"] == ({12.0}, True)


def test_nederlandse_notaties_zijn_gegrond():
    tekst = "Het aandeel is 53,95 procent tegen 41,3 gemiddeld; de buurt telt 1.132 inwoners."
    assert ongegronde_getallen(tekst, BRON) == []


def test_afronden_op_0_of_1_decimaal_en_binnen_1_procent():
    assert ongegronde_getallen("ongeveer 54 en 41 en 1,8 en 1130", BRON) == []


def test_percentage_mag_als_fractie_in_bron_staan():
    assert ongegronde_getallen("12% van de inwoners", BRON) == []


def test_negatieve_bron_telt_op_absolute_waarde():
    assert ongegronde_getallen("een afwijking van 1,83", BRON) == []


def test_verzonnen_getallen_worden_gemeld():
    assert ongegronde_getallen("Het aandeel is 67% en er wonen 2.500 mensen, 53,95 klopt wel.", BRON) == [
        "67%",
        "2.500",
    ]


def test_triviale_getallen_worden_genegeerd():
    tekst = "In 2023 en 2026 zijn 3 punten opvallend; samengevat in 80 woorden."
    assert ongegronde_getallen(tekst, BRON) == []


def test_getallen_uit_strings_in_bron_tellen_mee():
    assert 1000.0 in getallen_in_bron(BRON)
    assert 65.0 in getallen_in_bron(BRON)
    assert ongegronde_getallen("per 1.000 inwoners van 65 jaar", BRON) == []


def test_melding_noemt_getal_en_context():
    tekst = "Er wonen 2.500 mensen."
    melding = grounding_melding("rapport", tekst, BRON, ongegronde_getallen(tekst, BRON))
    assert "'2.500'" in melding and "Er wonen 2.500 mensen" in melding and "53.95" in melding
