"""
Unit test: bevindingen rondleiding demo-omgeving (#246).

- De uitvoerder vat de leveringen per dataset samen met aantal per status en de reden,
  in plaats van 57x "overgeslagen" zonder uitleg.
- In-process installeren van een compat-dataset (swf-adapter-fme) zegt wat er wel moet.
"""
import pytest

from omnitwin import usecases as uc

pytestmark = pytest.mark.unit


def test_kort_telt_per_status_met_reden():
    res = [{"status": "overgeslagen", "melding": "route compat kan niet met --inproces"}] * 57
    assert uc._kort(res) == "57x overgeslagen (route compat kan niet met --inproces)"


def test_kort_meerdere_statussen_en_zonder_melding():
    res = [{"status": "geladen"}, {"status": "geladen"}, {"status": "afgekeurd", "melding": "schema"}, {"http": 501}]
    assert uc._kort(res) == "2x geladen, 1x afgekeurd (schema), 1x 501"


def test_kort_tekst_blijft_tekst():
    assert uc._kort("overgeslagen: bron ontbreekt") == "overgeslagen: bron ontbreekt"


def test_inproces_compat_noemt_de_weg_via_http(tmp_path):
    from omnitwin.laden.inproces import InprocesLaadApi
    api = InprocesLaadApi.__new__(InprocesLaadApi)  # geen database nodig voor deze tak
    pad = tmp_path / "x.json"
    pad.write_text("{}", encoding="utf-8")
    uit = api.lever("swf-monitor-definities", pad, route="compat")
    assert uit["status"] == "overgeslagen"
    assert "laad-API" in uit["melding"] and "machineclient" in uit["melding"]
