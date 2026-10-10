"""
Unit tests voor datavragen in de chat (#149): herkennen van datavragen, gebieden en
indicatoren, richting, feiten en de grounding-terugval. Geen database, geen taalmodel.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omnitwin.services import chat_datavraag as dv  # noqa: E402

pytestmark = pytest.mark.unit

BUURT = "afba67cb-6b38-4723-9c95-102a22d5b38a"
WIJK = "wijk-type"

GEBIEDEN = [
    {"id": "BU19000001", "naam": "Bolsward-Noord", "gemeente_code": "1900", "gebiedstype_id": BUURT},
    {"id": "BU19000002", "naam": "Bolsward-Zuidoost", "gemeente_code": "1900", "gebiedstype_id": BUURT},
    {"id": "BU19000004", "naam": "Bolsward-Noordoost", "gemeente_code": "1900", "gebiedstype_id": BUURT},
    {"id": "BU19000200", "naam": "Workum", "gemeente_code": "1900", "gebiedstype_id": BUURT},
    {"id": "BU19000202", "naam": "Hindeloopen", "gemeente_code": "1900", "gebiedstype_id": BUURT},
    {"id": "BU00800001", "naam": "Bolswardervaart", "gemeente_code": "0080", "gebiedstype_id": BUURT},  # fictief
    {"id": "BU00800002", "naam": "Centrum", "gemeente_code": "0080", "gebiedstype_id": BUURT},
    {"id": "WK190000", "naam": "Bolsward", "gemeente_code": "1900", "gebiedstype_id": WIJK},
]
GEMEENTEN = {"1900": "Súdwest-Fryslân", "0080": "Leeuwarden"}
BOLSWARD = ["BU19000001", "BU19000002", "BU19000004"]


def ind(naam, uuid=None, **kw):
    return {"uuid": uuid or f"u-{naam}", "naam": naam, **kw}


INDICATOREN = [ind(n) for n in [
    "Afstand tot koele plek", "Oppervlak groen per inwoner", "65+ jaar", "65+ jaar (%)", "45-65 jaar",
    "Eenzaamheid", "Vrijwilliger", "Mantelzorger", "Gemiddeld energielabel", "Aantal energielabels",
    "Aantal energielabels (definitief)", "Definitief energielabel", "Energielabel coverage",
    "Huishoudens met laag inkomen", "Moeite met rondkomen", "Inkomen per inwoner",
    "Netto arbeidsparticipatie", "Ervaren gezondheid", "Diversiteit Functies (Simpson Index)",
    "Afstand tot huisarts", "Eenpersoonshuishoudens", "Eenpersoonshuishoudens (%)",
]]

USECASE_VRAGEN = {
    "hittestress": "Ik werk aan hittestress in Bolsward. Welke buurt ligt het verst van een koele plek, "
                   "en waar wonen relatief de meeste 65-plussers?",
    "sociale-cohesie": "Ik ben wijkcoördinator in Bolsward-Zuidoost. Hoe staat het met eenzaamheid en "
                       "vrijwilligerswerk in mijn wijk?",
    "energiearmoede": "Waar in Bolsward is het risico op energiearmoede het grootst? Ik wil weten waar slechte "
                      "energielabels samengaan met lage inkomens.",
    "brede-welvaart": "Hoe staat het met de brede welvaart in Bolsward-Zuidoost vergeleken met de rest van Bolsward?",
}


def namen(treffers):
    return [t.naam for t in treffers]


def gebieden(vraag, **kw):
    return dv.herken_gebieden(vraag, GEBIEDEN, GEMEENTEN, voorkeur_type=kw.pop("voorkeur_type", BUURT), **kw)


def indicatoren(vraag, **kw):
    onderwerp = dv.resterende_tekst(vraag, [g["naam"] for g in GEBIEDEN] + ["Bolsward"])
    return namen(dv.herken_indicatoren(onderwerp, INDICATOREN, **kw))


# ── Datavraag herkennen ──────────────────────────────────────────────────────

@pytest.mark.parametrize("vraag", list(USECASE_VRAGEN.values()) + [
    "welke buurt ligt het verst van een koele plek",
    "hoe staat het met eenzaamheid in Bolsward-Zuidoost",
    "vergelijk Workum met Hindeloopen op eenzaamheid",
    "top 3 buurten met de hoogste eenzaamheid",
    "Hoeveel 65-plussers wonen er in Workum?",
    "Hoe groen is Bolsward-Zuidoost?",
    "Hoe staat Workum ervoor op eenzaamheid?",
    "Hoe veilig is Hindeloopen?",
    "Wat is de eenzaamheid in Workum?",
])
def test_datavraag_herkend(vraag):
    assert dv.is_datavraag(vraag)


@pytest.mark.parametrize("vraag", [
    "Ik ben beleidsadviseur",
    "Welke indicatoren zeggen iets over eenzaamheid bij ouderen in de buurt?",
    "Maak een rapport van deze buurt",
    "Toon eenzaamheid op de kaart",
    "Open het Kompas",
    "Selecteer Bolsward-Zuidoost",
    "Wat kun je allemaal?",
])
def test_geen_datavraag(vraag):
    assert not dv.is_datavraag(vraag)


def test_gevraagd_aantal_en_volgorde():
    assert dv.gevraagd_aantal("top 3 buurten met de meeste eenzaamheid") == 3
    assert dv.gevraagd_aantal("de vijf wijken met de laagste inkomens") == 5
    assert dv.gevraagd_aantal("welke buurt ligt het verst") is None
    assert dv.gevraagde_volgorde("welke buurt ligt het dichtst bij een koele plek") == "laag"
    assert dv.gevraagde_volgorde("welke buurt ligt het verst van een koele plek") == "hoog"


# ── Gebieden herkennen ───────────────────────────────────────────────────────

def test_woonplaats_wordt_buurten():
    r = gebieden(USECASE_VRAGEN["hittestress"])
    assert sorted(r.gevraagd) == BOLSWARD
    assert "BU00800001" not in r.gevraagd  # Bolswardervaart is een andere plaats
    assert r.bron == "vraag"


def test_buurtnaam_plus_woonplaats():
    r = gebieden(USECASE_VRAGEN["brede-welvaart"])
    assert r.gevraagd[0] == "BU19000002"
    assert sorted(r.gevraagd) == BOLSWARD


def test_een_buurt_krijgt_buren_als_referentie():
    r = gebieden(USECASE_VRAGEN["sociale-cohesie"])
    assert r.gevraagd == ["BU19000002"]
    assert sorted(r.referentie) == ["BU19000001", "BU19000004"]


def test_buurt_zonder_woonplaatsdeel_krijgt_gemeente_als_referentie():
    r = gebieden("Hoe staat het met eenzaamheid in Workum?")
    assert r.gevraagd == ["BU19000200"]
    assert set(r.referentie) == {"BU19000001", "BU19000002", "BU19000004", "BU19000202"}


def test_twee_buurten_vergelijken():
    r = gebieden("vergelijk Workum met Hindeloopen")
    assert r.gevraagd == ["BU19000200", "BU19000202"]
    assert r.referentie == []


def test_gemeente_wordt_buurten_van_die_gemeente():
    r = gebieden("top 3 buurten in Súdwest-Fryslân met de meeste eenzaamheid")
    assert set(r.gevraagd) == {"BU19000001", "BU19000002", "BU19000004", "BU19000200", "BU19000202"}


def test_gewoon_woord_is_geen_gebied():
    r = gebieden("hoe staat het met eenzaamheid in het centrum")
    assert r.gevraagd == []


def test_kaartcontext_als_niets_in_de_vraag():
    r = gebieden("hoe staat het met eenzaamheid hier", huidig_gebied_id="BU19000004")
    assert r.gevraagd == ["BU19000004"] and r.bron == "kaart"
    assert sorted(r.referentie) == ["BU19000001", "BU19000002"]


def test_voorkeur_buurten_boven_wijk():
    """'Bolsward' is ook een wijknaam; met voorkeur buurten worden het de drie buurten."""
    assert sorted(gebieden("hoe staat het met eenzaamheid in Bolsward").gevraagd) == BOLSWARD
    assert gebieden("hoe staat het met eenzaamheid in Bolsward", voorkeur_type=WIJK).gevraagd == ["WK190000"]


# ── Indicatoren herkennen ────────────────────────────────────────────────────

def test_indicatoren_hittestress():
    gevonden = indicatoren(USECASE_VRAGEN["hittestress"])
    assert gevonden[0] == "Afstand tot koele plek"
    assert "65+ jaar (%)" in gevonden
    assert "65+ jaar" not in gevonden  # het percentage gaat voor het aantal
    assert "45-65 jaar" not in gevonden


def test_indicatoren_groen():
    assert indicatoren("Hoe groen is Bolsward-Zuidoost?") == ["Oppervlak groen per inwoner"]


def test_indicatoren_sociale_cohesie():
    assert indicatoren(USECASE_VRAGEN["sociale-cohesie"]) == ["Eenzaamheid", "Vrijwilliger"]


def test_indicatoren_energiearmoede():
    gevonden = indicatoren(USECASE_VRAGEN["energiearmoede"])
    assert set(gevonden) == {"Gemiddeld energielabel", "Huishoudens met laag inkomen", "Moeite met rondkomen"}


def test_indicatoren_brede_welvaart():
    gevonden = indicatoren(USECASE_VRAGEN["brede-welvaart"])
    assert set(gevonden) == {"Inkomen per inwoner", "Netto arbeidsparticipatie", "Ervaren gezondheid",
                             "Diversiteit Functies (Simpson Index)"}


def test_geen_indicator_bij_onbekend_onderwerp():
    assert indicatoren("Hoeveel windmolens staan er in Bolsward?") == []


def test_ai_treffer_telt_alleen_boven_drempel():
    # 'medische post' staat niet in de synoniemen: alleen AI-zoeken kan hem vinden
    ai = [{"uuid": "u-Afstand tot huisarts", "naam": "Afstand tot huisarts", "score": 0.55}]
    assert indicatoren("Hoe ver is de medische post in Workum?", ai_treffers=ai) == []
    ai[0]["score"] = 0.82
    assert indicatoren("Hoe ver is de medische post in Workum?", ai_treffers=ai) == ["Afstand tot huisarts"]


def test_indicatoren_via_synoniem():
    """#233: 'bejaard' staat in db/stuurdata/synoniemen.json bij bejaarden → 65+ jaar (%)."""
    assert indicatoren("hoeveel % is bejaard bij mij in de buurt?") == ["65+ jaar (%)"]  # 80+ niet in de testlijst
    assert indicatoren("Hoe ver is de dokter in Workum?") == ["Afstand tot huisarts"]


