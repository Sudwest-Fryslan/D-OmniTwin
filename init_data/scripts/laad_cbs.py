#!/usr/bin/env python3
"""
D-OmniTwin — CBS Kerncijfers (alle jaargangen) laden
====================================================
Haalt de CBS-reeksen op voor de gebieden die in de database staan en laadt ze in gebied_data.
De data staat niet in git: download_cbs_kerncijfers.rijen_voor() leest de cache ($DATA_CACHE/cbs)
of downloadt bij CBS en vult de cache. Geen netwerk en geen cache: waarschuwing, geen fout.
Voor welke gebieden:

- na db-init met LOAD_SAMPLE_DATA=true: de gebieden van de use cases;
- na seed_fryslan.py (buurten): alle buurten van Fryslân.

Per waarde: jaar = peiljaar van de CBS-tabel, bron = "CBS Kerncijfers wijken en buurten <jaar> (<tabel>)",
en metadata.bron_tabel = het tabel-ID. Indicatoren worden op UUID gekoppeld (dezelfde als de sample);
ontbreekt de UUID, dan op naam; ontbreekt die ook, dan wordt de indicator aangemaakt.

Idempotent: opnieuw laden werkt dezelfde rijen bij. Oude, verkeerd gelabelde CBS-rijen
("Kerncijfers wijken en buurten 2023" = eigenlijk 2021, #159) voor deze indicatoren worden verwijderd.

Gebruik:
    python init_data/scripts/laad_cbs.py                    # alle gebieden in de database
    python init_data/scripts/laad_cbs.py BU19000001 ...     # alleen deze gebieden
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_cbs_kerncijfers as cbs  # noqa: E402
import load_sample  # noqa: E402  (databaseverbinding hergebruiken)

from psycopg2.extras import execute_values  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUDE_BRONNEN = ("Kerncijfers wijken en buurten 2023",)  # verkeerd label van 85039NED (2021)


def lees(gebieden):
    """Reeksen voor deze buurten (cache of download). Alleen CBS-buurtcodes (BU...)."""
    buurten = sorted(g for g in gebieden if g.startswith("BU"))
    if not buurten:
        return []
    try:
        return cbs.rijen_voor(buurten)
    except Exception as e:  # geen netwerk, CBS onbereikbaar, tabel gewijzigd
        print(
            f"   ⚠️  CBS Kerncijfers niet opgehaald ({type(e).__name__}: {e}). Zonder internet: "
            f"vul de cache ($DATA_CACHE/cbs) met download_cbs_kerncijfers.py --alle op een machine met internet."
        )
        return []


def indicator_uuids(cur, rijen):
    """CSV-UUID -> UUID in de database (zelfde UUID, anders op naam, anders nieuw aangemaakt)."""
    meta = {}
    for r in rijen:
        meta.setdefault(r["indicator_uuid"], r)
    cur.execute("SELECT uuid::text, lower(naam) FROM indicatoren")
    bestaand = cur.fetchall()
    op_uuid = {u for u, _ in bestaand}
    op_naam = {}
    for u, n in bestaand:
        op_naam.setdefault(n, u)
    uit = {}
    for u, r in meta.items():
        if u in op_uuid:
            uit[u] = u
        elif r["indicator_naam"].lower() in op_naam:
            uit[u] = op_naam[r["indicator_naam"].lower()]
        else:
            naam = r["indicator_naam"]
            code = f"IND_{''.join(c if c.isalnum() else '_' for c in naam.upper())[:30]}_{u[:8]}"
            logica = r["interpretatie_logica"] or "pos_is_pos"
            cur.execute(
                "INSERT INTO indicatoren (uuid, naam, code, eenheid, categorie, interpretatie_logica, bron, "
                "score_type, status, is_actief) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'O', TRUE) "
                "ON CONFLICT (uuid) DO NOTHING",
                (
                    u,
                    naam,
                    code,
                    r["eenheid"] or None,
                    r["categorie"] or None,
                    logica,
                    "CBS Kerncijfers wijken en buurten",
                    "+/-" if logica == "-/+" else "+/+",
                ),
            )
            uit[u] = u
            print(f"   ➕ indicator aangemaakt: {naam}")
    return uit


def laad(conn, gebied_ids=None):
    """Laadt de CBS-reeksen voor gebied_ids (standaard: alle actieve gebieden in de database)."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM gebieden WHERE actief = true")
    in_db = {r[0] for r in cur.fetchall()}
    gebieden = in_db if gebied_ids is None else in_db & set(gebied_ids)
    rijen = lees(gebieden)
    if not rijen:
        print(f"   ℹ️  CBS Kerncijfers: geen rijen voor {len(gebieden)} gebieden")
        cur.close()
        return 0

    uuids = indicator_uuids(cur, rijen)
    doel = sorted(set(uuids.values()))
    # Oude, verkeerd gelabelde rijen van dezelfde indicatoren in deze gebieden weghalen
    cur.execute(
        "DELETE FROM gebied_data WHERE indicator_uuid = ANY(%s::uuid[]) AND gebied_id = ANY(%s) AND bron = ANY(%s)",
        (doel, sorted({r["gebied_id"] for r in rijen}), list(OUDE_BRONNEN)),
    )
    verwijderd = cur.rowcount

    waarden = {}
    for r in rijen:
        key = (r["gebied_id"], uuids[r["indicator_uuid"]], int(r["jaar"]), r["scenario_id"] or "current")
        waarden[key] = key[:2] + (
            float(r["waarde"]),
            key[2],
            r["bron"],
            None,
            key[3],
            json.dumps({"bron_tabel": r["bron_tabel"]}),
        )
    execute_values(
        cur,
        """
        INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, kwaliteit, scenario_id, metadata)
        VALUES %s
        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
            waarde = EXCLUDED.waarde, bron = EXCLUDED.bron, kwaliteit = EXCLUDED.kwaliteit,
            metadata = COALESCE(gebied_data.metadata, '{}'::jsonb) || EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP
    """,
        list(waarden.values()),
        template="(%s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
        page_size=5000,
    )
    conn.commit()
    cur.close()
    jaren = sorted({k[2] for k in waarden})
    print(
        f"   ✅ CBS Kerncijfers: {len(waarden)} waarden, {len({k[0] for k in waarden})} gebieden, "
        f"{len(doel)} indicatoren, jaren {jaren[0]}-{jaren[-1]}"
        + (f" | {verwijderd} oude rijen verwijderd" if verwijderd else "")
    )
    return len(waarden)


def main():
    parser = argparse.ArgumentParser(description="Laad CBS Kerncijfers (alle jaargangen) voor gebieden in de database")
    parser.add_argument("gebieden", nargs="*", help="gebiedcodes (standaard: alle gebieden in de database)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"\n📈 CBS Kerncijfers laden (cache: {cbs.CACHE_DIR})")
    conn = load_sample.get_db_connection()
    try:
        laad(conn, args.gebieden or None)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
