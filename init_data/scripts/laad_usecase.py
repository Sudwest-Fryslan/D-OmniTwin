#!/usr/bin/env python3
"""
D-OmniTwin — use-casepakket laden
=================================
Alle data hoort bij een use case. Een use case (usecases/<naam>/) laadt:

1. data: de gebieden uit usecase.json (geometrie en alle indicatorwaarden),
   gekozen uit de bronbibliotheek init_data/sample/2_brondata
2. inrichting: richting van de indicatoren (hoger/lager is beter)
3. afgeleide indicatoren: percentages berekend uit bestaande brondata
   (bijvoorbeeld 65+ jaar ÷ Inwoners), voor alle gebieden in de database,
   per jaar met teller en noemer uit hetzelfde jaar
4. extra brondata: usecases/<naam>/data/waarden.csv, zelfde formaat als
   init_data/sample/2_brondata/sample_indicatoren.csv (optioneel)

Een demopakket met `datasets` (de data komt via de laad-API uit open bronnen, #236) krijgt
hier alleen zijn inrichting: `--inrichting <naam>` zet de richting (en eenheid) van de
indicatoren en maakt de afgeleide indicatoren. De uitvoerder (`python -m omnitwin.usecases
installeer`) roept dat aan na de laad-API.

Vereist: het product zonder data, geladen met
    python init_data/scripts/load_sample.py --stap definities

Idempotent: opnieuw laden overschrijft dezelfde rijen. Pakketten zijn te
combineren; --alle laadt ze allemaal.

Volgorde en afhankelijkheden (`afhankelijk_van` in usecase.json) komen uit de
use-case-uitvoerder (omnitwin.usecases): eerst de afhankelijkheden, elke use case
één keer; een use case met status 'ontwerp' en wat er (niet-optioneel) van afhangt,
wordt overgeslagen. Use cases met `datasets` laden via de laad-API
(python -m omnitwin.usecases), niet via dit script.

Gebruik:
    python init_data/scripts/laad_usecase.py hittestress [sociale-cohesie ...]
    python init_data/scripts/laad_usecase.py --alle
    python init_data/scripts/laad_usecase.py --inrichting hittestress [...]
    python init_data/scripts/laad_usecase.py --lijst | --boom <naam> | --index
"""

import argparse
import csv
import json
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import load_sample  # noqa: E402  (databaseverbinding en CSV-import hergebruiken)

from omnitwin import usecases as uitvoerder  # noqa: E402  (volgorde, afhankelijkheden, status)

ROOT = Path(__file__).resolve().parent.parent.parent
USECASES_DIR = ROOT / "usecases"
# Vaste namespace: dezelfde naam geeft altijd dezelfde uuid
NAMESPACE = uuid.UUID("6f1d3c2a-0b7e-4c8e-9a51-d0a1b2c3e4f5")

# richting = indicatoren.polariteit (#120): hoger_is_beter | lager_is_beter | neutraal.
# Neutraal: geen oordeel (de chat zegt dan niet 'beter' of 'slechter', #149). De oude
# kolommen score_type en interpretatie_logica volgen via de trigger uit V046.
RICHTING = ("hoger_is_beter", "lager_is_beter", "neutraal")


def pakketten(namen, alle, map_=USECASES_DIR):
    """Te laden demopakketten in volgorde (afhankelijkheden eerst). Overgeslagen: status 'ontwerp'
    (en wat ervan afhangt) en use cases met `datasets` (die laden via de laad-API)."""
    ucs = uitvoerder.lees_usecases(map_)
    try:
        orde, overgeslagen = uitvoerder.plan(namen, ucs, alle)
    except uitvoerder.UseCaseFout as e:
        sys.exit(f"❌ {e}. Beschikbaar: {sorted(ucs)}")
    for naam, reden in overgeslagen.items():
        print(f"⏭️  {naam}: overgeslagen ({reden})")
    for naam in orde:
        if "datasets" in ucs[naam]:
            print(f"⏭️  {naam}: laadt via de laad-API (python -m omnitwin.usecases), niet via dit script")
    return [n for n in orde if "datasets" not in ucs[n]]


def zet_richting(cur, indicatoren):
    for ind in indicatoren:
        if ind["richting"] not in RICHTING:
            continue  # onbekende richting: test_usecase_pakketten vangt dit af
        cur.execute(
            "UPDATE indicatoren SET polariteit = %s, updated_at = CURRENT_TIMESTAMP WHERE naam = %s",
            (ind["richting"], ind["naam"]),
        )
        if cur.rowcount == 0:
            print(f"   ⚠️ indicator niet gevonden: {ind['naam']}")
        if ind.get("eenheid"):
            # Eenheid aanvullen waar de bron die niet meegaf (chat: '246 m', '48,3%', #149)
            cur.execute(
                "UPDATE indicatoren SET eenheid = %s, updated_at = CURRENT_TIMESTAMP "
                "WHERE naam = %s AND COALESCE(eenheid, '') = ''",
                (ind["eenheid"], ind["naam"]),
            )


