"""
Unit test: migratierunner (src/omnitwin/migraties.py, #54).

Zonder database: psql wordt vervangen door een nep-uitvoerder die de tabel
schema_migraties in het geheugen bijhoudt.
"""
import re
from pathlib import Path

import pytest

from omnitwin import migraties as mig

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parent.parent


class NepPsql:
    """Speelt psql na: onthoudt registraties en welke bestanden zijn uitgevoerd."""

    def __init__(self, toegepast=None, faal_op=None):
        self.toegepast = dict(toegepast or {})
        self.uitgevoerd = []
        self.faal_op = faal_op

    def __call__(self, args):
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
        return ""  # CREATE TABLE IF NOT EXISTS


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
    open_ = mig.migreer(map_, uitvoeren=psql, alleen_status=True, log=lambda _: None)
    assert [m.versie for m in open_] == [2, 10]
    assert psql.uitgevoerd == []


def test_migraties_in_de_repository():
    """db/migraties: geldige namen, oplopend, en includes die bestaan."""
    gevonden = mig.zoek_migraties()
    assert [m.versie for m in gevonden] == [18, 19, 20, 21, 22]
    for m in gevonden:
        for inc in mig.INCLUDE.findall(m.pad.read_text(encoding="utf-8")):
            assert (m.pad.parent / inc).is_file(), f"{m.pad.name}: include {inc} bestaat niet"
    assert (ROOT / "db" / "migraties" / "R__api_rollen.sql").is_file()