@pytest.mark.parametrize("vraag,verwacht", [
    ("hoeveel % is bejaard bij mij in de buurt?", True),
    ("hoe gezond zijn de mensen in mijn wijk", True),
    ("hoe staat het met eenzaamheid hier", True),
    ("hoeveel ouderen wonen er in Workum", False),
    ("Welke indicatoren zeggen iets over eenzaamheid bij ouderen in de buurt?", False),
])
def test_vraagt_eigen_buurt(vraag, verwacht):
    assert dv.vraagt_eigen_buurt(vraag) is verwacht


# ── Richting en feiten ───────────────────────────────────────────────────────

@pytest.mark.parametrize("score_type,logica,verwacht", [
    ("+/+", "pos_is_pos", "hoger_is_beter"),
    ("+/-", "-/+", "lager_is_beter"),
    ("-/+", None, "lager_is_beter"),
    ("-/-", None, "lager_is_beter"),  # zelfde regel als report_service
    ("+/+", "neutraal", "neutraal"),
    ("+/+", "N/A", "neutraal"),
    (None, None, "hoger_is_beter"),
])
def test_richting(score_type, logica, verwacht):
    assert dv.richting(score_type, logica) == verwacht


@pytest.mark.parametrize("w,verwacht", [(48.3, "48,3"), (246.0, "246"), (26.27, "26,3"), (0.734, "0,73"), (0, "0")])
def test_formatteer_getal(w, verwacht):
    assert dv.formatteer_getal(w) == verwacht


