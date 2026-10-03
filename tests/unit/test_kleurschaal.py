"""
Unit test: kaartkleuring bij weinig gebieden of gelijke waarden (#161).

Zonder database: de visualisatieconfiguratie (kleurenschema, classificatie) wordt
vervangen door een vaste configuratie.
"""
import pytest

from omnitwin.services.color_scale_service import ColorScaleService

pytestmark = pytest.mark.unit

KLEUREN = {"min": "#000000", "mid": "#808080", "max": "#ffffff"}


def service(classificatie="quantile", klassen=7, score_type="+/+"):
    svc = ColorScaleService(db=None)
    svc.get_visualization_config = lambda _uuid: {
        "colors": KLEUREN,
        "klassen": klassen,
        "nodata_kleur": "#d1d5db",
        "classificatie": classificatie,
        "score_type": score_type,
        "midpoint_waarde": None,
    }
    return svc


def kleuren(svc, waarden):
    ramp, breaks, _ = svc.compute_colors_for_data(waarden, "x")
    return ramp, [svc.get_color_for_value(w, ramp, breaks) for w in waarden]


def test_een_gebied_krijgt_neutrale_middenkleur():
    ramp, (kleur,) = kleuren(service(), [0.42])
    assert kleur == ramp[len(ramp) // 2]


def test_twee_gebieden_krijgen_de_uitersten():
    ramp, k = kleuren(service(), [0.37, 0.47])
    assert k == [ramp[0], ramp[-1]]


def test_drie_gebieden_krijgen_drie_kleuren():
    # het geval uit #161: drie Bolsward-buurten, 0,37-0,47 °C
    ramp, k = kleuren(service(), [0.37, 0.47, 0.42])
    assert k == [ramp[0], ramp[-1], ramp[len(ramp) // 2]]
    assert len(set(k)) == 3


@pytest.mark.parametrize("classificatie", ["quantile", "equal_interval", "jenks", "diverging_midpoint"])
def test_minder_unieke_waarden_dan_klassen_altijd_verschillende_kleuren(classificatie):
    waarden = [5.0, 1.0, 3.0, 2.0, 4.0]
    ramp, k = kleuren(service(classificatie), waarden)
    assert len(set(k)) == 5
    # oplopend in waarde = oplopend in de kleurenschaal
    volgorde = [ramp.index(c) for _, c in sorted(zip(waarden, k))]
    assert volgorde == sorted(volgorde)
    assert volgorde[0] == 0 and volgorde[-1] == len(ramp) - 1


def test_zeven_of_meer_waarden_gebruiken_de_classificatie():
    waarden = [float(i) for i in range(1, 15)]
    ramp, k = kleuren(service(), waarden)
    assert k[0] == ramp[0] and k[-1] == ramp[-1]
    assert len(set(k)) == 7
    volgorde = [ramp.index(c) for c in k]
    assert volgorde == sorted(volgorde)


def test_gelijke_waarden_krijgen_dezelfde_kleur():
    waarden = [1.0, 1.0, 2.0, 2.0, 2.0, 3.0]
    ramp, k = kleuren(service(), waarden)
    assert k[0] == k[1] and k[2] == k[3] == k[4]
    assert len(set(k)) == 3


def test_veel_gebieden_allemaal_gelijk_neutraal():
    ramp, k = kleuren(service(), [7.0] * 20)
    assert set(k) == {ramp[len(ramp) // 2]}


def test_lager_is_beter_draait_de_schaal_om():
    ramp_normaal, _ = kleuren(service(), [1.0, 2.0])
    ramp, k = kleuren(service(score_type="+/-"), [1.0, 2.0])
    assert ramp == list(reversed(ramp_normaal))
    assert k == [ramp[0], ramp[-1]]
