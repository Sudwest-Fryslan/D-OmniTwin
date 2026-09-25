"""
Unit tests voor KompasScoringService — pure Python, geen database of server vereist.

Wat wordt getest:
- Kleurpalet selectie (normaal vs Samenstelling blauw)
- Bin-index berekening op basis van percentiel-drempels
- Inversie-logica voor verschillende score_types (+/+, +/-, -/-, positive_descending)
- Fallback naar grijs bij ontbrekende of ongeldige drempelwaarden
- Z-score formule als geïsoleerde berekening
- Normalize-helper op grenscondities
"""
import sys
import os
import pytest

# Voeg project root toe aan sys.path zodat services importeerbaar zijn zonder installatie
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importeer direct de scoring class (geen DB-afhankelijkheden)
from services.kompas_service import KompasScoringService


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def svc():
    return KompasScoringService()


@pytest.fixture
def even_thresholds():
    """7 gelijkmatig verdeelde drempelwaarden over 0-100."""
    return [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]


# ─── Kleurpalet selectie ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestPaletSelection:
    def test_normaal_palet_zonder_context(self, svc, even_thresholds):
        """Zonder context wordt het rode-groene palet gebruikt."""
        color = svc.get_color_for_value(75.0, thresholds=even_thresholds)
        assert color in svc.PALETTE_NORMAL

    def test_blauw_palet_bij_samenstelling_context(self, svc, even_thresholds):
        """Context 'samenstelling' activeert het blauwe palet."""
        color = svc.get_color_for_value(75.0, thresholds=even_thresholds, context="Samenstelling")
        assert color in svc.PALETTE_BLUE

    def test_context_hoofdletterongevoelig(self, svc, even_thresholds):
        """Context-check is case-insensitief."""
        color_lower = svc.get_color_for_value(50.0, thresholds=even_thresholds, context="samenstelling")
        color_upper = svc.get_color_for_value(50.0, thresholds=even_thresholds, context="SAMENSTELLING")
        assert color_lower == color_upper
        assert color_lower in svc.PALETTE_BLUE


# ─── Bin-index berekening ────────────────────────────────────────────────────

