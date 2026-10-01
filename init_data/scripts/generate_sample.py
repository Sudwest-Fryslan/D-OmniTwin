#!/usr/bin/env python3
"""
D-OmniTwin — Generate Sample Dataset
====================================
Exporteert een compacte, zelfstandige sample dataset uit de actieve database
voor Súdwest-Fryslân (12 buurten).

Genereert:
  1. init_data/sample/1_stuurdata/stuurdata_seed.sql
  2. init_data/sample/2_brondata/sample_buurten.geojson
  3. init_data/sample/2_brondata/sample_indicatoren.csv

Gebruik:
  ./.venv/bin/python init_data/scripts/generate_sample.py
"""

import csv
import json
import os
import sys
from pathlib import Path

# Zorg voor .env laden
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

import psycopg2

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_DIR = ROOT / "init_data" / "sample"
STUURDATA_DIR = SAMPLE_DIR / "1_stuurdata"
BRONDATA_DIR = SAMPLE_DIR / "2_brondata"

STUURDATA_DIR.mkdir(parents=True, exist_ok=True)
BRONDATA_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_BUURTEN = [
    "BU19000004",  # Bolsward-Noordoost
    "BU19000001",  # Bolsward-Noord
    "BU19000002",  # Bolsward-Zuidoost (in de sample: demodata, zie README)
    "BU19000108",  # Bomenbuurt
    "BU19000200",  # Workum
    "BU19000202",  # Hindeloopen
    "BU19000300",  # Koudum
    "BU19000301",  # Heidenschap
    "BU19000400",  # Hemelum
    "BU19000401",  # Warns
    "BU19001200",  # Woudsend
    "BU19001300",  # Witmarsum
    "BU19002017",  # Boazum
]


def get_conn():
    host = os.environ.get("DATABASE_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    port = int(os.environ.get("DATABASE_PORT", 5433))
    dbname = os.environ.get("DATABASE_NAME", "omnitwin_db")
    user = os.environ.get("DATABASE_USER", "omnitwin_user")
    password = os.environ.get("DATABASE_PASSWORD", "")
    return psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=5
    )


def format_sql_val(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list)):
        s = json.dumps(val, ensure_ascii=False)
        return "'" + s.replace("'", "''") + "'::jsonb"
    s = str(val)
    if "\n" in s or len(s) > 100:
        return "$$" + s + "$$"
    return "'" + s.replace("'", "''") + "'"


