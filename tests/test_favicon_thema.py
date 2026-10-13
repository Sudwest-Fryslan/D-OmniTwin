"""Favicon in de kleuren van het organisatiethema (#249)."""

import pytest

from omnitwin.services.organisatie import BEELDMERK, beeldmerk_kleuren, beeldmerk_svg

pytestmark = pytest.mark.unit


def test_swf_thema_geeft_swf_kleuren():
    assert beeldmerk_kleuren("swf") == {"vlak": "#bf0042", "lijn": "#ffffff", "kern": "#ffffff"}


def test_favicon_svg_bevat_themakleuren():
    svg = beeldmerk_svg({"thema": "swf"})
    assert "var(--d-omnitwin-beeldmerk-vlak, #bf0042)" in svg
    assert "var(--d-omnitwin-beeldmerk-lijn, #3b82f6)" not in svg  # blauwe terugval vervangen


def test_standaardthema_en_onbekend_thema_houden_eigen_kleuren():
    standaard = BEELDMERK.read_text(encoding="utf-8")
    assert beeldmerk_svg({"thema": "d-omnitwin"}) == standaard
    assert beeldmerk_svg({"thema": "../../geheim"}) == standaard
    assert beeldmerk_svg(None) == standaard


def test_eigen_logo_zonder_tokens_ongewijzigd(tmp_path):
    eigen = tmp_path / "logo.svg"
    eigen.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#123456"/></svg>', encoding="utf-8")
    assert beeldmerk_svg({"thema": "swf"}, svg=eigen) == eigen.read_text(encoding="utf-8")


def test_paginas_gebruiken_het_thema_favicon():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for pad in ("templates/index.html", "static/help.html", "admin-panel/index.html"):
        assert 'href="/api/organisatie/beeldmerk.svg"' in (root / pad).read_text(encoding="utf-8"), pad
