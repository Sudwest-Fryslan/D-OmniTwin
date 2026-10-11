"""
Unit tests voor zoeken in gewone taal (#233): begrippen en synoniemen, rangschikken, afkappen,
de embeddingtekst en de synoniemenlijst zelf. Geen database, geen model.
"""
import csv
import json
from pathlib import Path

import pytest

from omnitwin.services import zoektaal as z

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parent.parent
BEGRIPPEN = z.laad_begrippen()


def ind(naam):
    return {"uuid": f"u-{naam}", "naam": naam}


INDICATOREN = [ind(n) for n in [
    "65+ jaar (%)", "65+ jaar", "80 jaar of ouder (%)", "Oppervlak groen per inwoner", "Boomkroonbedekking",
    "Bouwjaar voor 1915", "Verwerken hemelwater exc. schade", "Ervaren gezondheid", "Bouwjaar 1945-1984",
    "Huishoudens met laag inkomen", "Moeite met rondkomen", "Inkomen per inwoner", "Gemiddelde WOZ-waarde",
    "Gemiddelde woonoppervlakte (BAG)", "Gemiddeld energielabel", "Aantal energielabels", "Inwoners",
]]


def namen(rangen):
    return [r.naam for r in rangen]


# ── Begrippen herkennen ──────────────────────────────────────────────────────

def test_bejaard_is_een_synoniem_van_ouderen():
    [t] = z.herken_begrippen("hoeveel % is bejaard bij mij in de buurt?", BEGRIPPEN)
    assert t.begrip.label == "bejaarden" and t.woorden == ["bejaard"]


def test_label_past_op_langere_woordvorm():
    """'bejaard' (5+ letters) past ook op 'bejaarden'; korte labels alleen op het hele woord."""
    assert [t.begrip.label for t in z.herken_begrippen("veel bejaarden", BEGRIPPEN)] == ["bejaarden"]
    assert [t.begrip.label for t in z.herken_begrippen("veel seniorencomplexen", BEGRIPPEN)] == ["ouderen"]
    assert z.herken_begrippen("armband", BEGRIPPEN) == []  # 'arm' is te kort voor een voorvoegsel


def test_langer_label_verbruikt_de_woorden():
    """'lage inkomens' is één begrip; 'inkomens' telt niet nog eens als 'inkomen'."""
    labels = [t.begrip.label for t in z.herken_begrippen("waar wonen lage inkomens", BEGRIPPEN)]
    assert labels == ["lage inkomens"]


def test_vraagwoord_niet_als_begin_van_een_langer_label():
    """'huizen' is geen 'huizenprijzen' (WOZ): alleen het label mag het begin van het vraagwoord zijn."""
    assert "woningwaarde" not in [t.begrip.label for t in z.herken_begrippen("hoe groot zijn de huizen", BEGRIPPEN)]


def test_begrippen_in_volgorde_van_de_vraag():
    labels = [t.begrip.label for t in z.herken_begrippen("eenzaamheid en vrijwilligerswerk", BEGRIPPEN)]
    assert labels == ["eenzaamheid", "vrijwilligers"]


# ── Rangschikken en afkappen ─────────────────────────────────────────────────

def test_vraag_van_eduard_geeft_ouderen_en_niet_groen():
    """De vraag uit #233: eerst 65+ jaar (%) en 80 jaar of ouder (%), geen groen, bouwjaren of hemelwater."""
    gelijkenis = {i["uuid"]: 0.5 for i in INDICATOREN}  # betekenis zegt niets: alleen het begrip telt
    rangen = z.rangschik("hoeveel % is bejaard bij mij in de buurt?", INDICATOREN, gelijkenis, BEGRIPPEN, 0.5, 0.6)
    assert namen(rangen)[:3] == ["65+ jaar (%)", "80 jaar of ouder (%)", "65+ jaar"]
    assert not {"Oppervlak groen per inwoner", "Bouwjaar voor 1915", "Verwerken hemelwater exc. schade"} & set(namen(rangen))
    assert rangen[0].redenen == ["begrip: bejaarden"]


def test_betekenis_zonder_trefwoord_is_hoogstens_matig():
    gelijkenis = {i["uuid"]: 0.0 for i in INDICATOREN}
    gelijkenis["u-80 jaar of ouder (%)"] = 1.0
    [r] = z.rangschik("hoogbejaard is een ander woord", INDICATOREN[2:3], gelijkenis, [], 0.0, 0.5)
    assert r.score == z.GEWICHT_BETEKENIS and r.relevantie == "matig" and r.redenen == ["betekenis"]


def test_afkap_binnen_afstand_van_de_beste():
    gelijkenis = {"u-Inwoners": 0.0, "u-Inkomen per inwoner": 0.0}
    rangen = z.rangschik("hoeveel inwoners", INDICATOREN, gelijkenis, [], 0.0, 1.0)
    # Inwoners (naam 1,0) wel; Inkomen per inwoner (naam 0,5) ligt te ver van de beste
    assert namen(rangen) == ["Inwoners"]


def test_niets_tonen_als_niets_past():
    gelijkenis = {i["uuid"]: 0.1 for i in INDICATOREN}
    assert z.rangschik("windmolens", INDICATOREN, gelijkenis, BEGRIPPEN, 0.5, 0.6) == []


