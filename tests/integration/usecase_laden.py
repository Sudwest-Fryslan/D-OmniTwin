"""
Gedeelde opzet voor de acceptatietests van de use cases die via de laad-API laden
(tests/integration/test_usecase_<naam>.py).

Een test installeert de use case met zijn afhankelijkheden (python -m omnitwin.usecases)
en voert de controles uit het manifest uit, elk als eigen test. Overgeslagen zolang:
- de laad-API er niet is (GET /api/laden/v1/openapi.json geeft geen 200);
- een benodigde bron ontbreekt (SWF_DUMP_DIR, SWF_DOCS_DIR, SWF_GEO_DIR);
- er geen machineclient is (OMNITWIN_CLIENT_ID en OMNITWIN_CLIENT_SECRET).

Draaien tegen een stack met Keycloak en de laad-API:

    OMNITWIN_BASE_URL=http://localhost OMNITWIN_CLIENT_ID=usecase-test OMNITWIN_CLIENT_SECRET=... \\
    SWF_DUMP_DIR=... SWF_DOCS_DIR=... pytest -m integration tests/integration/test_usecase_swf_definities.py
"""

import os

import pytest

from omnitwin import usecases as uc

BRONVARIABELEN = ("SWF_DUMP_DIR", "SWF_DOCS_DIR", "SWF_GEO_DIR")


def benodigde_bronnen(naam, ucs):
    """Omgevingsvariabelen die de datasets van deze use case (en zijn afhankelijkheden) gebruiken."""
    nodig = set()
    for n in uc.volgorde([naam], ucs):
        for ds in ucs[n].get("datasets", []):
            tekst = (uc.USECASES_DIR / n / ds["registratie"]).read_text(encoding="utf-8")
            nodig |= {v for v in BRONVARIABELEN
                      if "${" + v + "}" in tekst or (v == "SWF_DUMP_DIR" and '"swf-dump"' in tekst)}
    return nodig


def vereisten(naam):
    """Slaat de module over als de laad-API, een bron of de machineclient ontbreekt."""
    ucs = uc.lees_usecases()
    if not uc.laad_api_beschikbaar():
        pytest.skip(f"laad-API nog niet beschikbaar ({uc.basis_url()}{uc.LAAD_API}/openapi.json)", allow_module_level=True)
    ontbreekt = sorted(v for v in benodigde_bronnen(naam, ucs) if not os.environ.get(v))
    if ontbreekt:
        pytest.skip(f"bron ontbreekt: {', '.join(ontbreekt)}", allow_module_level=True)
    if not (os.environ.get("OMNITWIN_CLIENT_ID") and os.environ.get("OMNITWIN_CLIENT_SECRET")):
        pytest.skip("geen machineclient (OMNITWIN_CLIENT_ID, OMNITWIN_CLIENT_SECRET)", allow_module_level=True)
    return ucs


def controles(naam):
    return uc.lees_usecases()[naam].get("controles", [])


def controle_id(c):
    return f"{c['type']}-{c.get('dataset') or c.get('pad') or c.get('stap', '')}"[:80]


def installeer(naam, ucs):
    api = uc.LaadApi()
    resultaat = uc.installeer([naam], ucs=ucs, api=api, ook_ontwerp=True)
    return api, resultaat


def voer_uit(c, api, ucs, naam):
    melding = uc.controle_api(c, api, ucs[naam])
    if melding and str(melding).startswith("overgeslagen"):
        pytest.skip(melding)
    assert melding is None, melding
