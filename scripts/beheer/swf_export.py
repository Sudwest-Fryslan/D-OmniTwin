#!/usr/bin/env python3
"""
Export uit een dump van de lokale D-OmniTwin-database van SWF (#222 A1)
======================================================================
Leest een herstelde dump van de lokale D-OmniTwin-database van de projectleider. Geen 1-op-1
restore: het script haalt eruit wat de use cases nodig hebben; die laden het via de laad-API en de
beheerroute (niets gaat buiten de laadstraat om de database in).

Twee doelen (besluit projectleiding 04-10-2026: de data is openbaar):

1. `--repo`: wat **niet online te downloaden** is, als bestand bij de use case waar het hoort
   (in git, via een PR):

   | Bestand | Uit | Use case |
   |---|---|---|
   | `usecases/swf-gebiedsindelingen/data/welstandsgebieden.gpkg` | gebieden (welstand × buurt), EPSG:28992, zonder ruimtelijke index | swf-gebiedsindelingen |
   | `usecases/swf-kompasprofiel/data/kompasprofiel_<naam>.json` | kompas_* (profielen met koppelingen), formaat van `db/stuurdata/kompasprofiel_*.json` plus `weging`, `is_actueel` | swf-kompasprofiel |
   | `usecases/swf-kaartlagen/data/externe_kaartlagen.json` | externe_kaartlagen, met `toegang` (B3: GeoVisia en projecten 'in plan' intern) | swf-kaartlagen |
   | `herkomst.json` in elke map | – | herkomst, aantallen, controlesommen |

2. `--uit DIR` (`SWF_EXPORT_DIR`, nooit in git): wat online te halen is maar nog geen adapter heeft
   (BAG, RVO EP-Online, OpenStreetMap) plus de monitorwaarden uit de dump, voor de use case
   swf-initialisatie: `gebied_data.csv` (Fryslân + welstandsgebieden; standaard alleen wat meegaat:
   geen DEMODATA, geen open data die een eigen use case downloadt, geen waarde zonder bron, geen
   provincie; `--alles` laat alleen DEMODATA weg), `indicatoren.csv` (alleen definities die de waarden
   of het Kompas gebruiken en die nog niet uit swf-definities of de stuurdata komen) en `export.json`.

    python scripts/beheer/swf_export.py --repo --uit /pad/naar/export --dump-datum 2026-10-04 \
        --monitor-definities "$SWF_DUMP_DIR/output/api_backup_dump.json"

Verbinding: `--dsn` (libpq-sleutelwoorden, bijv. "host=localhost dbname=swfbron user=...") of de
standaard PG-omgevingsvariabelen (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD). Zet nooit een
wachtwoord in een script of in de repo. Vereist psycopg2 en (voor de welstandsgebieden) fiona en
shapely: draai het in de backend-image (zie usecases/swf-initialisatie/README.md).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WELSTAND = "29fc9f28-89d9-488b-bf68-2ed176187b21"  # gebiedstype welstand × buurt (codes 1..758 → WS1..)
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
# Definities die D-OmniTwin al zelf levert (stuurdata, sample, CBS-recept): niet opnieuw uit de export
REPO_DEFINITIES = (
    "db/stuurdata/indicatoren.csv",
    "init_data/sample/2_brondata/sample_indicatoren.csv",
    "init_data/cbs/datapackage.json",
)
REPO_WELSTAND = "usecases/swf-gebiedsindelingen/data/welstandsgebieden.gpkg"
REPO_KOMPAS = "usecases/swf-kompasprofiel/data"
REPO_KAARTLAGEN = "usecases/swf-kaartlagen/data/externe_kaartlagen.json"
# Standaard (zonder --alles): wat de use case swf-initialisatie toch zou weglaten, niet exporteren (de use case houdt
# dezelfde regels als controle, met aantal 0). Open data downloadt de eigen use case.
OPEN_DATA = ("CBS", "Gezondheidsmonitor RIVM", "Kerncijfers wijken en buurten")
PROVINCIE = "22401c4c-8272-4895-a0a2-a8d48a0b4c36"
# Aanname B3 (#222): alleen voor ingelogden
INTERN = re.compile(r"geovisia|in plan", re.IGNORECASE)

INDICATOR_KOLOMMEN = (
    "uuid",
    "naam",
    "code",
    "omschrijving",
    "eenheid",
    "score_type",
    "min_waarde",
    "max_waarde",
    "status",
    "begingeldigheid",
    "eindgeldigheid",
    "bron",
)
WAARDE_KOLOMMEN = (
    "gebied_id",
    "gebiedstype_id",
    "indicator_uuid",
    "jaar",
    "peildatum",
    "scenario_id",
    "waarde",
    "n",
    "kwaliteit",
    "bron",
)
KAARTLAAG_KOLOMMEN = (
    "naam",
    "beschrijving",
    "laag_type",
    "bron_type",
    "url",
    "typename",
    "srsname",
    "versie",
    "filter_type",
    "filter_waarde",
    "koppel_veld",
    "kleur_lijn",
    "kleur_fill",
    "opacity",
    "actief",
    "volgorde",
)


# ------------------------------------------------------------------ zonder database (getest)


def bekende_definities(monitor_definities: Path | None, root: Path = ROOT) -> set[str]:
    """UUID's waarvan D-OmniTwin de definitie al uit een andere bron haalt: de SWF-definities (export
    van de monitor, use case swf-definities) en de stuurdata/sample/CBS-recept in de repo."""
    bekend = set()
    for rel in REPO_DEFINITIES:
        pad = root / rel
        if pad.exists():
            bekend |= set(UUID.findall(pad.read_text(encoding="utf-8")))
    if monitor_definities:
        data = json.loads(Path(monitor_definities).read_text(encoding="utf-8"))
        bekend |= {str(i.get("id") or i.get("uuid")).lower() for i in data.get("indicatoren", [])}
    return bekend


def toegang(laag: dict) -> str:
    """'intern' voor GeoVisia en projecten 'in plan' (aanname B3, #222), anders 'openbaar'."""
    tekst = " ".join(str(laag.get(k) or "") for k in ("naam", "beschrijving", "typename"))
    return "intern" if INTERN.search(tekst) else "openbaar"


def slug(naam: str) -> str:
    s = re.sub(r"[^0-9a-z]+", "_", naam.lower()).strip("_")
    return s or "profiel"


def kompasprofielen(regels: list[dict]) -> list[dict]:
    """Regels (profiel, classificatie, beschrijving, kwadrant, thema, onderdeel, indicator_uuid, indicator_naam,
    weging, is_actueel) → één profiel per naam, in het formaat van db/stuurdata/kompasprofiel_*.json."""
    uit: dict[str, dict] = {}
    for r in regels:
        p = uit.setdefault(
            r["profiel"],
            {
                "omschrijving": r.get("beschrijving") or "",
                "profiel": r["profiel"],
                "classificatie": r.get("classificatie") or "zscore",
                "indicatoren": [],
            },
        )
        p["indicatoren"].append(
            {
                "kwadrant": r["kwadrant"],
                "thema": r["thema"],
                "onderdeel": r.get("onderdeel") or "",
                "indicator_uuid": str(r["indicator_uuid"]),
                "indicator_naam": r.get("indicator_naam") or "",
                "weging": float(r["weging"]) if r.get("weging") is not None else 1.0,
                "is_actueel": bool(r.get("is_actueel")),
            }
        )
    return list(uit.values())


def sha256(pad: Path) -> str:
    h = hashlib.sha256()
    with open(pad, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def _tekst(w):
    if w is None:
        return ""
    if isinstance(w, (dt.datetime, dt.date)):
        return w.isoformat(sep=" ") if isinstance(w, dt.datetime) else w.isoformat()
    return str(w)


# ------------------------------------------------------------------ export


def verbind(dsn: str):
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(dsn)  # leeg: PGHOST, PGDATABASE, PGUSER, ... uit de omgeving
    conn.set_client_encoding("UTF8")
    conn.set_session(readonly=True)
    return conn, psycopg2.extras.RealDictCursor


def mee_voorwaarde() -> str:
    """SQL-voorwaarde (standaard, zonder --alles): geen open data, geen waarde zonder bron, geen provincie."""
    open_data = " AND ".join(f"d.bron NOT LIKE '{p}%%'" for p in OPEN_DATA)
    return f"(coalesce(d.bron, '') <> '' AND {open_data} AND g.gebiedstype_id <> '{PROVINCIE}')"


def exporteer_waarden(cur, uit: Path, provincie: str, alleen_mee: bool = False) -> dict:
    """gebied_data.csv: alles binnen het gebied van de installatie, zonder DEMODATA (met alleen_mee ook zonder
    open data, waarden zonder bron en provincies). Geeft de aantallen."""
    p = {"welstand": WELSTAND, "provincie": provincie}
    binnen = "(g.gebiedstype_id = %(welstand)s OR g.provincienaam = %(provincie)s)"
    niet_mee = 0
    if alleen_mee:
        cur.execute(
            f"""SELECT count(*) AS n FROM gebied_data d JOIN gebieden g ON g.id = d.gebied_id
                        WHERE coalesce(d.bron, '') NOT LIKE 'DEMODATA%%' AND {binnen} AND NOT {mee_voorwaarde()}""",
            p,
        )
        niet_mee = cur.fetchone()["n"]
        binnen = f"({binnen} AND {mee_voorwaarde()})"
    cur.execute("SELECT count(*) AS n FROM gebied_data", p)
    totaal = cur.fetchone()["n"]
    cur.execute("SELECT count(*) AS n FROM gebied_data d WHERE coalesce(d.bron, '') LIKE 'DEMODATA%%'", p)
    demodata = cur.fetchone()["n"]
    cur.execute(
        f"""SELECT count(*) AS n FROM gebied_data d JOIN gebieden g ON g.id = d.gebied_id
                    WHERE coalesce(d.bron, '') NOT LIKE 'DEMODATA%%' AND NOT {binnen}""",
        p,
    )
    buiten = cur.fetchone()["n"]
    sql = cur.mogrify(
        f"""
        SELECT d.gebied_id, g.gebiedstype_id, d.indicator_uuid, d.jaar,
               CASE WHEN d.jaar IS NULL THEN d.datum::date END AS peildatum,
               coalesce(d.scenario_id, 'current') AS scenario_id, d.waarde, d.n, d.kwaliteit, d.bron
        FROM gebied_data d JOIN gebieden g ON g.id = d.gebied_id
        WHERE coalesce(d.bron, '') NOT LIKE 'DEMODATA%%' AND {binnen}
        ORDER BY d.indicator_uuid, g.gebiedstype_id, d.gebied_id, d.jaar, d.datum""",
        p,
    ).decode()
    with open(uit / "gebied_data.csv", "w", encoding="utf-8", newline="") as f:
        cur.copy_expert(f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)", f)
    cur.execute(
        f"""SELECT coalesce(d.bron, '') AS bron, count(*) AS n FROM gebied_data d
                    JOIN gebieden g ON g.id = d.gebied_id
                    WHERE coalesce(d.bron, '') NOT LIKE 'DEMODATA%%' AND {binnen}
                    GROUP BY 1 ORDER BY 2 DESC, 1""",
        p,
    )
    per_bron = {r["bron"]: r["n"] for r in cur.fetchall()}
    return {
        "totaal_in_database": totaal,
        "demodata": demodata,
        "buiten_gebied": buiten - niet_mee,
        "niet_mee": niet_mee,
        "geschreven": sum(per_bron.values()),
        "per_bron": per_bron,
    }


def exporteer_welstand(cur, pad: Path) -> int:
    """GeoPackage (EPSG:28992) met id, naam, aanduiding; geen ruimtelijke index (kleiner, zelfde geometrie)."""
    import fiona
    from fiona.crs import CRS
    from shapely import wkb
    from shapely.geometry import mapping

    cur.execute(
        """SELECT id, naam, metadata->>'aanduiding' AS aanduiding, ST_AsBinary(ST_Multi(geom)) AS geom
                   FROM gebieden WHERE gebiedstype_id = %s AND geom IS NOT NULL
                   ORDER BY (CASE WHEN id ~ '^[0-9]+$' THEN id::int END), id""",
        (WELSTAND,),
    )
    rijen = cur.fetchall()
    pad.parent.mkdir(parents=True, exist_ok=True)
    if pad.exists():
        pad.unlink()
    schema = {"geometry": "MultiPolygon", "properties": {"id": "str", "naam": "str", "aanduiding": "str"}}
    with fiona.open(
        pad, "w", driver="GPKG", layer="welstandsgebieden", crs=CRS.from_epsg(28992), schema=schema, SPATIAL_INDEX="NO"
    ) as dst:  # kleiner bestand; de laadstraat leest alles
        dst.writerecords(
            {
                "geometry": mapping(wkb.loads(bytes(r["geom"]))),
                "properties": {"id": r["id"], "naam": r["naam"], "aanduiding": r["aanduiding"]},
            }
            for r in rijen
        )
    return len(rijen)


def exporteer_kompas(cur, uit: Path) -> dict:
    uit.mkdir(parents=True, exist_ok=True)
    cur.execute("""
        SELECT c.naam AS profiel, c.classificatie, c.beschrijving, t.naam AS kwadrant, th.naam AS thema,
               o.naam AS onderdeel, m.indicator_uuid, i.naam AS indicator_naam, m.weging, m.is_actueel
        FROM kompas_indicator_mapping m
        JOIN kompas_configuraties c ON c.id = m.config_id
        JOIN kompas_onderdelen o ON o.id = m.onderdeel_id
        JOIN kompas_themas th ON th.id = o.thema_id
        JOIN kompas_titels t ON t.id = th.titel_id
        LEFT JOIN indicatoren i ON i.uuid = m.indicator_uuid
        ORDER BY c.id, t.volgorde, t.id, th.volgorde, th.id, o.volgorde, o.id, m.id""")
    profielen = kompasprofielen(cur.fetchall())
    bestanden = {}
    for p in profielen:
        pad = uit / f"kompasprofiel_{slug(p['profiel'])}.json"
        pad.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        bestanden[pad.name] = {
            "profiel": p["profiel"],
            "indicatoren": len(p["indicatoren"]),
            "unieke_indicatoren": len({i["indicator_uuid"] for i in p["indicatoren"]}),
        }
    niet = {}
    for t in ("kompas_extra_onderdelen", "kompas_indicator_extra_tags", "kompas_indicator_scoring_regels"):
        cur.execute(f"SELECT count(*) AS n FROM {t}")
        niet[t] = cur.fetchone()["n"]
    cur.execute("""SELECT c.naam FROM kompas_configuraties c
                   WHERE NOT EXISTS (SELECT 1 FROM kompas_indicator_mapping m WHERE m.config_id = c.id) ORDER BY c.id""")
    leeg = [r["naam"] for r in cur.fetchall()]
    return {"bestanden": bestanden, "lege_profielen": leeg, "niet_geexporteerd": niet}


def exporteer_kaartlagen(cur, pad: Path) -> dict:
    cur.execute(f"SELECT {', '.join(KAARTLAAG_KOLOMMEN)} FROM externe_kaartlagen ORDER BY volgorde, id")
    lagen, lokaal = [], []
    for r in cur.fetchall():
        if r["bron_type"] == "lokaal":  # bestand in de oude installatie; lokale lagen gaan via de laad-API
            lokaal.append(r["naam"])
            continue
        laag = {k: r[k] for k in KAARTLAAG_KOLOMMEN}
        laag["opacity"] = float(laag["opacity"]) if laag["opacity"] is not None else None
        laag["toegang"] = toegang(laag)
        lagen.append(laag)
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(lagen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {
        "lagen": len(lagen),
        "intern": [la["naam"] for la in lagen if la["toegang"] == "intern"],
        "lokaal_niet_geexporteerd": lokaal,
    }


def exporteer_indicatoren(cur, uit: Path, bekend: set[str], waarden_csv: Path) -> dict:
    """indicatoren.csv: gebruikt (waarden of Kompas) en niet al elders gedefinieerd."""
    gebruikt = set()
    with open(waarden_csv, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            gebruikt.add(r["indicator_uuid"])
    cur.execute("SELECT DISTINCT indicator_uuid::text AS u FROM kompas_indicator_mapping")
    gebruikt |= {r["u"] for r in cur.fetchall()}
    nodig = sorted(u for u in gebruikt if u not in bekend)
    cur.execute(
        f"SELECT uuid::text AS uuid, {', '.join(INDICATOR_KOLOMMEN[1:])} FROM indicatoren "
        "WHERE uuid::text = ANY(%s) ORDER BY naam, uuid",
        (nodig,),
    )
    rijen = cur.fetchall()
    with open(uit / "indicatoren.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(INDICATOR_KOLOMMEN)
        for r in rijen:
            w.writerow([_tekst(r[k]) for k in INDICATOR_KOLOMMEN])
    cur.execute("SELECT count(*) AS n FROM indicatoren")
    return {
        "in_database": cur.fetchone()["n"],
        "gebruikt": len(gebruikt),
        "al_bekend": len(gebruikt) - len(nodig),
        "geschreven": len(rijen),
        "zonder_definitie": sorted(set(nodig) - {r["uuid"] for r in rijen}),
    }


def herkomst(map_: Path, dump_datum: str | None, inhoud: dict) -> None:
    """herkomst.json naast de bestanden in de repo: waar het vandaan komt, aantallen, controlesommen."""
    bestanden = {p.name: sha256(p) for p in sorted(map_.iterdir()) if p.is_file() and p.name != "herkomst.json"}
    (map_ / "herkomst.json").write_text(
        json.dumps(
            {
                "bron": "lokale D-OmniTwin-database van de projectleider SWF (dump)",
                "dump_datum": dump_datum,
                "toegang": "openbaar (besluit projectleiding 04-10-2026, https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/222)",
                "gemaakt_met": "scripts/beheer/swf_export.py --repo",
                "inhoud": inhoud,
                "bestanden": bestanden,
            },
            ensure_ascii=False,
            indent=1,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    import os

    a = argparse.ArgumentParser(
        description=__doc__.split("\n")[1], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument("--uit", help="exportmap voor swf-initialisatie (SWF_EXPORT_DIR, niet in git)")
    a.add_argument(
        "--repo",
        action="store_true",
        help="welstandsgebieden, Kompas en externe kaartlagen naar de data-mappen van hun use case in deze repo",
    )
    a.add_argument("--repo-map", default=str(ROOT), help="root van de repo (standaard die van dit script)")
    a.add_argument("--dsn", default="", help="libpq-verbinding; leeg = PG*-omgevingsvariabelen")
    a.add_argument(
        "--monitor-definities",
        help="api_backup_dump.json van de monitor (standaard "
        "$SWF_DUMP_DIR/output/api_backup_dump.json): die definities levert swf-definities",
    )
    a.add_argument("--provincie", default="Fryslân", help="gebied van de installatie (gebieden.provincienaam)")
    a.add_argument(
        "--alles",
        action="store_true",
        help="--uit: ook open data, waarden zonder bron en provincies (de use case laat ze dan weg en telt ze)",
    )
    a.add_argument("--dump-datum", help="datum van de dump (JJJJ-MM-DD), voor herkomst.json en export.json")
    args = a.parse_args(argv)
    if not args.uit and not args.repo:
        a.error("geef --uit, --repo of beide")
    monitor = args.monitor_definities or (
        str(Path(os.environ["SWF_DUMP_DIR"]) / "output" / "api_backup_dump.json")
        if os.environ.get("SWF_DUMP_DIR")
        else None
    )
    if args.uit and (not monitor or not Path(monitor).exists()):
        print(
            "FOUT: de definities van de monitor zijn nodig (--monitor-definities of SWF_DUMP_DIR), anders "
            "levert de export definities opnieuw die swf-definities al levert.",
            file=sys.stderr,
        )
        return 2
    conn, dict_cursor = verbind(args.dsn)
    try:
        with conn.cursor(cursor_factory=dict_cursor) as cur:
            if args.repo:
                repo = Path(args.repo_map)
                n = exporteer_welstand(cur, repo / REPO_WELSTAND)
                herkomst((repo / REPO_WELSTAND).parent, args.dump_datum, {"welstandsgebieden": n})
                print(f"{REPO_WELSTAND}: {n} gebieden")
                k = exporteer_kompas(cur, repo / REPO_KOMPAS)
                herkomst(repo / REPO_KOMPAS, args.dump_datum, k)
                print(f"{REPO_KOMPAS}: {k['bestanden']}")
                la = exporteer_kaartlagen(cur, repo / REPO_KAARTLAGEN)
                herkomst((repo / REPO_KAARTLAGEN).parent, args.dump_datum, la)
                print(f"{REPO_KAARTLAGEN}: {la['lagen']} lagen")
            if args.uit:
                uit = Path(args.uit)
                uit.mkdir(parents=True, exist_ok=True)
                samenvatting = {
                    "gemaakt_op": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                    "database": conn.get_dsn_parameters().get("dbname"),
                    "dump_datum": args.dump_datum,
                    "provincie": args.provincie,
                    "alleen_mee": not args.alles,
                }
                samenvatting["gebied_data"] = exporteer_waarden(cur, uit, args.provincie, not args.alles)
                print(f"gebied_data.csv: {samenvatting['gebied_data']['geschreven']} waarden")
                samenvatting["indicatoren"] = exporteer_indicatoren(
                    cur, uit, bekende_definities(Path(monitor)), uit / "gebied_data.csv"
                )
                print(f"indicatoren.csv: {samenvatting['indicatoren']['geschreven']} definities")
                samenvatting["bestanden"] = {
                    p.name: sha256(p) for p in sorted(uit.iterdir()) if p.is_file() and p.name != "export.json"
                }
                (uit / "export.json").write_text(
                    json.dumps(samenvatting, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
                )
                print(f"klaar: {uit}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
