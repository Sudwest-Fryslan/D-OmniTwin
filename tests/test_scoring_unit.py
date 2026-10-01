"""
Unit tests voor KompasScoringService — pure Python, geen database of server vereist.

Wat wordt getest:
- Kleurpalet selectie (normaal vs Samenstelling blauw)
- Bin-index berekening op basis van percentiel-drempels
- Inversie-logica voor verschillende score_types (+/+, +/-, -/-, positive_descending)
- Fallback naar grijs bij ontbrekende of ongeldige drempelwaarden
- Z-score formule (services.zscore_referentie.bereken_zscore) en referentieparameters
- Normalize-helper op grenscondities
"""
import sys
import os
import pytest

# Voeg project root toe aan sys.path zodat services importeerbaar zijn zonder installatie
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importeer direct de scoring class (geen DB-afhankelijkheden)
from omnitwin.services.kompas_service import KompasScoringService
from omnitwin.services.zscore_referentie import JAARLOGICA_STANDAARD, MIN_N_STANDAARD, bereken_zscore, referentie_params


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
    De Z-score zit in SQL (zscore() in init_data/schema/08_zscore_referentie.sql).
    Hier wordt de Python-tegenhanger getest die de services gebruiken voor
    afgeleide waarden (gewogen deelgebiedsgemiddelde). Dat beide gelijk
    rekenen, borgt tests/integration/test_zscore_referentie.py tegen de database.
    """

    def test_zscore_gemiddelde_is_nul(self):
        """Waarde gelijk aan gemiddelde → z-score = 0."""
        assert bereken_zscore(10.0, 10.0, 2.0, 5) == pytest.approx(0.0)

    def test_zscore_een_standaarddeviatie_boven_gemiddelde(self):
        """Waarde = gemiddelde + 1 std → z-score = 1.0."""
        assert bereken_zscore(12.0, 10.0, 2.0, 5) == pytest.approx(1.0)

    def test_zscore_negatief_bij_waarde_onder_gemiddelde(self):
        """Waarde onder gemiddelde → negatieve z-score."""
        assert bereken_zscore(8.0, 10.0, 2.0, 5) == pytest.approx(-1.0)

    def test_zscore_geen_waarde_bij_zero_std(self):
        """Standaarddeviatie = 0 → geen Z-score (geen deling door nul)."""
        assert bereken_zscore(15.0, 10.0, 0.0, 5) is None

    def test_zscore_geen_waarde_bij_n_kleiner_dan_2(self):
        """Eén gebied in de referentie → geen Z-score."""
        assert bereken_zscore(15.0, 15.0, None, 1) is None


@pytest.mark.unit
class TestReferentieParams:
    def test_standaardwaarden(self):
        p = referentie_params("afba67cb-6b38-4723-9c95-102a22d5b38a", "1900", gebied_ids=["BU19000002"])
        assert p["zs_jaarlogica"] == JAARLOGICA_STANDAARD == "zelfde_jaar"
        assert p["zs_scenario_id"] == "current"
        assert p["zs_gemeente_code"] == "1900"
        assert p["zs_gebied_ids"] == ["BU19000002"]
        assert p["zs_indicator_uuids"] is None
        assert p["zs_min_n"] == MIN_N_STANDAARD == 5

    def test_minimum_n_instelbaar(self):
        """#155: minimum-n bij zelfde_jaar; 0 = nooit terugvallen."""
        p = referentie_params("afba67cb-6b38-4723-9c95-102a22d5b38a", min_n=0)
        assert p["zs_min_n"] == 0

    def test_zonder_gemeente_is_alle_gemeenten(self):
        p = referentie_params("afba67cb-6b38-4723-9c95-102a22d5b38a")
        assert p["zs_gemeente_code"] is None
        assert p["zs_gebied_ids"] is None

    def test_alternatieve_jaarlogica(self):
        p = referentie_params("afba67cb-6b38-4723-9c95-102a22d5b38a", jaarlogica="recentst_per_gebied")
        assert p["zs_jaarlogica"] == "recentst_per_gebied"

    def test_onbekende_jaarlogica_geeft_fout(self):
        with pytest.raises(ValueError):
            referentie_params("afba67cb-6b38-4723-9c95-102a22d5b38a", jaarlogica="alle_jaren")


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