NAMEN = {"BU19000001": "Bolsward-Noord", "BU19000002": "Bolsward-Zuidoost", "BU19000004": "Bolsward-Noordoost"}
KOEL = ind("Afstand tot koele plek", eenheid="m", bron="bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c_d_cbs_buurten.json",
           score_type="+/-", interpretatie_logica="-/+")
WAARDEN = [
    {"gebied_id": "BU19000001", "indicator_uuid": KOEL["uuid"], "waarde": 246.0, "jaar": 2021, "bron": "x"},
    {"gebied_id": "BU19000002", "indicator_uuid": KOEL["uuid"], "waarde": 226.0, "jaar": 2021, "bron": "DEMO: gemiddelde"},
    {"gebied_id": "BU19000004", "indicator_uuid": KOEL["uuid"], "waarde": 206.0, "jaar": 2021, "bron": "x"},
]


def test_feiten_rang_en_richting():
    [f] = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, BOLSWARD)
    assert f["richting"] == "lager_is_beter"
    assert [w["gebied"] for w in f["waarden"]] == ["Bolsward-Noord", "Bolsward-Zuidoost", "Bolsward-Noordoost"]
    noord, zuidoost, noordoost = f["waarden"]
    assert noord["labels"] == ["hoogste waarde", "ongunstigst"]
    assert noordoost["labels"] == ["laagste waarde", "gunstigst"]
    assert zuidoost["demo"] and zuidoost["rang_hoog"] == 2
    assert f["bron"] == "onbekende bron (import)"


