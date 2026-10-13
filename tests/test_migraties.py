"""
Unit test: migratierunner (src/omnitwin/migraties.py, #54).

Zonder database: psql wordt vervangen door een nep-uitvoerder die de tabel
schema_migraties in het geheugen bijhoudt.
"""

import contextlib
import re
from pathlib import Path

import pytest

from omnitwin import migraties as mig

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parent.parent


class NepPsql:
    """Speelt psql na: onthoudt registraties en welke bestanden zijn uitgevoerd."""

    def __init__(self, toegepast=None, faal_op=None, log=None):
        self.toegepast = dict(toegepast or {})
        self.tabel = toegepast is not None  # bestaat schema_migraties al?
        self.uitgevoerd = []
        self.faal_op = faal_op
        self.log = log if log is not None else []  # volgorde van alle aanroepen

    def __call__(self, args):
        self.log.append(args[-1] if "-f" not in args else args[args.index("-f") + 1])
        if "to_regclass" in args[-1]:
            return "t\n" if self.tabel else "f\n"
        if "CREATE TABLE" in args[-1]:
            self.tabel = True
            return ""
        if "-f" in args:
            pad = Path(args[args.index("-f") + 1])
            assert "--single-transaction" in args, "bestand en registratie horen in één transactie"
            if self.faal_op and pad.name == self.faal_op:
                raise mig.MigratieFout("syntaxfout")
            self.uitgevoerd.append(pad.name)
            insert = args[args.index("-c") + 1]
            versie, naam, chk = re.search(r"VALUES \((\d+), '(\w+)', '(\w+)'\)", insert).groups()
            self.toegepast[int(versie)] = chk
            return ""
        if "SELECT versie, checksum" in args[-1]:
            return "".join(f"{v}|{c}\n" for v, c in sorted(self.toegepast.items()))
        raise AssertionError(f"onverwachte psql-aanroep: {args}")


def schrijf(map_, naam, inhoud="SELECT 1;\n"):
    (map_ / naam).write_text(inhoud, encoding="utf-8")


@pytest.fixture
def map_(tmp_path):
    for naam in ["V002__twee.sql", "V010__tien.sql", "V001__een.sql", "R__altijd.sql"]:
        schrijf(tmp_path, naam)
    return tmp_path


def test_volgorde_numeriek_en_zonder_herhaalbare(map_):
    gevonden = mig.zoek_migraties(map_)
    assert [m.versie for m in gevonden] == [1, 2, 10]
    assert [m.naam for m in gevonden] == ["een", "twee", "tien"]


def test_verse_database_past_alles_in_volgorde_toe(map_):
    psql = NepPsql()
    toegepast = mig.migreer(map_, uitvoeren=psql, log=lambda _: None)
    assert psql.uitgevoerd == ["V001__een.sql", "V002__twee.sql", "V010__tien.sql"]
    assert [m.versie for m in toegepast] == [1, 2, 10]
    assert set(psql.toegepast) == {1, 2, 10}


def test_toegepaste_worden_overgeslagen(map_):
    psql = NepPsql()
    mig.migreer(map_, uitvoeren=psql, log=lambda _: None)
    psql.uitgevoerd.clear()
    schrijf(map_, "V011__nieuw.sql")
    toegepast = mig.migreer(map_, uitvoeren=psql, log=lambda _: None)
    assert psql.uitgevoerd == ["V011__nieuw.sql"]
    assert [m.versie for m in toegepast] == [11]
    # derde keer: niets te doen
    psql.uitgevoerd.clear()
    assert mig.migreer(map_, uitvoeren=psql, log=lambda _: None) == []
    assert psql.uitgevoerd == []


def test_gewijzigde_migratie_geeft_waarschuwing_en_draait_niet_opnieuw(map_):
    psql = NepPsql()
    mig.migreer(map_, uitvoeren=psql, log=lambda _: None)
    psql.uitgevoerd.clear()
    schrijf(map_, "V002__twee.sql", "SELECT 2;\n")
    regels = []
    mig.migreer(map_, uitvoeren=psql, log=regels.append)
    assert psql.uitgevoerd == []
    assert any("V002 twee is gewijzigd" in r for r in regels)


def test_checksum_negeert_crlf_en_telt_includes_mee(tmp_path):
    (tmp_path / "sub").mkdir()
    schrijf(tmp_path / "sub", "deel.sql", "SELECT 1;\n")
    (tmp_path / "V001__a.sql").write_bytes(b"-- kop\r\n\\ir sub/deel.sql\r\n")
    (tmp_path / "V002__b.sql").write_bytes(b"-- kop\n\\ir sub/deel.sql\n")
    a, b = mig.zoek_migraties(tmp_path)
    assert a.checksum == b.checksum
    schrijf(tmp_path / "sub", "deel.sql", "SELECT 2;\n")
    assert mig.checksum(a.pad) != a.checksum