def maak_afgeleid(cur, afg, bron_uc):
    ind_uuid = str(uuid.uuid5(NAMESPACE, afg["naam"]))
    richting = afg.get("richting") if afg.get("richting") in RICHTING else "hoger_is_beter"
    code = f"IND_{''.join(c if c.isalnum() else '_' for c in afg['naam'].upper())[:30]}_{ind_uuid[:8]}"
    cur.execute(
        """
        INSERT INTO indicatoren (uuid, naam, code, eenheid, categorie, polariteit, bron, status, is_actief)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'O', TRUE)
        ON CONFLICT (uuid) DO UPDATE SET naam = EXCLUDED.naam, eenheid = EXCLUDED.eenheid,
            polariteit = EXCLUDED.polariteit, bron = EXCLUDED.bron, updated_at = CURRENT_TIMESTAMP
        """,
        (
            ind_uuid,
            afg["naam"],
            code,
            afg.get("eenheid", "%"),
            afg.get("categorie"),
            richting,
            f"Afgeleid: {afg['teller']} ÷ {afg['noemer']} (use case {bron_uc})",
        ),
    )
    # Waarde per gebied en jaar: teller en noemer uit hetzelfde jaar en scenario (#159).
    # Zonder noemer in dat jaar geen waarde; jaren mengen geeft schijnbare trends.
    cur.execute(
        """
        INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, kwaliteit, scenario_id)
        SELECT t.gebied_id, %s, ROUND((t.waarde / n.waarde * %s)::numeric, 1), t.jaar,
               CASE WHEN t.bron IS NOT DISTINCT FROM n.bron THEN 'Afgeleid uit ' || COALESCE(t.bron, '?')
                    ELSE 'Afgeleid uit ' || COALESCE(t.bron, '?') || ' en ' || COALESCE(n.bron, '?') END,
               NULL, t.scenario_id
        FROM gebied_data t
        JOIN indicatoren it ON it.uuid = t.indicator_uuid AND it.naam = %s
        JOIN gebied_data n ON n.gebied_id = t.gebied_id AND n.jaar = t.jaar
            AND n.scenario_id IS NOT DISTINCT FROM t.scenario_id AND n.waarde > 0
        JOIN indicatoren inn ON inn.uuid = n.indicator_uuid AND inn.naam = %s
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
    """Pad naar de extra brondata van een use case: de gecommitte data/waarden.csv (niet-downloadbare
    data). Downloadbare data komt via een dataset met een bronadapter (laad-API), niet hier."""
    return USECASES_DIR / naam / "data" / "waarden.csv"


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

    inrichting(conn, naam, uc)


def inrichting(conn, naam, uc=None):
    """Richting en eenheid van de indicatoren, en de afgeleide indicatoren. Geen data."""
    uc = uc or json.loads((USECASES_DIR / naam / "usecase.json").read_text(encoding="utf-8"))
    cur = conn.cursor()
    zet_richting(cur, (uc.get("data") or {}).get("indicatoren", []))
    for afg in (uc.get("data") or {}).get("afgeleid", []):
        maak_afgeleid(cur, afg, naam)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Laad use-casepakketten (usecases/<naam>/)")
    parser.add_argument("namen", nargs="*", help="naam van de map onder usecases/")
    parser.add_argument("--alle", action="store_true", help="alle use cases laden")
    parser.add_argument(
        "--inrichting",
        action="store_true",
        help="alleen de inrichting (richting, eenheid, afgeleide indicatoren), geen data",
    )
    parser.add_argument("--lijst", action="store_true", help="use cases tonen (zie python -m omnitwin.usecases lijst)")
    parser.add_argument("--boom", metavar="NAAM", help="afhankelijkheden als boom")
    parser.add_argument("--index", action="store_true", help="index in usecases/README.md bijwerken")
    args = parser.parse_args()
    if args.lijst or args.boom or args.index:
        sys.exit(uitvoerder.main(["lijst"] if args.lijst else ["boom", args.boom] if args.boom else ["index"]))
    if not args.namen and not args.alle:
        parser.error("geef een of meer namen, of --alle")

    conn = load_sample.get_db_connection()
    try:
        if args.inrichting:
            for naam in args.namen:
                print(f"\n🧭 {naam}: inrichting")
                inrichting(conn, naam)
        else:
            for naam in pakketten(args.namen, args.alle):
                laad(conn, naam)
    finally:
        conn.close()
    print("\n✅ Use cases geladen.")


if __name__ == "__main__":
    main()
