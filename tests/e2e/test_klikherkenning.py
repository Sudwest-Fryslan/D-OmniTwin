"""Klikherkenning van de kaart ruim genoeg voor trage pc's zonder GPU (#279)."""

import pytest

pytestmark = pytest.mark.e2e


def test_klikherkenning_ruim_genoeg(app_page):
    # deck.gl standaard 250 ms: op software-WebGL ging de klik verloren (gemeten in #278)
    tijd = app_page.evaluate("() => window.state.deckgl.eventManager.manager.get('click').options.time")
    assert tijd >= 1000
