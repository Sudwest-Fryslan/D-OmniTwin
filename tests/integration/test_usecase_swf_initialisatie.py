"""
Acceptatietest use case swf-initialisatie (TC-07-025): eerste SWF-vulling uit de export van de
lokale D-OmniTwin-database (#222 A1).

Specificatie: usecases/swf-initialisatie/usecase.json en README.md. Installeert de use case met zijn
afhankelijkheden via de laad-API en voert elke controle uit het manifest uit. Overgeslagen zolang
de laad-API, de export (SWF_EXPORT_DIR), de monitorexport (SWF_DUMP_DIR) of de machineclient
ontbreekt (zie usecase_laden.py). Het Kompas en de externe kaartlagen gaan via de beheerroute, die
nu alleen in-process bestaat (installeer --inproces); over HTTP worden ze hier niet geladen.
"""

import pytest
from usecase_laden import controle_id, controles, installeer, vereisten, voer_uit

pytestmark = pytest.mark.integration

NAAM = "swf-initialisatie"
UCS = vereisten(NAAM)


@pytest.fixture(scope="module")
def api():
    api, _ = installeer(NAAM, UCS)
    return api


@pytest.mark.parametrize("controle", controles(NAAM), ids=controle_id)
def test_controle(controle, api):
    voer_uit(controle, api, UCS, NAAM)
