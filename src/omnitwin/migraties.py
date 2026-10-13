"""
Migratierunner (#54): past de schemamigraties in db/migraties/ in volgorde toe.

    python -m omnitwin.migraties            # toepassen wat nog niet in schema_migraties staat
    python -m omnitwin.migraties --status   # alleen tonen, niets toepassen (alleen-lezen)

Een migratie is een bestand ``V<versie>__<naam>.sql`` (Flyway-stijl, bijv.
``V018__trigram.sql``). De runner

1. maakt zo nodig de tabel ``schema_migraties`` (versie, naam, checksum, toegepast_op);
2. past elke migratie waarvan de versie nog niet in die tabel staat toe, op volgorde
   van versie, en registreert hem in dezelfde transactie (``psql --single-transaction``);
3. waarschuwt (geen fout) als een al toegepaste migratie sindsdien gewijzigd is.

Een bestaande database zonder ``schema_migraties`` krijgt de tabel en alle migraties
opnieuw: ze zijn idempotent geschreven. Een nieuwe migratie moet dat ook zijn.

Gelijktijdige runs (bijv. twee keer ``db-init`` tegen dezelfde database): de runner
neemt een advisory lock (``pg_advisory_lock``, sleutel ``SLOT_SLEUTEL``) in een eigen
psql-sessie, vóór hij ``schema_migraties`` leest, en houdt die vast tot alles is
toegepast. Een tweede run wacht en ziet daarna dat er niets meer te doen is (#202).
``--status`` neemt geen lock en maakt de tabel niet aan.

De bestanden worden uitgevoerd met ``psql`` (ON_ERROR_STOP), zoals voorheen in
docker-entrypoint.sh: migraties mogen psql-opdrachten als ``\\ir`` bevatten. De
checksum (sha256) telt de bestanden mee die met ``\\ir``/``\\i`` worden ingelezen,
en negeert het verschil tussen CRLF en LF (checkout op Windows). Gevolg: wie een
ingelezen bestand wijzigt, wijzigt ook de checksum van de migratie die het inleest
(V021 leest ``db/schema/08_zscore_referentie.sql``). ``--status`` en de waarschuwing
noemen die bestanden; zie db/README.md.

Verbinding: de gewone libpq-variabelen (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD);
ontbreken die, dan DATABASE_HOST/PORT/NAME/USER/PASSWORD zoals in .env.

Niet hier: ``R__*.sql`` (herhaalbaar, bijv. ``R__api_rollen.sql``). Die voert
docker-entrypoint.sh bij elke start uit.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # root van de repository (src/omnitwin/migraties.py)
MIGRATIE_MAP = ROOT / "db" / "migraties"

BESTANDSNAAM = re.compile(r"^V(\d+)__([A-Za-z0-9_]+)\.sql$")
INCLUDE = re.compile(r"^\s*\\i[r]?\s+(\S+)", re.MULTILINE)

# Sleutel voor pg_advisory_lock: één runner tegelijk per database (#202)
SLOT_SLEUTEL = 54_202

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
    includes: tuple[str, ...] = ()  # bestanden die via \i/\ir meetellen in de checksum

    @property
    def label(self) -> str:
        return f"V{self.versie:03d} {self.naam}"


def _toon(pad: Path) -> str:
    try:
        return pad.relative_to(ROOT).as_posix()
    except ValueError:
        return pad.name


def _includes(pad: Path, gezien: frozenset = frozenset()) -> list[Path]:
    """Bestanden die pad (recursief) met \\i/\\ir inleest."""
    if pad in gezien:
        return []
    uit: list[Path] = []
    for match in INCLUDE.finditer(pad.read_bytes().decode("utf-8")):
        include = (pad.parent / match.group(1)).resolve()
        if include.is_file():
            uit += [include, *_includes(include, gezien | {pad})]
    return uit


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
    if not map_.is_dir():
        raise MigratieFout(f"Map met migraties niet gevonden: {map_}")
    migraties: dict[int, Migratie] = {}
    for pad in sorted(map_.glob("V*.sql")):
        m = BESTANDSNAAM.match(pad.name)
        if not m:
            raise MigratieFout(f"Ongeldige migratienaam: {pad.name} (verwacht V<versie>__<naam>.sql)")
        versie = int(m.group(1))
        if versie in migraties:
            raise MigratieFout(f"Versie {versie} komt twee keer voor: {migraties[versie].pad.name} en {pad.name}")
        includes = tuple(dict.fromkeys(_toon(p) for p in _includes(pad.resolve())))
        migraties[versie] = Migratie(versie, m.group(2), pad, checksum(pad), includes)
    return [migraties[v] for v in sorted(migraties)]


def plan(migraties: Iterable[Migratie], toegepast: dict[int, str]) -> tuple[list[Migratie], list[str]]:
    """Wat nog moet, en waarschuwingen voor toegepaste migraties met een andere checksum."""
    te_doen, waarschuwingen = [], []
    for m in migraties:
        if m.versie not in toegepast:
            te_doen.append(m)
        elif toegepast[m.versie] != m.checksum:
            meetellend = f" De checksum telt ook mee: {', '.join(m.includes)}." if m.includes else ""
            waarschuwingen.append(
                f"{m.label} is gewijzigd sinds hij is toegepast (checksum verschilt). "
                "Hij wordt niet opnieuw uitgevoerd; zet een wijziging in een nieuwe migratie." + meetellend
            )
    return te_doen, waarschuwingen


# ── psql ────────────────────────────────────────────────────────────────────

Psql = Callable[[list[str]], str]


def _psql_omgeving() -> dict[str, str]:
    env = dict(os.environ)
    # Standaardwaarden zoals in docker-entrypoint.sh en database.py
    for pg, db, standaard in [
        ("PGHOST", "DATABASE_HOST", None),
        ("PGPORT", "DATABASE_PORT", None),
        ("PGDATABASE", "DATABASE_NAME", "omnitwin_db"),
        ("PGUSER", "DATABASE_USER", "omnitwin_user"),
        ("PGPASSWORD", "DATABASE_PASSWORD", None),
    ]:
        waarde = env.get(pg) or env.get(db) or standaard
        if waarde:
            env[pg] = waarde
    # Geen NOTICE's van CREATE ... IF NOT EXISTS in de log
    env.setdefault("PGOPTIONS", "-c client_min_messages=warning")
    return env


def psql(args: list[str]) -> str:
    """Draai psql (ON_ERROR_STOP, zonder psqlrc) en geef stdout terug; fout bij exitcode != 0."""
    res = subprocess.run(
        ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", *args], capture_output=True, text=True, env=_psql_omgeving()
    )
    if res.returncode != 0:
        raise MigratieFout(res.stderr.strip() or f"psql faalde met exitcode {res.returncode}")
    return res.stdout


Slot = Callable[[], AbstractContextManager[None]]


@contextlib.contextmanager
def psql_slot(sleutel: int = SLOT_SLEUTEL, log: Callable[[str], None] = print) -> Iterator[None]:
    """Houd pg_advisory_lock(sleutel) vast in een eigen psql-sessie zolang het blok loopt.

    De lock hoort bij de sessie: hij vervalt als psql stopt, ook bij een crash.
    """
    proc = subprocess.Popen(
        ["psql", "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_psql_omgeving(),
    )

    def vraag(sql: str) -> str:
        proc.stdin.write(sql + "\n")
        proc.stdin.flush()
        antwoord = proc.stdout.readline()
        if not antwoord:  # psql gestopt: geen verbinding of een fout
            proc.wait()
            raise MigratieFout(f"advisory lock niet gekregen: {proc.stderr.read().strip() or 'psql gestopt'}")
        return antwoord.strip()

    try:
        if vraag(f"SELECT pg_try_advisory_lock({sleutel});") != "t":
            log("⏳ Een andere migratierun is bezig; wachten tot die klaar is...")
            vraag(f"SELECT 'ok' FROM pg_advisory_lock({sleutel});")
        yield
    finally:
        try:
            proc.stdin.write("\\q\n")
            proc.stdin.close()
            proc.wait(timeout=30)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            proc.kill()


def lees_toegepast(uitvoer: str) -> dict[int, str]:
    toegepast = {}
    for regel in uitvoer.splitlines():
        if regel.strip():
            versie, chk = regel.split("|", 1)
            toegepast[int(versie)] = chk.strip()
    return toegepast


def registreer_sql(m: Migratie) -> str:
    # naam is [A-Za-z0-9_]+ (BESTANDSNAAM) en checksum hex: veilig als literal
    return (
        f"INSERT INTO public.schema_migraties (versie, naam, checksum) VALUES ({m.versie}, '{m.naam}', '{m.checksum}');"
    )


LEES_SQL = "SELECT versie, checksum FROM public.schema_migraties ORDER BY versie"
BESTAAT_SQL = "SELECT to_regclass('public.schema_migraties') IS NOT NULL"


def migreer(
    map_: Path = MIGRATIE_MAP,
    uitvoeren: Psql = psql,
    alleen_status: bool = False,
    log: Callable[[str], None] = print,
    slot: Slot | None = None,
) -> list[Migratie]:
    """Pas openstaande migraties toe; geeft de toegepaste (of, bij alleen_status, openstaande) terug.

    slot: contextmanager die zorgt dat maar één run tegelijk migreert. Standaard
    psql_slot (advisory lock) als uitvoeren de echte psql is, anders geen.
    """
    migraties = zoek_migraties(map_)
    if alleen_status:
        # Alleen-lezen: geen lock, tabel niet aanmaken
        bestaat = uitvoeren(["-At", "-c", BESTAAT_SQL]).strip() == "t"
        toegepast = lees_toegepast(uitvoeren(["-At", "-c", LEES_SQL])) if bestaat else {}
        te_doen, waarschuwingen = plan(migraties, toegepast)
        for w in waarschuwingen:
            log(f"⚠️  {w}")
        for m in migraties:
            meetellend = f"  (+ {', '.join(m.includes)})" if m.includes else ""
            log(f"   {'open     ' if m in te_doen else 'toegepast'}  {m.label}{meetellend}")
        return te_doen

    if slot is None:
        slot = (lambda: psql_slot(log=log)) if uitvoeren is psql else contextlib.nullcontext
    with slot():
        # Pas lezen als de lock er is: wat een run vlak ervoor toepaste, telt dan mee
        uitvoeren(["-c", TABEL_SQL])
        toegepast = lees_toegepast(uitvoeren(["-At", "-c", LEES_SQL]))
        te_doen, waarschuwingen = plan(migraties, toegepast)
        for w in waarschuwingen:
            log(f"⚠️  {w}")
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
