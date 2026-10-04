"""
Beheerroute in-process (omnitwin.laden.beheer): Kompasprofielen en externe kaartlagen uit een
Data Package, voor use cases met route beheer (swf-initialisatie, #222 A1). Zonder database:
een nep-cursor met alleen de tabellen die de route raakt. Beleid: aanvullen, nooit overschrijven.
"""

import json
import re
import zipfile

import pytest

from omnitwin.laden import beheer

pytestmark = pytest.mark.unit


class NepCursor:
    """Genoeg SQL voor beheer.kompasprofielen en beheer.externe_kaartlagen (psycopg2-stijl, tuples)."""

    def __init__(self, indicatoren=(), profielen=(), lagen=(), toegang_kolom=False):
        self.toegang_kolom, self.classificatie = toegang_kolom, {}
        self.indicatoren = set(indicatoren)
        self.tabellen = {"kompas_configuraties": {n: i for i, n in enumerate(profielen, start=1)},
                         "kompas_titels": {}, "kompas_themas": {}, "kompas_onderdelen": {}}
        self.mapping, self.lagen, self._rij, self.rowcount = set(), {la: {} for la in lagen}, None, 0

    def execute(self, sql, p=()):
        sql = " ".join(sql.split())
        self._rij, self.rowcount = None, 0
        if sql.startswith("SELECT id FROM public.kompas_configuraties WHERE naam"):
            i = self.tabellen["kompas_configuraties"].get(p[0])
            self._rij = (i,) if i else None
        elif sql.startswith("INSERT INTO public.kompas_configuraties"):
            t = self.tabellen["kompas_configuraties"]
            t[p[0]] = len(t) + 1
            self.classificatie[p[0]] = p[1]
            self._rij = (t[p[0]],)
        elif sql.startswith("SELECT 1 FROM public.indicatoren"):
            self._rij = (1,) if p[0] in self.indicatoren else None
        elif m := re.match(r"SELECT id FROM public\.(kompas_\w+) WHERE naam = %s AND \w+ = %s", sql):
            i = self.tabellen[m.group(1)].get((p[0], p[1]))
            self._rij = (i,) if i else None
        elif m := re.match(r"INSERT INTO public\.(kompas_(?:titels|themas|onderdelen))", sql):
            t = self.tabellen[m.group(1)]
            t[(p[0], p[1])] = 1000 * len(self.tabellen) + len(t) + 1
            self._rij = (t[(p[0], p[1])],)
        elif sql.startswith("INSERT INTO public.kompas_indicator_mapping"):
            sleutel = (p[0], p[1], p[2])
            self.rowcount = 0 if sleutel in self.mapping else 1
            self.mapping.add(sleutel)
        elif sql.startswith("SELECT 1 FROM information_schema.columns"):
            self._rij = (1,) if self.toegang_kolom else None
        elif sql.startswith("SELECT 1 FROM public.externe_kaartlagen"):
            self._rij = (1,) if p[0] in self.lagen else None
        elif sql.startswith("INSERT INTO public.externe_kaartlagen"):
            kolommen = re.search(r"\((.*?)\) VALUES", sql).group(1).split(", ")
            laag = dict(zip(kolommen, p))
            self.lagen[laag["naam"]] = laag
        else:
            raise AssertionError(f"onverwachte SQL: {sql}")

    def fetchone(self):
        return self._rij


def pakket(tmp_path, regels, naam="r"):
    pad = tmp_path / f"{naam}.zip"
    velden = list(regels[0])
    csv = ",".join(velden) + "\r\n" + "".join(",".join(str(r.get(v, "")) for v in velden) + "\r\n" for r in regels)
    with zipfile.ZipFile(pad, "w") as z:
        z.writestr("datapackage.json", json.dumps({"resources": [{"name": naam, "path": f"{naam}.csv"}]}))
        z.writestr(f"{naam}.csv", csv)
    return pad


KOMPAS = [
    {"profiel": "Volledig Kompas", "kwadrant": "Samenstelling", "thema": "Bevolking", "onderdeel": "Leeftijd",
     "indicator_uuid": "u1", "weging": "10", "is_actueel": "True"},
    {"profiel": "Volledig Kompas", "kwadrant": "Samenstelling", "thema": "Bevolking", "onderdeel": "",
     "indicator_uuid": "u2", "weging": "", "is_actueel": "False"},
    {"profiel": "Volledig Kompas", "kwadrant": "Samenstelling", "thema": "Bevolking", "onderdeel": "Leeftijd",
     "indicator_uuid": "onbekend", "weging": "1", "is_actueel": "True"},
]


def test_lees_resource_leeg_is_none(tmp_path):
    assert beheer.lees_resource(pakket(tmp_path, KOMPAS))[1]["onderdeel"] is None


