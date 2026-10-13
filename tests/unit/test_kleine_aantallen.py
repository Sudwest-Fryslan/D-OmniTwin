"""Kleine aantallen (#325): één instelbare drempel, overal toegepast.

Per plek (zonder database): de module zelf, de drempel van de instantie (organisatie.n_drempel),
percentiel/label, indicatorpaneel, chat-datavraag, benchmarkrapport, Kompas, Z-score-SQL (V044)
en de kaart. De werking tegen de database staat in tests/integration/test_kleine_aantallen_stack.py.
"""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnitwin.routers import organisatie as org_router
from omnitwin.services import chat_datavraag as dv
from omnitwin.services import kleine_aantallen as ka
from omnitwin.services import percentielklasse as pk
from omnitwin.services import zscore_referentie as zr

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "omnitwin"


class _Rij:
    def __init__(self, waarde):
        self.waarde = waarde

    def scalar(self):
        return self.waarde

    def fetchall(self):
        return []

    def __iter__(self):
        return iter([])


class _Savepoint:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class NepDB:
    """Onthoudt de SQL; SELECT kleine_aantallen_drempel() geeft `drempel` (None = functie ontbreekt)."""

    def __init__(self, drempel=7):
        self.drempel = drempel
        self.sql = []

    def begin_nested(self):
        return _Savepoint()

    def execute(self, stmt, params=None):
        tekst = str(stmt)
        self.sql.append((tekst, params))
        if "kleine_aantallen_drempel()" in tekst and tekst.strip().startswith("SELECT kleine"):
            if self.drempel is None:
                raise RuntimeError("function kleine_aantallen_drempel() does not exist")
            return _Rij(self.drempel)
        return _Rij(None)


# ── De module ────────────────────────────────────────────────────────────────


def test_standaard_en_onderdrukking():
    assert ka.N_DREMPEL_STANDAARD == 10 == pk.N_DREMPEL
    assert ka.is_onderdrukt(9) and not ka.is_onderdrukt(10)
    assert not ka.is_onderdrukt(None), "zonder bekende n telt een waarde mee"
    assert pk.is_onderdrukt(4, 5) and not pk.is_onderdrukt(5, 5)


def test_drempel_van_de_instantie():
    assert ka.drempel(NepDB(7)) == 7
    assert ka.drempel(None) == 10
    assert ka.drempel(NepDB(None)) == 10, "database van vóór V044: de standaard"


def test_minimum_gebieden_is_iets_anders():
    """De minimum-n van de Z-scorereferentie (gebieden) staat apart van de n-drempel (waarnemingen)."""
    assert zr.MIN_N_STANDAARD == ka.MIN_GEBIEDEN_REFERENTIE == 5
    assert "kleine_aantallen" in zr.methodiek_beschrijving()


def test_geen_losse_drempels_meer():
    """Geen eigen getal voor kleine aantallen buiten services/kleine_aantallen.py."""
    for pad in SRC.rglob("*.py"):
        if pad.name == "kleine_aantallen.py":
            continue
        tekst = pad.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(N_DREMPEL|MIN_N_STANDAARD)\s*=\s*\d", tekst, re.M), pad


# ── Percentiel en label: zonder drempel die van de instantie ────────────────


def test_percentiel_volgt_de_instelling():
    db = NepDB(7)
    pk.onderdrukte_waarden(db, ["BU1"], ["u"])
    assert db.sql[-1][1]["pk_drempel"] == 7
    db = NepDB(7)
    pk.onderdrukte_waarden(db, ["BU1"], ["u"], drempel=12)
    assert db.sql[-1][1]["pk_drempel"] == 12


# ── Indicatorpaneel ──────────────────────────────────────────────────────────


def test_indicatorpaneel_gebruikt_de_instelling():
    tekst = (SRC / "services" / "indicatorpaneel_service.py").read_text(encoding="utf-8")
    assert "drempel: int | None = None" in tekst and "ka.drempel(self.db)" in tekst


# ── Chat-datavraag ───────────────────────────────────────────────────────────


def test_chat_laat_kleine_aantallen_weg():
    db = NepDB()
    assert dv.laad_waarden(db, ["u"], ["BU1"]) == []
    sql = db.sql[-1][0]
    assert "NOT is_kleine_aantallen(r.n)" in sql
    # eerst de recentste waarde, dan pas onderdrukken (geen terugval op een ouder jaar)
    assert sql.index("DISTINCT ON") < sql.index("is_kleine_aantallen")


# ── Rapporten en Kompas ──────────────────────────────────────────────────────


@pytest.mark.parametrize("bestand,aantal", [("report_service.py", 2), ("kompas_service.py", 1)])
def test_rapport_en_kompas_onderdrukken(bestand, aantal):
    tekst = (SRC / "services" / bestand).read_text(encoding="utf-8")
    assert tekst.count("is_kleine_aantallen(") >= aantal


def test_zscore_sql_v044():
    sql = (ROOT / "db" / "migraties" / "V044__kleine_aantallen.sql").read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS n_drempel" in sql
    assert "COALESCE((SELECT o.n_drempel FROM organisatie o LIMIT 1), 10)" in sql
    # referentiegroep en doelgebied
    assert sql.count("NOT is_kleine_aantallen(") == 2
    for f in ("zscore_referentie_waarden", "zscore_referentie_stats", "zscore_gebieden"):
        assert f"CREATE OR REPLACE FUNCTION {f}(" in sql
    assert "public." not in sql, "geen schemanaam: volgt het search_path (#137)"


# ── Kaart ────────────────────────────────────────────────────────────────────


def test_kaart_onderdrukt_en_tooltip():
    tekst = (SRC / "services" / "gebiedsmonitor_service.py").read_text(encoding="utf-8")
    assert "ka.is_onderdrukt(" in tekst and '"aantal_onderdrukt"' in tekst and '"n_drempel"' in tekst
    js = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "props.onderdrukt" in js and "waarnemingen" in js


# ── Instelling ───────────────────────────────────────────────────────────────

BASIS = {"code": "swf", "naam": "Gemeente", "gemeente_codes": ["1900"]}


def test_instelling_n_drempel():
    assert org_router.OrganisatieInvoer(**BASIS).n_drempel is None
    assert org_router.OrganisatieInvoer(**BASIS, n_drempel=15).n_drempel == 15
    for fout in (0, -1, 1001):
        with pytest.raises(ValidationError):
            org_router.OrganisatieInvoer(**BASIS, n_drempel=fout)