def test_fout_stopt_en_registreert_niet(map_):
    psql = NepPsql(faal_op="V002__twee.sql")
    with pytest.raises(mig.MigratieFout):
        mig.migreer(map_, uitvoeren=psql, log=lambda _: None)
    assert psql.uitgevoerd == ["V001__een.sql"]
    assert set(psql.toegepast) == {1}


def test_dubbele_versie_en_ongeldige_naam(tmp_path):
    schrijf(tmp_path, "V001__een.sql")
    schrijf(tmp_path, "V1__ook_een.sql")
    with pytest.raises(mig.MigratieFout, match="twee keer"):
        mig.zoek_migraties(tmp_path)
    (tmp_path / "V1__ook_een.sql").unlink()
    schrijf(tmp_path, "V002-fout.sql")
    with pytest.raises(mig.MigratieFout, match="Ongeldige migratienaam"):
        mig.zoek_migraties(tmp_path)


def test_status_past_niets_toe(map_):
    psql = NepPsql(toegepast={1: mig.checksum(map_ / "V001__een.sql")})
    open_ = mig.migreer(
        map_,
        uitvoeren=psql,
        alleen_status=True,
        log=lambda _: None,
        slot=lambda: pytest.fail("--status neemt geen lock"),
    )
    assert [m.versie for m in open_] == [2, 10]
    assert psql.uitgevoerd == []
    assert not any("CREATE TABLE" in a for a in psql.log)


def test_status_zonder_tabel_is_alleen_lezen(map_):
    """--status op een database zonder schema_migraties: alles open, tabel niet aanmaken."""
    psql = NepPsql()
    open_ = mig.migreer(map_, uitvoeren=psql, alleen_status=True, log=lambda _: None)
    assert [m.versie for m in open_] == [1, 2, 10]
    assert not psql.tabel


def test_includes_zichtbaar_in_status_en_waarschuwing(tmp_path):
    """V021-geval: een migratie die een schemabestand inleest; dat bestand telt mee (#202)."""
    (tmp_path / "schema").mkdir()
    (tmp_path / "migraties").mkdir()
    schrijf(tmp_path / "schema", "08_deel.sql", "SELECT 1;\n")
    schrijf(tmp_path / "migraties", "V021__met_include.sql", "\\ir ../schema/08_deel.sql\n")
    map_ = tmp_path / "migraties"
    (m,) = mig.zoek_migraties(map_)
    assert m.includes == ("08_deel.sql",)  # buiten de repository: alleen de naam

    psql = NepPsql()
    mig.migreer(map_, uitvoeren=psql, log=lambda _: None)
    regels = []
    mig.migreer(map_, uitvoeren=psql, alleen_status=True, log=regels.append)
    assert any("V021 met_include  (+ 08_deel.sql)" in r for r in regels)

    schrijf(tmp_path / "schema", "08_deel.sql", "SELECT 2;\n")  # alleen het ingelezen bestand
    regels = []
    mig.migreer(map_, uitvoeren=psql, log=regels.append)
    assert any("V021 met_include is gewijzigd" in r and "telt ook mee: 08_deel.sql" in r for r in regels)


def test_v021_noemt_zscore_referentie():
    v021 = next(m for m in mig.zoek_migraties() if m.versie == 21)
    assert v021.includes == ("db/schema/08_zscore_referentie.sql",)


def test_ontbrekende_map_is_een_fout(tmp_path):
    with pytest.raises(mig.MigratieFout, match="niet gevonden"):
        mig.zoek_migraties(tmp_path / "bestaat_niet")


# ── advisory lock (#202) ─────────────────────────────────────────────────────


class NepSlot:
    """Contextmanager die in het gedeelde log bijhoudt wanneer de lock vastgehouden wordt."""

    def __init__(self, log, tijdens_wachten=None):
        self.log = log
        self.tijdens_wachten = tijdens_wachten

    def __call__(self):
        return self

    def __enter__(self):
        if self.tijdens_wachten:  # een andere run die klaar is terwijl wij wachten
            self.tijdens_wachten()
        self.log.append("slot vast")

    def __exit__(self, *exc):
        self.log.append("slot los")
        return False


def test_lock_omsluit_lezen_en_toepassen(map_):
    log = []
    psql = NepPsql(log=log)
    mig.migreer(map_, uitvoeren=psql, log=lambda _: None, slot=NepSlot(log))
    assert log[0] == "slot vast" and log[-1] == "slot los"
    assert "CREATE TABLE" in log[1]  # pas na de lock de tabel aanmaken en lezen
    assert sum("V0" in regel for regel in log) == 3


def test_lock_wordt_vrijgegeven_bij_fout(map_):
    log = []
    psql = NepPsql(faal_op="V002__twee.sql", log=log)
    with pytest.raises(mig.MigratieFout):
        mig.migreer(map_, uitvoeren=psql, log=lambda _: None, slot=NepSlot(log))
    assert log[-1] == "slot los"


