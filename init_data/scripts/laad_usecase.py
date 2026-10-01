#!/usr/bin/env python3
"""
D-OmniTwin — use-casepakket laden
=================================
Alle data hoort bij een use case. Een use case (usecases/<naam>/) laadt:

1. data: de gebieden uit usecase.json (geometrie en alle indicatorwaarden),
   gekozen uit de bronbibliotheek init_data/sample/2_brondata
2. inrichting: richting van de indicatoren (hoger/lager is beter)
3. afgeleide indicatoren: percentages berekend uit bestaande brondata
   (bijvoorbeeld 65+ jaar ÷ Inwoners), voor alle gebieden in de database
4. extra brondata: usecases/<naam>/data/waarden.csv, zelfde formaat als
   init_data/sample/2_brondata/sample_indicatoren.csv (optioneel)

Vereist: het product zonder data, geladen met
    python init_data/scripts/load_sample.py --stap definities

Idempotent: opnieuw laden overschrijft dezelfde rijen. Pakketten zijn te
combineren; --alle laadt ze allemaal.

Gebruik:
    python init_data/scripts/laad_usecase.py hittestress [sociale-cohesie ...]
    python init_data/scripts/laad_usecase.py --alle
"""

import argparse
import csv
import importlib.util
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import load_sample  # noqa: E402  (databaseverbinding en CSV-import hergebruiken)

ROOT = Path(__file__).resolve().parent.parent.parent
USECASES_DIR = ROOT / "usecases"
# Vaste namespace: dezelfde naam geeft altijd dezelfde uuid
NAMESPACE = uuid.UUID("6f1d3c2a-0b7e-4c8e-9a51-d0a1b2c3e4f5")

RICHTING = {
    # richting -> (interpretatie_logica, score_type); zie report_service en color_scale_service
    "hoger_is_beter": ("pos_is_pos", "+/+"),
    "lager_is_beter": ("-/+", "+/-"),
}


def pakketten(namen, alle):
    beschikbaar = sorted(p.parent.name for p in USECASES_DIR.glob("*/usecase.json"))
    if alle:
        return beschikbaar
    onbekend = [n for n in namen if n not in beschikbaar]
    if onbekend:
        sys.exit(f"❌ Onbekende use case(s): {onbekend}. Beschikbaar: {beschikbaar}")
    return namen


def zet_richting(cur, indicatoren):
    for ind in indicatoren:
        if ind["richting"] not in RICHTING:
            continue  # neutraal: niet aanpassen
        logica, score_type = RICHTING[ind["richting"]]
        cur.execute(
            "UPDATE indicatoren SET interpretatie_logica = %s, score_type = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE naam = %s",
            (logica, score_type, ind["naam"]),
        )
        if cur.rowcount == 0:
            print(f"   ⚠️ indicator niet gevonden: {ind['naam']}")


def maak_afgeleid(cur, afg, bron_uc):
    ind_uuid = str(uuid.uuid5(NAMESPACE, afg["naam"]))
    logica, score_type = RICHTING.get(afg.get("richting"), ("pos_is_pos", "+/+"))
    code = f"IND_{''.join(c if c.isalnum() else '_' for c in afg['naam'].upper())[:30]}_{ind_uuid[:8]}"
    cur.execute(
        """
        INSERT INTO indicatoren (uuid, naam, code, eenheid, categorie, interpretatie_logica, bron, score_type, status, is_actief)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'O', TRUE)
        ON CONFLICT (uuid) DO UPDATE SET naam = EXCLUDED.naam, eenheid = EXCLUDED.eenheid,
            interpretatie_logica = EXCLUDED.interpretatie_logica, score_type = EXCLUDED.score_type,
            bron = EXCLUDED.bron, updated_at = CURRENT_TIMESTAMP
        """,
        (ind_uuid, afg["naam"], code, afg.get("eenheid", "%"), afg.get("categorie"), logica,
         f"Afgeleid: {afg['teller']} ÷ {afg['noemer']} (use case {bron_uc})", score_type),
    )
    # Waarde per gebied en jaar van de teller. De noemer komt uit dezelfde of de
    # dichtstbijzijnde jaargang (bronnen hebben verschillende jaargangen, #119);
    # bij een afwijkend jaar staat dat in de bron.
    cur.execute(
        """
        INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, kwaliteit, scenario_id)
        SELECT t.gebied_id, %s, ROUND((t.waarde / n.waarde * %s)::numeric, 1), t.jaar,
               'Afgeleid uit ' || COALESCE(t.bron, '?') || ' en ' || COALESCE(n.bron, '?')
                   || CASE WHEN n.jaar <> t.jaar THEN ' (noemer ' || n.jaar || ')' ELSE '' END,
               NULL, t.scenario_id
        FROM gebied_data t
        JOIN indicatoren it ON it.uuid = t.indicator_uuid AND it.naam = %s
        CROSS JOIN LATERAL (
            SELECT d.waarde, d.jaar, d.bron FROM gebied_data d
            JOIN indicatoren inn ON inn.uuid = d.indicator_uuid AND inn.naam = %s
            WHERE d.gebied_id = t.gebied_id AND d.scenario_id IS NOT DISTINCT FROM t.scenario_id AND d.waarde > 0
            ORDER BY abs(d.jaar - t.jaar), d.jaar DESC LIMIT 1
        ) n
        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
            waarde = EXCLUDED.waarde, bron = EXCLUDED.bron, updated_at = CURRENT_TIMESTAMP
        """,
        (ind_uuid, afg.get("factor", 100), afg["teller"], afg["noemer"]),
    )
    print(f"   ➕ {afg['naam']}: {cur.rowcount} waarden")