def export_stuurdata(conn):
    print("📦 Exporteren stuurdata (stuurdata_seed.sql)...")
    cur = conn.cursor()
    target_file = STUURDATA_DIR / "stuurdata_seed.sql"

    sections = [
        (
            "1. Gebiedstypes",
            "gebiedstypes",
            "id",
            "id, naam, code, beschrijving, bron, niveau, created_at, updated_at",
            "SELECT id, naam, code, beschrijving, bron, niveau, created_at, updated_at FROM gebiedstypes ORDER BY naam",
        ),
        (
            "2. Gemeenten (alle 18 Friese gemeenten, CBS-indeling 2024; nodig voor seed_fryslan.py)",
            "gemeenten",
            "code",
            "code, naam, provincie, is_eiland, created_at, updated_at",
            "SELECT code, naam, provincie, is_eiland, created_at, updated_at FROM gemeenten "
            "WHERE code IN ('0059','0060','0072','0074','0080','0085','0086','0088','0090',"
            "'0093','0096','0098','0737','1891','1900','1940','1949','1970') ORDER BY code",
        ),
        (
            "3. Kompas Configuraties",
            "kompas_configuraties",
            "id",
            "id, naam, beschrijving, is_standaard, is_actief, icoon, versie",
            "SELECT id, naam, beschrijving, is_standaard, is_actief, icoon, versie FROM kompas_configuraties WHERE id IN (1, 2) ORDER BY id",
        ),
        (
            "4. Kleurenschema's (Color Schemas)",
            "color_schemas",
            "id",
            "id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur",
            "SELECT id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur FROM color_schemas ORDER BY id",
        ),
        (
            "5. Visualisatie Profielen",
            "visualisatie_profielen",
            "id",
            "id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at",
            "SELECT id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at FROM visualisatie_profielen ORDER BY id",
        ),
        (
            "6. Chat Scenario's",
            "chat_scenarios",
            "id",
            "id, rol_code, rol_naam, beschrijving, narrative, acties, trigger_keywords, is_actief, volgorde",
            "SELECT id, rol_code, rol_naam, beschrijving, narrative, acties, trigger_keywords, is_actief, volgorde FROM chat_scenarios WHERE id IN (1, 2) ORDER BY id",
        ),
        (
            "7. LLM Configuratie",
            "llm_config",
            "id",
            "id, api_url, model_name, aangemaakt_op, bijgewerkt_op",
            "SELECT id, api_url, model_name, aangemaakt_op, bijgewerkt_op FROM llm_config WHERE id = 1",
        ),
        (
            "8. Log Configuratie",
            "log_config",
            "category",
            "category, level, enabled, updated_at, updated_by",
            "SELECT category, level, enabled, updated_at, updated_by FROM log_config ORDER BY category",
        ),
        (
            "9. Systeem Prompts",
            "system_prompts",
            "id",
            "id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd",
            "SELECT id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd FROM system_prompts ORDER BY naam",
        ),
        (
            "10. Externe Kaartlagen (BAG Woonplaatsen)",
            "externe_kaartlagen",
            "id",
            "id, naam, beschrijving, laag_type, bron_type, url, typename, srsname, versie, filter_type, filter_waarde, koppel_veld, kleur_lijn, kleur_fill, opacity, actief, volgorde, created_at, updated_at",
            "SELECT id, naam, beschrijving, laag_type, bron_type, url, typename, srsname, versie, filter_type, filter_waarde, koppel_veld, kleur_lijn, kleur_fill, opacity, actief, volgorde, created_at, updated_at FROM externe_kaartlagen WHERE id = 1",
        ),
    ]

    lines = [
        "--",
        "-- D-OmniTwin — Stuurdata Seed (Sample Dataset)",
        "-- Bevat: basisconfiguratie, scenario's, prompts, profielen en instellingen",
        "-- Idempotent: uitgevoerd met INSERT ... ON CONFLICT DO NOTHING",
        "--",
        "",
    ]

    total_rows = 0
    for title, table, pk, cols, q in sections:
        lines.append("-- -------------------------------------------------------------")
        lines.append(f"-- {title}")
        lines.append("-- -------------------------------------------------------------")
        cur.execute(q)
        rows = cur.fetchall()
        total_rows += len(rows)
        for row in rows:
            formatted_vals = [format_sql_val(v) for v in row]
            vals_str = ", ".join(formatted_vals)
            lines.append(
                f"INSERT INTO public.{table} ({cols})\nVALUES ({vals_str})\nON CONFLICT ({pk}) DO NOTHING;\n"
            )

    lines.append("-- -------------------------------------------------------------")
    lines.append("-- Sequenties bijwerken")
    lines.append("-- -------------------------------------------------------------")
    lines.append("SELECT setval('public.chat_scenarios_id_seq', COALESCE((SELECT MAX(id) FROM public.chat_scenarios), 1), true);")
    lines.append("SELECT setval('public.color_schemas_id_seq', COALESCE((SELECT MAX(id) FROM public.color_schemas), 1), true);")
    lines.append("SELECT setval('public.externe_kaartlagen_id_seq', COALESCE((SELECT MAX(id) FROM public.externe_kaartlagen), 1), true);")
    lines.append("SELECT setval('public.llm_config_id_seq', COALESCE((SELECT MAX(id) FROM public.llm_config), 1), true);")
    lines.append("SELECT setval('public.visualisatie_profielen_id_seq', COALESCE((SELECT MAX(id) FROM public.visualisatie_profielen), 1), true);")
    lines.append("SELECT setval('public.kompas_configuraties_id_seq', COALESCE((SELECT MAX(id) FROM public.kompas_configuraties), 1), true);")
    lines.append("")

    with open(target_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    cur.close()
    print(f"   ✅ {total_rows} stuurdata records weggeschreven naar {target_file.name}")


def export_buurten(conn):
    print("🗺️  Exporteren 12 SWF-buurten (sample_buurten.geojson)...")
    cur = conn.cursor()
    target_file = BRONDATA_DIR / "sample_buurten.geojson"

    q = """
    SELECT 
        id, naam, gemeente_code, gebiedstype_id, provincienaam,
        ST_AsGeoJSON(ST_Transform(geom, 4326)) as geojson_geom
    FROM gebieden
    WHERE id = ANY(%s) AND actief = true
    ORDER BY id;
    """
    cur.execute(q, (SAMPLE_BUURTEN,))
    rows = cur.fetchall()

    features = []
    for r in rows:
        b_id, naam, gm_code, type_id, prov, geom_str = r
        geom = json.loads(geom_str) if geom_str else None
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "id": b_id,
                "naam": naam,
                "gemeente_code": gm_code,
                "gebiedstype_id": str(type_id) if type_id else None,
                "provincienaam": prov or "Fryslân",
            }
        })

    geojson_data = {
        "type": "FeatureCollection",
        "name": "sample_buurten_swf",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": features
    }

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)

    cur.close()
    print(f"   ✅ {len(features)} buurten geëxporteerd naar {target_file.name}")


def export_indicatoren(conn):
    print("📊 Exporteren sample indicatormetingen (sample_indicatoren.csv)...")
    cur = conn.cursor()
    target_file = BRONDATA_DIR / "sample_indicatoren.csv"

    q = """
    SELECT 
        gd.gebied_id,
        gd.indicator_uuid::text,
        i.naam as indicator_naam,
        gd.waarde,
        gd.jaar,
        gd.bron,
        gd.kwaliteit,
        i.eenheid,
        i.categorie,
        i.interpretatie_logica,
        gd.scenario_id
    FROM (
        SELECT DISTINCT ON (gebied_id, indicator_uuid)
            gebied_id, indicator_uuid, waarde, jaar, bron, kwaliteit, scenario_id
        FROM gebied_data
        WHERE gebied_id = ANY(%s)
        ORDER BY gebied_id, indicator_uuid, jaar DESC
    ) gd
    JOIN indicatoren i ON gd.indicator_uuid = i.uuid
    ORDER BY gd.gebied_id, i.naam;
    """
    cur.execute(q, (SAMPLE_BUURTEN,))
    rows = cur.fetchall()

    fieldnames = [
        "gebied_id",
        "indicator_uuid",
        "indicator_naam",
        "waarde",
        "jaar",
        "bron",
        "kwaliteit",
        "eenheid",
        "categorie",
        "interpretatie_logica",
        "scenario_id"
    ]

    with open(target_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for r in rows:
            writer.writerow(r)

    cur.close()
    print(f"   ✅ {len(rows)} metingen geëxporteerd naar {target_file.name}")


def main():
    print("=" * 60)
    print("🚀 Genereren Sample Dataset D-OmniTwin")
    print("=" * 60)
    try:
        conn = get_conn()
        export_stuurdata(conn)
        export_buurten(conn)
        export_indicatoren(conn)
        conn.close()
        print("=" * 60)
        print("🎉 Sample dataset export succesvol voltooid!")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Fout tijdens genereren: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