def test_gelijke_waarden_delen_de_rang():
    gelijk = [dict(w) for w in WAARDEN]
    gelijk[1]["waarde"] = 246.0
    [f] = dv.bouw_feiten([KOEL], gelijk, NAMEN, BOLSWARD)
    assert [w["rang_hoog"] for w in f["waarden"]] == [1, 1, 3]
    assert all("ongunstigst" in w["labels"] for w in f["waarden"][:2])


def test_feiten_top_n_en_volgorde_laag():
    [f] = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, BOLSWARD, volgorde="laag", aantal=1)
    assert [w["gebied"] for w in f["waarden"]] == ["Bolsward-Noordoost"]
    assert f["aantal_gebieden"] == 3


def test_neutraal_geen_gunstig_label():
    neutraal = {**KOEL, "interpretatie_logica": "neutraal", "score_type": "+/+"}
    [f] = dv.bouw_feiten([neutraal], WAARDEN, NAMEN, BOLSWARD)
    assert all("gunstigst" not in w["labels"] and "ongunstigst" not in w["labels"] for w in f["waarden"])
    tekst = dv.samenvatting(f)
    assert "gunstig" not in tekst and "beter" not in tekst


def test_samenvatting_hoog_laag_midden_en_richting():
    [f] = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, ["BU19000002"])
    tekst = dv.samenvatting(f)
    assert "Hoogste waarde: Bolsward-Noord (246 m)" in tekst
    assert "laagste: Bolsward-Noordoost (206 m)" in tekst
    assert "Daartussen: Bolsward-Zuidoost (226 m)" in tekst
    assert "Bolsward-Noordoost scoort het gunstigst, Bolsward-Noord het ongunstigst" in tekst


def test_vaste_tekst_met_eenheid_bron_en_demo():
    feiten = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, BOLSWARD)
    tekst = dv.vaste_tekst(feiten)
    assert "246 m" in tekst and "2021" in tekst and "onbekende bron (import)" in tekst
    assert "Bolsward-Zuidoost zijn demodata" in tekst


@pytest.mark.parametrize("e,verwacht", [("%", "48,3%"), ("m", "48,3 m"), ("x 1 000 euro", "48,3 duizend euro"),
                                        ("aantal", "48,3"), ("", "48,3")])
def test_waarde_met_eenheid(e, verwacht):
    assert dv._waarde_tekst({"waarde": 48.3}, e) == verwacht


@pytest.mark.parametrize("bron,verwacht", [
    ("bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c_d_cbs_buurten.json", "onbekende bron (import)"),
    ("upload/groen_per_inwoner.csv", "onbekende bron (import)"),
    ("Gezondheidsmonitor RIVM 2024", "Gezondheidsmonitor RIVM 2024"),
    ("", "bron onbekend"),
])
def test_nette_bron(bron, verwacht):
    assert dv.nette_bron(bron) == verwacht


def test_prompt_bevat_cijfers_als_json():
    import json
    feiten = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, BOLSWARD)
    prompt = dv.gebruikersprompt("Welke buurt ligt het verst van een koele plek?", feiten, ["Bolsward"])
    blok = json.loads(prompt[prompt.index("["):prompt.rindex("]") + 1])
    assert [w["waarde"] for w in blok[0]["waarden"]] == ["246 m", "226 m", "206 m"]
    assert blok[0]["eenheid"] == "m" and "gunstigst" in blok[0]["samenvatting"]
    assert blok[0]["richting"].startswith("lager is beter")
    assert blok[0]["waarden"][1]["demowaarde"] is True
    assert "maximaal 4 zinnen" in prompt


def test_vaste_tekst_is_gegrond():
    feiten = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, BOLSWARD)
    assert dv.controleer_getallen(dv.vaste_tekst(feiten), feiten) == []


