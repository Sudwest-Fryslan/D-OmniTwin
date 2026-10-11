#!/usr/bin/env python3
"""
Jaargangcontrole: indicatorwaarden tegen de geometrie-jaargang (#119).

Buurtcodes en -grenzen veranderen per jaar. Een waarde uit jaargang X op een
buurtindeling uit jaargang Y kan bij de verkeerde buurt of bij geen enkele
buurt terechtkomen. Deze controle geeft waarschuwingen, geen harde fout:

  1. buurtcodes in de waarden die niet in de geometrie voorkomen;
  2. indicatoren waarvan de meest recente jaargang meer dan MAX_AFWIJKING
     jaar van het geometriejaar afwijkt.

Gebruik:
    python init_data/scripts/jaargang_controle.py            # sample
    python init_data/scripts/jaargang_controle.py --fryslan  # Fryslân-data

Vanuit code: controleer_jaargangen(rijen, geometrie_codes, geometrie_jaar).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_DIR = ROOT / "init_data" / "sample"
FRYSLAN_DIR = ROOT / "init_data" / "fryslan"

MAX_AFWIJKING = 2  # jaar


def geometrie_jaar_sample(datapackage: Path = SAMPLE_DIR / "datapackage.json"):
    """Lees het geometriejaar van de sample uit datapackage.json (resource sample-buurten)."""
    with open(datapackage, encoding="utf-8") as f:
        pakket = json.load(f)
    for res in pakket.get("resources", []):
        if res.get("name") == "sample-buurten":
            return res.get("geometrie_jaar")
    return None


def geometrie_codes(geojson: Path, sleutel: str = "id"):
    """Alle gebiedscodes in een GeoJSON FeatureCollection."""
    with open(geojson, encoding="utf-8") as f:
        data = json.load(f)
    return {feat["properties"].get(sleutel) for feat in data.get("features", [])} - {None}


def controleer_jaargangen(rijen, codes, geometrie_jaar, max_afwijking=MAX_AFWIJKING,
                          gebied_kolom="gebied_id", naam_kolom="indicator_naam"):
    """Controleer waarden tegen de geometrie.

    rijen: iterable van dicts met gebied_kolom, naam_kolom en 'jaar'.
    Geeft (ontbrekende_codes, jaren_per_indicator, afwijkend) terug:
      ontbrekende_codes: {code: aantal regels}
      jaren_per_indicator: {indicator: set(jaren)}
      afwijkend: {indicator: meest recente jaar} als dat meer dan max_afwijking
                 jaar van geometrie_jaar afwijkt
    """
    ontbrekend = defaultdict(int)
    jaren = defaultdict(set)
    for r in rijen:
        code = (r.get(gebied_kolom) or "").strip()
        if code and code not in codes:
            ontbrekend[code] += 1
        jaar = (str(r.get("jaar") or "")).strip()
        if jaar.isdigit():
            jaren[(r.get(naam_kolom) or "").strip()].add(int(jaar))

    # Het meest recente jaar telt: dat toont de app (kaart, Kompas, rapport).
    # Oudere jaargangen van een reeks zijn bedoeld; die vangt de codecontrole.
    afwijkend = {}
    if geometrie_jaar:
        for naam, js in jaren.items():
            if abs(max(js) - int(geometrie_jaar)) > max_afwijking:
                afwijkend[naam] = max(js)
    return dict(ontbrekend), dict(jaren), afwijkend


def rapporteer(ontbrekend, jaren, afwijkend, geometrie_jaar, max_regels=10, uitvoer=print):
    """Print de waarschuwingen. Geeft het aantal waarschuwingen terug."""
    n = 0
    uitvoer(f"   ℹ️  Geometrie-jaargang: {geometrie_jaar or 'onbekend'}; "
            f"{len(jaren)} indicatoren, jaargangen {format_jaren(set().union(*jaren.values()) if jaren else set())}")
    if not geometrie_jaar:
        uitvoer("   ⚠️  Geometrie-jaargang onbekend: leg hem vast (datapackage.json of gebieden.metadata)")
        n += 1
    if ontbrekend:
        n += 1
        uitvoer(f"   ⚠️  {len(ontbrekend)} buurtcodes in de waarden bestaan niet in de geometrie "
                f"({sum(ontbrekend.values())} regels worden niet gekoppeld):")
        for code, aantal in sorted(ontbrekend.items())[:max_regels]:
            uitvoer(f"        {code} ({aantal} regels)")
        if len(ontbrekend) > max_regels:
            uitvoer(f"        … en {len(ontbrekend) - max_regels} meer")
    if afwijkend:
        n += 1
        uitvoer(f"   ⚠️  {len(afwijkend)} indicatoren: meest recente jaargang wijkt meer dan "
                f"{MAX_AFWIJKING} jaar af van geometriejaar {geometrie_jaar}:")
        for naam, jaar in sorted(afwijkend.items())[:max_regels]:
            uitvoer(f"        {naam}: {jaar}")
        if len(afwijkend) > max_regels:
            uitvoer(f"        … en {len(afwijkend) - max_regels} meer")
    return n


def format_jaren(js):
    js = sorted(js)
    if not js:
        return "-"
    if len(js) <= 4:
        return ", ".join(str(j) for j in js)
    return f"{js[0]}–{js[-1]} ({len(js)} jaargangen)"


def main():
    parser = argparse.ArgumentParser(description="Jaargangcontrole waarden vs. geometrie (#119)")
    parser.add_argument("--fryslan", action="store_true",
                        help="Controleer init_data/fryslan in plaats van de sample")
    args = parser.parse_args()

    if args.fryslan:
        codes = geometrie_codes(FRYSLAN_DIR / "buurten_fryslan.geojson", sleutel="buurtcode")
        gemeenten = {c[2:6] for c in codes}
        from download_cbs_kerncijfers import GEOMETRIE_JAAR  # één bron voor de jaargang (#159)
        geo_jaar = GEOMETRIE_JAAR
        with open(FRYSLAN_DIR / "indicatorwaarden_fryslan.csv", encoding="utf-8") as f:
            # Alleen Friese buurtcodes; de CSV bevat ook andere gemeenten, wijken en GM/NL-regels.
            rijen = [r for r in csv.DictReader(f)
                     if r["buurt_id"].startswith("BU") and r["buurt_id"][2:6] in gemeenten]
        ontbrekend, jaren, afwijkend = controleer_jaargangen(rijen, codes, geo_jaar, gebied_kolom="buurt_id")
    else:
        codes = geometrie_codes(SAMPLE_DIR / "2_brondata" / "sample_buurten.geojson")
        geo_jaar = geometrie_jaar_sample()
        with open(SAMPLE_DIR / "2_brondata" / "sample_indicatoren.csv", encoding="utf-8") as f:
            ontbrekend, jaren, afwijkend = controleer_jaargangen(csv.DictReader(f), codes, geo_jaar)

    rapporteer(ontbrekend, jaren, afwijkend, geo_jaar)
    # Waarschuwingen, geen harde fout.
    return 0


if __name__ == "__main__":
    sys.exit(main())
