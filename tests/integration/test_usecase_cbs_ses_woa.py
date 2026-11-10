"""
Acceptatietest use case cbs-ses-woa (TC-07-027): CBS SES-WOA en 4-jaars arbeidsverleden per buurt via de laad-API.

Specificatie: usecases/cbs-ses-woa/usecase.json en README.md. Installeert de use case met zijn
afhankelijkheden via de laad-API en voert elke controle uit het manifest uit. Overgeslagen
zolang de laad-API, een bron of de machineclient ontbreekt (zie usecase_laden.py).
"""

import pytest
from usecase_laden import controle_id, controles, installeer, vereisten, voer_uit

pytestmark = pytest.mark.integration

NAAM = "cbs-ses-woa"
UCS = vereisten(NAAM)


@pytest.fixture(scope="module")
def api():
    api, _ = installeer(NAAM, UCS)
    return api


@pytest.mark.parametrize("controle", controles(NAAM), ids=controle_id)
def test_controle(controle, api):
    voer_uit(controle, api, UCS, NAAM)