def test_controleer_getallen_vindt_verzonnen_getal():
    feiten = dv.bouw_feiten([KOEL], WAARDEN, NAMEN, BOLSWARD)
    assert dv.controleer_getallen("Bolsward-Noord ligt op 246 meter, Bolsward-Zuidoost op 231.", feiten) == ["231"]


# ── Route met nep-database en nep-model ──────────────────────────────────────

class NepDB:
    """Minimale stand-in voor de SQLAlchemy-sessie; de laad-functies worden vervangen."""

    def rollback(self):
        pass


@pytest.fixture
def nep_route(monkeypatch):
    monkeypatch.setattr(dv, "laad_gebieden", lambda db: [{**g, "gebiedstype": "CBS Buurten"} for g in GEBIEDEN
                                                       if g["gebiedstype_id"] == BUURT])
    monkeypatch.setattr(dv, "laad_indicatoren", lambda db: [KOEL])
    monkeypatch.setattr(dv, "laad_waarden", lambda db, u, ids: [w for w in WAARDEN if w["gebied_id"] in ids])
    import omnitwin.services.gemeente_validatie as gv
    monkeypatch.setattr(gv, "laad_gemeenten", lambda db, alleen_met_gebieden=False: GEMEENTEN)


def route(vraag, antwoord):
    return dv.beantwoord_datavraag(vraag, {}, NepDB(), lambda t: [], lambda s, u, *_: {"text": antwoord})


def test_route_gebruikt_gegrond_antwoord(nep_route):
    r = route("Welke buurt in Bolsward ligt het verst van een koele plek?",
              "Bolsward-Noord ligt het verst van een koele plek: 246 (bron onbekend, 2021).")
    assert r["llm_gebruikt"] and r["narrative"].startswith("Bolsward-Noord")
    assert sorted(r["gebied_ids"]) == BOLSWARD


def test_route_valt_terug_bij_verzonnen_getal(nep_route):
    r = route("Welke buurt in Bolsward ligt het verst van een koele plek?", "Bolsward-Noord: 312 meter.")
    assert not r["llm_gebruikt"] and r["ongegrond"] == ["312"]
    assert "246" in r["narrative"] and "312" not in r["narrative"]


def test_route_valt_terug_bij_modelfout(nep_route):
    r = route("Welke buurt in Bolsward ligt het verst van een koele plek?", "Error contacting Ollama op x")
    assert not r["llm_gebruikt"] and "246" in r["narrative"]


def test_route_zonder_indicator_zegt_eerlijk_geen_data(nep_route):
    r = route("Hoeveel windmolens staan er in Bolsward?", "mag niet gebruikt worden")
    assert r["feiten"] == [] and "geen cijfers" in r["narrative"]


def test_route_geen_datavraag(nep_route):
    assert route("Ik ben beleidsadviseur", "x") is None


def test_route_zonder_llm_geeft_vaste_tekst(nep_route):
    r = dv.beantwoord_datavraag("Welke buurt in Bolsward ligt het verst van een koele plek?", {"geen_llm": True},
                                NepDB(), lambda t: [], lambda s, u, *_: pytest.fail("model mag niet gevraagd worden"))
    assert not r["llm_gebruikt"] and r["model"] is None
    assert "Bolsward-Noord (246 m)" in r["narrative"] and "Bolsward-Noordoost (206 m)" in r["narrative"]


def test_route_gebied_plus_indicator_zonder_patroon_is_datavraag(nep_route):
    """'Koele plek Bolsward-Zuidoost' heeft geen vraagpatroon, wel gebied + indicator."""
    r = route("Koele plek Bolsward-Zuidoost", "Bolsward-Zuidoost: 226 m.")
    assert r is not None and r["llm_gebruikt"]
    assert r["gebied_ids"][0] == "BU19000002" and len(r["gebied_ids"]) == 3


def test_route_navigatie_blijft_navigatie(nep_route):
    assert route("Toon de koele plek in Bolsward-Zuidoost op de kaart", "x") is None


OUDEREN = ind("65+ jaar (%)", eenheid="%", bron="CBS Kerncijfers wijken en buurten 2026 (86358NED)", score_type="+/+",
               interpretatie_logica="neutraal")
OUDEREN_WAARDEN = [
    {"gebied_id": "BU19000001", "indicator_uuid": OUDEREN["uuid"], "waarde": 24.1, "jaar": 2026, "bron": "CBS"},
    {"gebied_id": "BU19000002", "indicator_uuid": OUDEREN["uuid"], "waarde": 29.5, "jaar": 2026, "bron": "CBS"},
    {"gebied_id": "BU19000004", "indicator_uuid": OUDEREN["uuid"], "waarde": 18.0, "jaar": 2026, "bron": "CBS"},
]