def laad_gebieden(conn, gebied_ids):
    """Geometrie en indicatorwaarden van deze gebieden uit de bronbibliotheek laden."""
    bron_geojson, bron_csv = load_sample.BUURTEN_GEOJSON, load_sample.INDICATOREN_CSV
    with tempfile.TemporaryDirectory() as tmp:
        geo = json.loads(bron_geojson.read_text(encoding="utf-8"))
        geo["features"] = [f for f in geo["features"] if f["properties"].get("id") in gebied_ids]
        ontbreekt = set(gebied_ids) - {f["properties"]["id"] for f in geo["features"]}
        if ontbreekt:
            sys.exit(f"❌ Gebieden niet in de bronbibliotheek: {sorted(ontbreekt)}")
        geo_pad = Path(tmp) / "buurten.geojson"
        geo_pad.write_text(json.dumps(geo), encoding="utf-8")

        csv_pad = Path(tmp) / "waarden.csv"
        with open(bron_csv, encoding="utf-8") as fin, open(csv_pad, "w", encoding="utf-8", newline="") as fout:
            lezer = csv.DictReader(fin)
            schrijver = csv.DictWriter(fout, fieldnames=lezer.fieldnames)
            schrijver.writeheader()
            schrijver.writerows(r for r in lezer if r["gebied_id"] in gebied_ids)

        # load_sample leest de paden bij aanroep; tijdelijk omzetten naar de selectie
        load_sample.BUURTEN_GEOJSON, load_sample.INDICATOREN_CSV = geo_pad, csv_pad
        try:
            load_sample.import_buurten(conn)
            load_sample.import_waarden(conn)
        finally:
            load_sample.BUURTEN_GEOJSON, load_sample.INDICATOREN_CSV = bron_geojson, bron_csv


def extra_brondata(naam, uc):
    """Pad naar de extra brondata van een use case: de cache van zijn downloadscript
    (extra_data.script), of de gecommitte data/waarden.csv. Downloadfout: waarschuwing, None."""
    script = (uc["data"].get("extra_data") or {}).get("script")
    if not script:
        return USECASES_DIR / naam / "data" / "waarden.csv"
    cache = Path(os.environ.get("DATA_CACHE", ROOT / "data-cache")) / "usecases" / naam / "waarden.csv"
    if cache.exists():
        print(f"   💾 extra brondata uit cache: {cache}")
        return cache
    print(f"   🌐 extra brondata downloaden ({script})")
    try:
        spec = importlib.util.spec_from_file_location(f"maak_data_{naam.replace('-', '_')}", USECASES_DIR / naam / script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.main(cache)
    except Exception as e:  # geen netwerk, bron onbereikbaar, cache niet schrijfbaar
        print(f"   ⚠️  extra brondata van {naam} niet opgehaald ({type(e).__name__}: {e}); de use case is onvolledig")
        return None


def laad(conn, naam):
    uc = json.loads((USECASES_DIR / naam / "usecase.json").read_text(encoding="utf-8"))
    print(f"\n📦 {uc['id']} {naam}: {uc['titel']}")
    laad_gebieden(conn, list(uc["data"]["gebieden"]))

    # Extra brondata eerst: dan bestaan de nieuwe indicatoren als de richting wordt gezet.
    # Downloadbare data (extra_data.script) wordt bij het laden opgehaald en gecachet, niet uit git;
    # niet-downloadbare data staat in usecases/<naam>/data/waarden.csv.
    extra = extra_brondata(naam, uc)
    if extra and extra.exists():
        bron_csv = load_sample.INDICATOREN_CSV
        load_sample.INDICATOREN_CSV = extra  # zelfde formaat als de sample
        try:
            load_sample.import_indicatoren(conn)
            load_sample.import_waarden(conn)
        finally:
            load_sample.INDICATOREN_CSV = bron_csv

    cur = conn.cursor()
    zet_richting(cur, uc["data"]["indicatoren"])
    for afg in uc["data"].get("afgeleid", []):
        maak_afgeleid(cur, afg, naam)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Laad use-casepakketten (usecases/<naam>/)")
    parser.add_argument("namen", nargs="*", help="naam van de map onder usecases/")
    parser.add_argument("--alle", action="store_true", help="alle use cases laden")
    args = parser.parse_args()
    if not args.namen and not args.alle:
        parser.error("geef een of meer namen, of --alle")

    conn = load_sample.get_db_connection()
    try:
        for naam in pakketten(args.namen, args.alle):
            laad(conn, naam)
    finally:
        conn.close()
    print("\n✅ Use cases geladen.")


if __name__ == "__main__":
    main()