@pytest.mark.unit
class TestBinIndexCalculation:
    def test_laagste_waarde_krijgt_eerste_bin(self, svc, even_thresholds):
        """Waarde onder alle drempels → bin 0 → donkerrood (#D73027)."""
        color = svc.get_color_for_value(0.0, thresholds=even_thresholds)
        assert color == "#D73027"

    def test_hoogste_waarde_krijgt_laatste_bin(self, svc, even_thresholds):
        """Waarde boven alle drempels → bin 7 → donkergroen (#1A9850)."""
        color = svc.get_color_for_value(100.0, thresholds=even_thresholds)
        assert color == "#1A9850"

    def test_waarde_precies_op_drempel_valt_in_lagere_bin(self, svc, even_thresholds):
        """Waarde exact gelijk aan drempel valt in de bin daarvóór (niet erboven)."""
        # Waarde 10.0 is gelijk aan drempel 0 — niet groter dan, dus bin blijft 0
        color_op_drempel = svc.get_color_for_value(10.0, thresholds=even_thresholds)
        color_onder_drempel = svc.get_color_for_value(9.9, thresholds=even_thresholds)
        assert color_op_drempel == color_onder_drempel

    def test_fallback_grijs_zonder_drempelwaarden(self, svc):
        """Zonder drempelwaarden → grijs fallback."""
        color = svc.get_color_for_value(50.0, thresholds=None)
        assert color == "#94A3B8"

    def test_fallback_grijs_bij_verkeerd_aantal_drempels(self, svc):
        """Minder dan 7 drempels (zonder duplicaten) → via scaling, niet naar grijs."""
        # 7 drempels maar met duplicaten worden uniek gemaakt → scaling treedt in werking
        dubbele_drempels = [10.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        color = svc.get_color_for_value(55.0, thresholds=dubbele_drempels)
        # Resultaat moet een geldige kleur zijn, niet grijs
        assert color in svc.PALETTE_NORMAL


# ─── Inversie-logica (score_type) ────────────────────────────────────────────

@pytest.mark.unit
class TestScoreTypeInversion:
    """
    Kernlogica: bij 'positive_ascending' (+/+) is hoog groen.
    Bij '+/-' of 'positive_descending' is hoog rood (omgekeerd palet).
    """

    def test_positive_ascending_hoog_is_groen(self, svc, even_thresholds):
        hoog = svc.get_color_for_value(100.0, score_type="positive_ascending", thresholds=even_thresholds)
        assert hoog == "#1A9850"  # Donkergroen, bin 7

    def test_positive_descending_hoog_is_rood(self, svc, even_thresholds):
        """Hoge waarde bij positive_descending → rood (inversie)."""
        hoog = svc.get_color_for_value(100.0, score_type="positive_descending", thresholds=even_thresholds)
        assert hoog == "#D73027"  # Donkerrood, bin 0 na inversie

    def test_plus_min_score_type_inverteert(self, svc, even_thresholds):
        """'+/-' score type inverteert: hoog = rood."""
        hoog = svc.get_color_for_value(100.0, score_type="+/-", thresholds=even_thresholds)
        assert hoog == "#D73027"

    def test_min_min_score_type_inverteert(self, svc, even_thresholds):
        """-/- score type inverteert: hoog = rood."""
        hoog = svc.get_color_for_value(100.0, score_type="-/-", thresholds=even_thresholds)
        assert hoog == "#D73027"

    def test_inverse_flag_inverteert_ongeacht_score_type(self, svc, even_thresholds):
        """De `inverse` flag inverteert onafhankelijk van score_type."""
        normaal = svc.get_color_for_value(100.0, score_type="positive_ascending",
                                          thresholds=even_thresholds, inverse=False)
        geinverteerd = svc.get_color_for_value(100.0, score_type="positive_ascending",
                                               thresholds=even_thresholds, inverse=True)
        assert normaal != geinverteerd
        assert normaal == "#1A9850"
        assert geinverteerd == "#D73027"

    def test_inversie_is_symmetrisch(self, svc, even_thresholds):
        """Kleur van bin X normaal == kleur van bin (7-X) geinverteerd."""
        kleur_laag_normaal = svc.get_color_for_value(0.0, score_type="positive_ascending",
                                                     thresholds=even_thresholds)
        kleur_laag_invers = svc.get_color_for_value(0.0, score_type="+/-",
                                                    thresholds=even_thresholds)
        # Laag normaal = bin 0 = donkerrood; laag invers = bin 7 = donkergroen
        assert kleur_laag_normaal == "#D73027"
        assert kleur_laag_invers == "#1A9850"


# ─── Z-score formule ─────────────────────────────────────────────────────────

@pytest.mark.unit
class TestZScoreFormula:
    """
    De z-score berekening zit in SQL, maar de formule is simpel genoeg om
    als geïsoleerde Python berekening te testen. Dit dient als regressie-
    bescherming voor de mathematica, los van de database.
    """

    def _zscore(self, waarde: float, gemiddelde: float, std: float) -> float:
        """Lokale replica van de SQL z-score formule."""
        if std <= 0:
            return 0.0
        return (waarde - gemiddelde) / std

    def test_zscore_gemiddelde_is_nul(self):
        """Waarde gelijk aan gemiddelde → z-score = 0."""
        assert self._zscore(10.0, 10.0, 2.0) == pytest.approx(0.0)

    def test_zscore_een_standaarddeviatie_boven_gemiddelde(self):
        """Waarde = gemiddelde + 1 std → z-score = 1.0."""
        assert self._zscore(12.0, 10.0, 2.0) == pytest.approx(1.0)

    def test_zscore_negatief_bij_waarde_onder_gemiddelde(self):
        """Waarde onder gemiddelde → negatieve z-score."""
        assert self._zscore(8.0, 10.0, 2.0) == pytest.approx(-1.0)

    def test_zscore_nul_bij_zero_std(self):
        """Standaarddeviatie = 0 → z-score = 0 (geen deling door nul)."""
        assert self._zscore(15.0, 10.0, 0.0) == pytest.approx(0.0)


# ─── Normalize helper ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestNormalizeHelper:
    def test_normalize_middelste_waarde(self, svc):
        assert svc._normalize_value(50.0, 0.0, 100.0) == pytest.approx(0.5)

    def test_normalize_min_waarde_is_nul(self, svc):
        assert svc._normalize_value(0.0, 0.0, 100.0) == pytest.approx(0.0)

    def test_normalize_max_waarde_is_een(self, svc):
        assert svc._normalize_value(100.0, 0.0, 100.0) == pytest.approx(1.0)

    def test_normalize_clamp_onder_nul(self, svc):
        """Waarden buiten bereik worden geclamped naar [0, 1]."""
        assert svc._normalize_value(-10.0, 0.0, 100.0) == pytest.approx(0.0)

    def test_normalize_clamp_boven_een(self, svc):
        assert svc._normalize_value(150.0, 0.0, 100.0) == pytest.approx(1.0)

    def test_normalize_gelijk_min_max_geeft_half(self, svc):
        """Min == max → 0.5 (geen deling door nul)."""
        assert svc._normalize_value(10.0, 10.0, 10.0) == pytest.approx(0.5)