@pytest.fixture
def nep_ouderen(nep_route, monkeypatch):
    monkeypatch.setattr(dv, "laad_indicatoren", lambda db: [KOEL, OUDEREN])
    monkeypatch.setattr(dv, "laad_waarden", lambda db, u, ids: [w for w in WAARDEN + OUDEREN_WAARDEN
                                                               if w["gebied_id"] in ids and w["indicator_uuid"] in u])


def test_vraag_van_eduard_met_geselecteerde_buurt(nep_ouderen):
    """#233: 'hoeveel % is bejaard bij mij in de buurt?' met Bolsward-Zuidoost geselecteerd:
    een getal voor die buurt, met bron en jaar, en de buren ter vergelijking."""
    r = dv.beantwoord_datavraag("hoeveel % is bejaard bij mij in de buurt?",
                                {"huidig_gebied_id": "BU19000002", "geen_llm": True}, NepDB(), lambda t: [],
                                lambda s, u, *_: pytest.fail("geen model"))
    assert [t.naam for t in r["indicatoren"]] == ["65+ jaar (%)"]
    assert r["gebieden_bron"] == "kaart" and r["gebied_ids"][0] == "BU19000002"
    assert r["narrative"].startswith("65+ jaar (%) (CBS Kerncijfers wijken en buurten 2026 (86358NED), 2026): "
                                     "Bolsward-Zuidoost: 29,5% (2026). Ter vergelijking:")
    assert dv.controleer_getallen(r["narrative"], r["feiten"]) == []


def test_vraag_van_eduard_zonder_selectie_vraagt_welke_buurt(nep_ouderen):
    """Zonder geselecteerde buurt: niet alle buurten, maar vragen welke buurt; wel de indicator."""
    r = route("hoeveel % is bejaard bij mij in de buurt?", "mag niet gebruikt worden")
    assert r["feiten"] == [] and r["gebied_ids"] == []
    assert "Welke buurt is jouw buurt?" in r["narrative"] and "65+ jaar (%)" in r["narrative"]
    assert [t.naam for t in r["indicatoren"]] == ["65+ jaar (%)"]


def test_eigen_buurt_zonder_vraagpatroon_is_datavraag(nep_ouderen):
    r = route("ouderen bij mij in de buurt", "x")
    assert r is not None and "Welke buurt" in r["narrative"]


def test_route_geeft_gebiedstype_en_gemeente_voor_de_kaart(nep_route):
    r = route("Welke buurt in Bolsward ligt het verst van een koele plek?", "Bolsward-Noord: 246 m.")
    assert r["gebiedstype_id"] == BUURT and r["gemeente_code"] == "1900"

# ── 'Mijn buurt' (#233): multi-selectie en de aanname vooraf ─────────────────

def test_multiselectie_telt_mee():
    r = gebieden("hoeveel % is bejaard bij mij in de buurt?", huidig_gebied_id="BU19000001",
                 geselecteerd=["BU19000001", "BU19000002", "ONBEKEND"])
    assert r.gevraagd == ["BU19000001", "BU19000002"] and r.bron == "kaart"
    assert dv.aanname_tekst(r).startswith(
        "Ik ga uit van Bolsward-Noord en Bolsward-Zuidoost (geselecteerd op de kaart).")


def test_gebied_in_de_vraag_gaat_voor_de_selectie_en_geeft_geen_aanname():
    r = gebieden("hoeveel ouderen in Workum", geselecteerd=["BU19000001"])
    assert r.gevraagd == ["BU19000200"] and dv.aanname_tekst(r) is None


def test_aanname_bij_een_buurt_van_de_kaart():
    r = gebieden("hoe staat het met eenzaamheid hier", huidig_gebied_id="BU19000004")
    assert dv.aanname_tekst(r) == ("Ik ga uit van Bolsward-Noordoost (geselecteerd op de kaart). Een andere buurt? "
                                   "Selecteer die op de kaart of noem de naam in je vraag.")


@pytest.mark.parametrize("vraag", ["hoeveel ouderen wonen er bij ons in de wijk?", "zijn er veel bejaarden in deze buurt?",
                                   "inkomen in onze straat", "waar wij wonen"])
def test_eigen_buurt_varianten(vraag):
    assert dv.vraagt_eigen_buurt(vraag)