def test_kompasprofiel_vult_aan_en_is_idempotent(tmp_path):
    cur = NepCursor(indicatoren={"u1", "u2"}, profielen=["Volledig Kompas"])
    regels = beheer.lees_resource(pakket(tmp_path, KOMPAS))
    uit = beheer.kompasprofielen(cur, [dict(r) for r in regels])
    assert uit["gekoppeld"] == 2 and uit["alAanwezig"] == 0 and uit["indicatorOnbekend"] == ["onbekend"]
    assert uit["nieuweProfielen"] == []
    assert ("(Algemeen)", max(cur.tabellen["kompas_themas"].values())) in cur.tabellen["kompas_onderdelen"]
    tweede = beheer.kompasprofielen(cur, [dict(r) for r in regels])
    assert tweede["gekoppeld"] == 0 and tweede["alAanwezig"] == 2


def test_kompasprofiel_maakt_een_onbekend_profiel_aan(tmp_path):
    cur = NepCursor(indicatoren={"u1"})
    uit = beheer.kompasprofielen(cur, [dict(KOMPAS[0], profiel="SWF Basis")])
    assert uit["nieuweProfielen"] == ["SWF Basis"] and uit["gekoppeld"] == 1


def test_kompasprofiel_zonder_bekende_indicator_wordt_niet_aangemaakt():
    """Zonder de SWF-definities bestaan de klimaatindicatoren niet: dan ook geen leeg profiel."""
    cur = NepCursor()
    uit = beheer.kompasprofielen(cur, [dict(KOMPAS[0], profiel="SWF Klimaat", classificatie="label")])
    assert uit["nieuweProfielen"] == [] and uit["indicatorOnbekend"] == ["u1"]
    assert "SWF Klimaat" not in cur.tabellen["kompas_configuraties"]


def test_kompasprofiel_classificatie_bij_een_nieuw_profiel():
    cur = NepCursor(indicatoren={"u1"})
    beheer.kompasprofielen(cur, [dict(KOMPAS[0], profiel="SWF Klimaat", classificatie="label")])
    assert cur.classificatie["SWF Klimaat"] == "label_ae"


LAAG = {"naam": "Natura 2000", "beschrijving": "", "laag_type": "selectie", "bron_type": "WFS",
        "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0", "typename": "natura2000:natura2000",
        "srsname": "EPSG:28992", "versie": "2.0.0", "filter_type": "provincie", "filter_waarde": "Fryslân",
        "koppel_veld": "", "kleur_lijn": "#059669", "kleur_fill": "#34ef99", "opacity": "0.3", "actief": "True",
        "volgorde": "2", "toegang": "openbaar"}


def test_externe_kaartlagen_toevoegen_bestaand_blijft_intern_niet_actief(tmp_path):
    pytest.importorskip("fastapi")
    cur = NepCursor(lagen=["BAG Woonplaatsen"])
    regels = [dict(LAAG), dict(LAAG, naam="BAG Woonplaatsen"),
              dict(LAAG, naam="GeoVisia Project Locaties", toegang="intern")]
    uit = beheer.externe_kaartlagen(cur, beheer.lees_resource(pakket(tmp_path, regels)))
    assert uit["toegevoegd"] == ["Natura 2000", "GeoVisia Project Locaties"]
    assert uit["alAanwezig"] == ["BAG Woonplaatsen"] and uit["internNietActief"] == ["GeoVisia Project Locaties"]
    assert cur.lagen["Natura 2000"]["actief"] is True and cur.lagen["Natura 2000"]["opacity"] == 0.3
    assert cur.lagen["GeoVisia Project Locaties"]["actief"] is False
    assert "toegang" not in cur.lagen["Natura 2000"]


def test_externe_kaartlagen_met_toegang_per_laag(tmp_path):
    """Met de kolom toegang (#254) blijft een interne laag actief en wordt hij intern."""
    pytest.importorskip("fastapi")
    cur = NepCursor(toegang_kolom=True)
    regels = [dict(LAAG, naam="GeoVisia Project Locaties", toegang="intern")]
    uit = beheer.externe_kaartlagen(cur, beheer.lees_resource(pakket(tmp_path, regels)))
    assert uit["intern"] == ["GeoVisia Project Locaties"] and uit["internNietActief"] == []
    assert cur.lagen["GeoVisia Project Locaties"]["toegang"] == "intern"
    assert cur.lagen["GeoVisia Project Locaties"]["actief"] is True


def test_voer_uit_onbekende_soort_is_overgeslagen(tmp_path):
    uit = beheer.voer_uit("/api/beheer/v1/iets-anders/x", pakket(tmp_path, KOMPAS))
    assert uit["http"] == 501 and uit["status"] == "overgeslagen"


def test_voer_uit_in_een_transactie(tmp_path):
    from contextlib import contextmanager
    cur = NepCursor(indicatoren={"u1", "u2"}, profielen=["Volledig Kompas"])

    @contextmanager
    def transactie():
        yield cur

    uit = beheer.voer_uit("/api/beheer/v1/kompasprofielen/swf-init-kompas", pakket(tmp_path, KOMPAS), transactie)
    assert uit["http"] == 200 and uit["status"] == "verwerkt" and uit["aantallen"]["gekoppeld"] == 2
