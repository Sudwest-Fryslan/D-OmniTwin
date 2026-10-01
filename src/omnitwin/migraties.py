"""
Migratierunner (#54): past de schemamigraties in db/migraties/ in volgorde toe.

    python -m omnitwin.migraties            # toepassen wat nog niet in schema_migraties staat
    python -m omnitwin.migraties --status   # alleen tonen, niets toepassen

Een migratie is een bestand ``V<versie>__<naam>.sql`` (Flyway-stijl, bijv.
``V018__trigram.sql``). De runner

1. maakt zo nodig de tabel ``schema_migraties`` (versie, naam, checksum, toegepast_op);
2. past elke migratie waarvan de versie nog niet in die tabel staat toe, op volgorde
   van versie, en registreert hem in dezelfde transactie (``psql --single-transaction``);
3. waarschuwt (geen fout) als een al toegepaste migratie sindsdien gewijzigd is.

Een bestaande database zonder ``schema_migraties`` krijgt de tabel en alle migraties
opnieuw: ze zijn idempotent geschreven. Een nieuwe migratie moet dat ook zijn.

De bestanden worden uitgevoerd met ``psql`` (ON_ERROR_STOP), zoals voorheen in
docker-entrypoint.sh: migraties mogen psql-opdrachten als ``\\ir`` bevatten. De
checksum (sha256) telt de bestanden mee die met ``\\ir``/``\\i`` worden ingelezen,
en negeert het verschil tussen CRLF en LF (checkout op Windows).

Verbinding: de gewone libpq-variabelen (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD);
ontbreken die, dan DATABASE_HOST/PORT/NAME/USER/PASSWORD zoals in .env.

Niet hier: ``R__*.sql`` (herhaalbaar, bijv. ``R__api_rollen.sql``). Die voert
docker-entrypoint.sh bij elke start uit.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]  # root van de repository (src/omnitwin/migraties.py)
MIGRATIE_MAP = ROOT / "db" / "migraties"

BESTANDSNAAM = re.compile(r"^V(\d+)__([A-Za-z0-9_]+)\.sql$")
INCLUDE = re.compile(r"^\s*\\i[r]?\s+(\S+)", re.MULTILINE)

TABEL_SQL = """
CREATE TABLE IF NOT EXISTS public.schema_migraties (
    versie       integer     PRIMARY KEY,
    naam         text        NOT NULL,
    checksum     text        NOT NULL,
    toegepast_op timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.schema_migraties IS
    'Toegepaste migraties uit db/migraties (python -m omnitwin.migraties, #54)';
"""


class MigratieFout(Exception):
    pass


@dataclass(frozen=True)
class Migratie:
    versie: int
    naam: str
    pad: Path
    checksum: str

    @property
    def label(self) -> str:
        return f"V{self.versie:03d} {self.naam}"


def _inhoud(pad: Path, gezien: frozenset = frozenset()) -> bytes:
    """Bestandsinhoud (LF) plus die van \\i/\\ir-includes, voor de checksum."""
    if pad in gezien:
        return b""
    tekst = pad.read_bytes().replace(b"\r\n", b"\n")
    delen = [tekst]
    for match in INCLUDE.finditer(tekst.decode("utf-8")):
        include = (pad.parent / match.group(1)).resolve()
        if include.is_file():
            delen.append(_inhoud(include, gezien | {pad}))
    return b"\0".join(delen)


def checksum(pad: Path) -> str:
    return hashlib.sha256(_inhoud(pad.resolve())).hexdigest()


def zoek_migraties(map_: Path = MIGRATIE_MAP) -> list[Migratie]:
    """Alle V<versie>__<naam>.sql in de map, gesorteerd op versie (numeriek)."""
    migraties: dict[int, Migratie] = {}
    for pad in sorted(map_.glob("V*.sql")):
        m = BESTANDSNAAM.match(pad.name)
        if not m:
            raise MigratieFout(f"Ongeldige migratienaam: {pad.name} (verwacht V<versie>__<naam>.sql)")
        versie = int(m.group(1))
        if versie in migraties:
            raise MigratieFout(f"Versie {versie} komt twee keer voor: {migraties[versie].pad.name} en {pad.name}")
        migraties[versie] = Migratie(versie, m.group(2), pad, checksum(pad))
    return [migraties[v] for v in sorted(migraties)]


def plan(migraties: Iterable[Migratie], toegepast: dict[int, str]) -> tuple[list[Migratie], list[str]]:
    """Wat nog moet, en waarschuwingen voor toegepaste migraties met een andere checksum."""
    te_doen, waarschuwingen = [], []
    for m in migraties:
        if m.versie not in toegepast:
            te_doen.append(m)
        elif toegepast[m.versie] != m.checksum:
            waarschuwingen.append(
                f"{m.label} is gewijzigd sinds hij is toegepast (checksum verschilt). "
                "Hij wordt niet opnieuw uitgevoerd; zet een wijziging in een nieuwe migratie."
            )
    return te_doen, waarschuwingen


# ── psql ────────────────────────────────────────────────────────────────────

Psql = Callable[[list[str]], str]


def _psql_omgeving() -> dict[str, str]:
    env = dict(os.environ)
    for pg, db in [("PGHOST", "DATABASE_HOST"), ("PGPORT", "DATABASE_PORT"), ("PGDATABASE", "DATABASE_NAME"),
                   ("PGUSER", "DATABASE_USER"), ("PGPASSWORD", "DATABASE_PASSWORD")]:
        if not env.get(pg) and env.get(db):
            env[pg] = env[db]
    # Geen NOTICE's van CREATE ... IF NOT EXISTS in de log
    env.setdefault("PGOPTIONS", "-c client_min_messages=warning")
    return env


def psql(args: list[str]) -> str:
    """Draai psql (ON_ERROR_STOP, zonder psqlrc) en geef stdout terug; fout bij exitcode != 0."""
    res = subprocess.run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", *args],
                         capture_output=True, text=True, env=_psql_omgeving())
    if res.returncode != 0:
        raise MigratieFout(res.stderr.strip() or f"psql faalde met exitcode {res.returncode}")
    return res.stdout


def lees_toegepast(uitvoer: str) -> dict[int, str]:
    toegepast = {}
    for regel in uitvoer.splitlines():
        if regel.strip():
            versie, chk = regel.split("|", 1)
            toegepast[int(versie)] = chk.strip()
    return toegepast


def registreer_sql(m: Migratie) -> str:
    # naam is [A-Za-z0-9_]+ (BESTANDSNAAM) en checksum hex: veilig als literal
    return (f"INSERT INTO public.schema_migraties (versie, naam, checksum) "
            f"VALUES ({m.versie}, '{m.naam}', '{m.checksum}');")


def migreer(map_: Path = MIGRATIE_MAP, uitvoeren: Psql = psql, alleen_status: bool = False,
            log: Callable[[str], None] = print) -> list[Migratie]:
    """Pas openstaande migraties toe; geeft de toegepaste (of, bij alleen_status, openstaande) terug."""
    migraties = zoek_migraties(map_)
    uitvoeren(["-c", TABEL_SQL])
    toegepast = lees_toegepast(uitvoeren(["-At", "-c", "SELECT versie, checksum FROM public.schema_migraties ORDER BY versie"]))
    te_doen, waarschuwingen = plan(migraties, toegepast)
    for w in waarschuwingen:
        log(f"⚠️  {w}")
    if alleen_status:
        for m in migraties:
            log(f"   {'open     ' if m in te_doen else 'toegepast'}  {m.label}")
        return te_doen
    if not te_doen:
        log(f"✅ Migraties: niets te doen ({len(toegepast)} toegepast).")
        return []
    for m in te_doen:
        log(f"⚙️  Migratie {m.label} toepassen...")
        uitvoeren(["--single-transaction", "-f", str(m.pad), "-c", registreer_sql(m)])
    log(f"✅ Migraties: {len(te_doen)} toegepast ({', '.join(m.label for m in te_doen)}).")
    return te_doen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pas de migraties in db/migraties toe (#54).")
    parser.add_argument("--map", type=Path, default=MIGRATIE_MAP, help="map met V<versie>__<naam>.sql")
    parser.add_argument("--status", action="store_true", help="alleen tonen wat toegepast en open is")
    args = parser.parse_args(argv)
    try:
        migreer(args.map, alleen_status=args.status)
    except MigratieFout as e:
        print(f"❌ Migratie mislukt: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
