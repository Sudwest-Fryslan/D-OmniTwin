"""
Unit-tests voor het AI-logboek (#313): de regel (geen gebruikersgegevens, afkappen), de hashketen
en de CSV-export. Dat de database dezelfde hash rekent als regelhash, toetst
tests/integration/test_ai_vrijgave_stack.py.
"""
import pytest

from omnitwin import ai_logboek
from omnitwin.version import __version__

pytestmark = pytest.mark.unit


def test_regel_zonder_gebruikersgegevens_en_afgekapt():
    r = ai_logboek.regel("A", "Chat", "uitgevoerd", taak="x" * 2000, bronnen=["u1", "u1", None, "u2"],
                         model="qwen3:4b", resultaat="y" * 5000)
    assert set(r) == {"usecase", "functie", "status", "taak", "bronnen", "model", "modelversie",
                      "app_versie", "resultaat", "foutmelding"}
    assert len(r["taak"]) == ai_logboek.MAX_TAAK and r["taak"].endswith("…")
    assert len(r["resultaat"]) == ai_logboek.MAX_RESULTAAT
    assert r["bronnen"] == ["u1", "u2"]
    assert r["app_versie"] == __version__


def test_regel_onbekende_status():
    with pytest.raises(ValueError):
        ai_logboek.regel("A", "Chat", "misschien")


def test_schrijven_mislukt_breekt_niets_af(monkeypatch):
    def kapot(rij):
        raise RuntimeError("database weg")
    monkeypatch.setattr(ai_logboek, "_schrijf_rij", kapot)
    ai_logboek.schrijf("C", "Kompas-zoeken", "geweigerd", taak="groen")  # geen exceptie


def _keten(n):
    regels, vorige = [], None
    for i in range(1, n + 1):
        r = {"id": i, "tijdstip_utc": f"2026-10-10T12:00:0{i}.000000Z", "usecase": "A", "functie": "Chat",
             "status": "uitgevoerd", "taak": f"vraag {i}", "bronnen": [f"u{i}"], "model": "m",
             "modelversie": None, "app_versie": "0.4.0", "resultaat": "antwoord", "foutmelding": None,
             "vorige_hash": vorige}
        r["hash"] = ai_logboek.regelhash(r)
        vorige = r["hash"]
        regels.append(r)
    return regels


def test_keten_klopt():
    uit = ai_logboek.controleer_keten(_keten(4))
    assert uit == {"ok": True, "aantal": 4, "eerste_id": 1, "laatste_id": 4, "fouten": []}


def test_gewijzigde_inhoud_valt_op():
    regels = _keten(4)
    regels[1]["resultaat"] = "ander antwoord"
    uit = ai_logboek.controleer_keten(regels)
    assert not uit["ok"] and uit["fouten"] == [{"id": 2, "reden": "hash past niet bij de inhoud"}]


def test_herberekende_hash_valt_op_bij_de_volgende_regel():
    regels = _keten(4)
    regels[1]["resultaat"] = "ander antwoord"
    regels[1]["hash"] = ai_logboek.regelhash(regels[1])
    uit = ai_logboek.controleer_keten(regels)
    assert [f["id"] for f in uit["fouten"]] == [3]


def test_verwijderde_regel_in_het_midden_valt_op():
    regels = _keten(4)
    del regels[1]
    assert [f["id"] for f in ai_logboek.controleer_keten(regels)["fouten"]] == [3]


def test_opgeschoond_begin_is_geen_fout():
    """Na opschonen is de eerste overgebleven regel het anker."""
    uit = ai_logboek.controleer_keten(_keten(5)[2:])
    assert uit["ok"] and uit["eerste_id"] == 3


def test_hash_hangt_af_van_elk_veld():
    r = _keten(1)[0]
    for veld in ai_logboek.HASHVELDEN:
        ander = dict(r, **{veld: ["x"] if veld == "bronnen" else "anders"})
        assert ai_logboek.regelhash(ander) != r["hash"], veld


def test_csv_zonder_formules():
    regels = _keten(1)
    regels[0]["taak"] = "=HYPERLINK(\"http://x\")"
    csv = ai_logboek.als_csv(regels)
    kop, rij = csv.splitlines()[:2]
    assert kop.split(";")[:5] == ["id", "tijdstip_utc", "usecase", "functie", "status"]
    assert "'=HYPERLINK" in rij and ";u1;" in rij