def test_zonder_afkap_de_volledige_volgorde():
    gelijkenis = {i["uuid"]: 0.1 for i in INDICATOREN}
    assert len(z.rangschik("windmolens", INDICATOREN, gelijkenis, BEGRIPPEN, 0.5, 0.6, limit=3, afkappen=False)) == 3


def test_relatieve_grenzen_rond_de_mediaan():
    onder, boven = z.relatieve_grenzen({"a": 0.70, "b": 0.80, "c": 0.90}, 0.0, 0.07)
    assert (round(onder, 3), round(boven, 3)) == (0.80, 0.87)
    assert z.schaal_gelijkenis(0.835, onder, boven) == pytest.approx(0.5)
    assert z.schaal_gelijkenis(0.95, onder, boven) == 1.0 and z.schaal_gelijkenis(0.7, onder, boven) == 0.0


# ── Embeddingtekst ───────────────────────────────────────────────────────────

def test_indicator_tekst_met_kompaspad_eenheid_en_synoniemen():
    syn = z.synoniemen_van("65+ jaar (%)", BEGRIPPEN)
    assert "bejaard" in syn and "senioren" in syn
    tekst = z.indicator_tekst("65+ jaar (%)", "", ["Bevolking", "Huishoudens", None], "%", syn[:2])
    assert tekst == "65+ jaar (%). Thema: Bevolking / Huishoudens. Eenheid: %. Ook: ouderen, oudere"


# ── De synoniemenlijst zelf ──────────────────────────────────────────────────

def _alle_teksten(data, uit):
    if isinstance(data, dict):
        for v in data.values():
            _alle_teksten(v, uit)
    elif isinstance(data, list):
        for v in data:
            _alle_teksten(v, uit)
    elif isinstance(data, str):
        uit.add(z.normaliseer(data))
    return uit


def bekende_indicatornamen():
    """Indicatornamen uit stuurdata, sample, CBS-recept en use cases."""
    namen = set()
    for pad in [ROOT / "db/stuurdata/indicatoren_seed.json", ROOT / "init_data/cbs/datapackage.json",
                *sorted(ROOT.glob("usecases/*/usecase.json"))]:
        _alle_teksten(json.loads(pad.read_text(encoding="utf-8")), namen)
    with open(ROOT / "init_data/sample/2_brondata/sample_indicatoren.csv", encoding="utf-8") as f:
        namen |= {z.normaliseer(r["indicator_naam"]) for r in csv.DictReader(f)}
    return namen


def test_synoniemenlijst_verwijst_naar_bestaande_indicatoren():
    bekend = bekende_indicatornamen()
    onbekend = sorted({n for b in BEGRIPPEN for n in b.indicatoren if z.normaliseer(n) not in bekend})
    assert onbekend == [], f"indicatornamen in db/stuurdata/synoniemen.json die nergens voorkomen: {onbekend}"


def test_synoniemenlijst_is_geldig():
    data = json.loads(z.SYNONIEMEN.read_text(encoding="utf-8"))
    assert len(data["begrippen"]) >= 30
    for b in data["begrippen"]:
        assert set(b) <= {"prefLabel", "altLabel", "soort", "indicatoren"}, b
        assert b["soort"] in ("specifiek", "thema") and b["indicatoren"], b
    # een label hoort bij één begrip, anders is de uitkomst afhankelijk van de volgorde
    labels = [l for b in BEGRIPPEN for l in b.labels]
    dubbel = sorted({l for l in labels if labels.count(l) > 1})
    assert dubbel == []

# ── Zonder embeddings (AI-usecase C dicht, #233) ─────────────────────────────

def test_zonder_betekenis_telt_het_trefwoord_voor_de_hele_score():
    """Zonder gelijkenissen kan een trefwoord ook 'sterk' zijn (anders hoogstens 0,5)."""
    [r] = z.rangschik("hoeveel inwoners", [ind("Inwoners")], {}, [], 0.0, 1.0)
    assert r.score == 1.0 and r.relevantie == "sterk"


def test_woord_in_kompaspad_als_de_naam_niet_past():
    inds = [{"uuid": "u-hemelwater", "naam": "Verwerken hemelwater exc. schade",
             "tekst": "Kwaliteit fysieke leefomgeving Openbare ruimte Klimaat"},
            {"uuid": "u-groen", "naam": "Oppervlak groen per inwoner", "tekst": "Wonen Groen"}]
    rangen = z.rangschik("klimaatadaptatie", inds, {}, [], 0.0, 1.0)
    assert namen(rangen) == ["Verwerken hemelwater exc. schade"]
    assert rangen[0].relevantie == "matig" and rangen[0].redenen == ["thema: klimaatadaptatie"]


def test_naam_gaat_voor_kompaspad():
    inds = [{"uuid": "u-a", "naam": "Inwoners", "tekst": "Bevolking"},
            {"uuid": "u-b", "naam": "Leeftijd", "tekst": "Inwoners en bevolking"}]
    rangen = z.rangschik("inwoners", inds, {}, [], 0.0, 1.0)
    assert namen(rangen)[0] == "Inwoners"
    assert z.tekst_score(["inwoners"], "Inwoners en bevolking")[0] == z.TEKST_FACTOR
    assert z.tekst_score(["hoe"], "Inwoners") == (0.0, [])