def test_tweede_run_leest_pas_na_de_lock(map_):
    """Run B wacht op de lock terwijl run A alles toepast; B past daarna niets dubbel toe."""
    psql = NepPsql()
    run_a = lambda: mig.migreer(map_, uitvoeren=psql, log=lambda _: None)  # noqa: E731
    regels = []
    toegepast_b = mig.migreer(map_, uitvoeren=psql, log=regels.append, slot=NepSlot([], tijdens_wachten=run_a))
    assert toegepast_b == []
    assert psql.uitgevoerd == ["V001__een.sql", "V002__twee.sql", "V010__tien.sql"]
    assert any("niets te doen" in r for r in regels)


def test_standaard_slot_alleen_met_echte_psql(map_, monkeypatch):
    """Zonder slot-argument: psql_slot bij de echte psql, geen lock bij een nep-uitvoerder."""
    gebruikt = []

    @contextlib.contextmanager
    def nep_psql_slot(**_):
        gebruikt.append(True)
        yield

    monkeypatch.setattr(mig, "psql_slot", nep_psql_slot)
    mig.migreer(map_, uitvoeren=NepPsql(), log=lambda _: None)
    assert gebruikt == []
    monkeypatch.setattr(mig, "psql", NepPsql())
    mig.migreer(map_, uitvoeren=mig.psql, log=lambda _: None)
    assert gebruikt == [True]


class NepPsqlProces:
    """Speelt een interactieve psql-sessie na voor psql_slot."""

    def __init__(self, vrij=True, verbinding=True):
        self.vrij, self.verbinding = vrij, verbinding
        self.verzonden, self.antwoorden = [], []
        self.gestopt = False
        proces = self

        class Stdin:
            def write(self, tekst):
                proces.verzonden.append(tekst)
                if not proces.verbinding:
                    return
                if "pg_try_advisory_lock" in tekst:
                    proces.antwoorden.append("t\n" if proces.vrij else "f\n")
                elif "pg_advisory_lock" in tekst:
                    proces.antwoorden.append("ok\n")

            def flush(self):
                pass

            def close(self):
                proces.gestopt = True

        class Stdout:
            def readline(self):
                return proces.antwoorden.pop(0) if proces.antwoorden else ""

        class Stderr:
            def read(self):
                return "could not connect to server"

        self.stdin, self.stdout, self.stderr = Stdin(), Stdout(), Stderr()

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.gestopt = True


@pytest.mark.parametrize("vrij", [True, False])
def test_psql_slot_neemt_lock_en_sluit_sessie(monkeypatch, vrij):
    proces = NepPsqlProces(vrij=vrij)
    monkeypatch.setattr(mig.subprocess, "Popen", lambda *a, **k: proces)
    regels = []
    with mig.psql_slot(log=regels.append):
        assert not proces.gestopt
    assert f"pg_try_advisory_lock({mig.SLOT_SLEUTEL})" in proces.verzonden[0]
    if vrij:
        assert regels == [] and len(proces.verzonden) == 2
    else:
        assert any("wachten" in r for r in regels)
        assert f"pg_advisory_lock({mig.SLOT_SLEUTEL})" in proces.verzonden[1]
    assert proces.verzonden[-1] == "\\q\n" and proces.gestopt


def test_psql_slot_zonder_verbinding_is_een_fout(monkeypatch):
    proces = NepPsqlProces(verbinding=False)
    monkeypatch.setattr(mig.subprocess, "Popen", lambda *a, **k: proces)
    with pytest.raises(mig.MigratieFout, match="could not connect"):
        with mig.psql_slot(log=lambda _: None):
            pytest.fail("blok mag niet draaien zonder lock")
    assert proces.gestopt


def test_migraties_in_de_repository():
    """db/migraties: geldige namen, oplopend, en includes die bestaan."""
    gevonden = mig.zoek_migraties()
    versies = [m.versie for m in gevonden]
    assert versies[:13] == [18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31]  # V023 bestaat niet (#205)
    assert versies == sorted(set(versies)) and 35 in versies  # V032-V034: open PR's (#253, #254, #256)
    for m in gevonden:
        for inc in mig.INCLUDE.findall(m.pad.read_text(encoding="utf-8")):
            assert (m.pad.parent / inc).is_file(), f"{m.pad.name}: include {inc} bestaat niet"
    assert (ROOT / "db" / "migraties" / "R__api_rollen.sql").is_file()


def test_verbinding_uit_database_variabelen(monkeypatch):
    for k in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "DATABASE_NAME", "DATABASE_USER"]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DATABASE_HOST", "postgres")
    monkeypatch.setenv("DATABASE_PASSWORD", "geheim")
    env = mig._psql_omgeving()
    assert env["PGHOST"] == "postgres" and env["PGPASSWORD"] == "geheim"
    assert env["PGUSER"] == "omnitwin_user" and env["PGDATABASE"] == "omnitwin_db"
    monkeypatch.setenv("PGUSER", "ander")
    assert mig._psql_omgeving()["PGUSER"] == "ander"
