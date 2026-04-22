#!/usr/bin/env python3
"""
D-OmniTwin ETL — Volledig Pipeline Runner
==========================================
Centrale orchestrator voor het volledig inrichten van een
D-OmniTwin database op een doelomgeving naar keuze.

Dit script roept de losse ETL stappen op in de juiste volgorde.
Het is volledig onafhankelijk van de FastAPI applicatie.

Gebruik:
    cd ETL/local

    # Volledige pipeline (alle stappen):
    python run_pipeline.py --alle

    # Stap voor stap:
    python run_pipeline.py --stap schema
    python run_pipeline.py --stap geometrie --provincie Fryslan
    python run_pipeline.py --stap indicatoren
    python run_pipeline.py --stap cbs --gemeenten 1900,0090
    python run_pipeline.py --stap kompas
    python run_pipeline.py --stap admin

    # Status controle (wat zit er in de DB?):
    python run_pipeline.py --status

    # Specifieke gemeente:
    python run_pipeline.py --alle --gemeenten 1900

Configuratie:
    cp ETL/local/db.ini.example ETL/local/db.ini
    → vul DATABASE wachtwoord in

Stappen:
    1. schema      — Database schema laden (tabellen, views, triggers)
    2. geometrie   — CBS buurtgrenzen ophalen via PDOK WFS
    3. indicatoren — Indicator definities seeden
    4. cbs         — CBS kerncijfers importeren via OData API
    5. kompas      — Kompas hiërarchie laden uit CSV
    6. admin       — Admin gebruiker aanmaken
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path

LOCAL_DIR = Path(__file__).resolve().parent

# Map stap-namen naar script bestanden
STAPPEN = {
    "schema":      "etl_01_init_schema.py",
    "geometrie":   "etl_02_import_geometrie.py",
    "indicatoren": "etl_03_seed_indicatoren.py",
    "cbs":         "etl_04_import_cbs.py",
    "kompas":      "etl_05_import_kompas.py",
    "admin":       "etl_06_maak_admin.py",
}

STAP_VOLGORDE = ["schema", "geometrie", "indicatoren", "cbs", "kompas", "admin"]


def run_stap(stap: str, extra_args: list = None) -> bool:
    """
    Voer een ETL stap uit als subprocess.

    Returns:
        True als succesvol, False bij fout
    """
    script = LOCAL_DIR / STAPPEN[stap]
    if not script.exists():
        print(f"❌ Script niet gevonden: {script}")
        return False

    cmd = [sys.executable, str(script)] + (extra_args or [])

    print(f"\n{'='*60}")
    print(f"🚀 Stap: {stap.upper()}")
    print(f"   Script: {script.name}")
    if extra_args:
        print(f"   Args: {' '.join(extra_args)}")
    print(f"{'='*60}")

    start = time.time()
    result = subprocess.run(cmd, cwd=str(LOCAL_DIR))
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"\n✅ Stap '{stap}' voltooid in {elapsed:.1f}s")
        return True
    else:
        print(f"\n❌ Stap '{stap}' mislukt (exit code {result.returncode}) na {elapsed:.1f}s")
        return False


def show_status():
    """Toon database status via db_connect."""
    sys.path.insert(0, str(LOCAL_DIR))
    try:
        from db_connect import test_connection
        test_connection()
    except SystemExit:
        pass  # Foutmelding al getoond door db_connect


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — ETL Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stap-volgorde (bij --alle):
  1. schema      Database schema initialiseren
  2. geometrie   CBS buurtgrenzen importeren
  3. indicatoren Indicator definities seeden
  4. cbs         CBS kerncijfers importeren
  5. kompas      Kompas hiërarchie laden
  6. admin       Admin gebruiker aanmaken

Voorbeelden:
  python run_pipeline.py --alle
  python run_pipeline.py --alle --gemeenten 1900,0090
  python run_pipeline.py --stap schema
  python run_pipeline.py --stap cbs --gemeenten 1900
  python run_pipeline.py --status
        """
    )

    parser.add_argument(
        "--alle", action="store_true",
        help="Voer alle ETL stappen uit in volgorde"
    )
    parser.add_argument(
        "--stap",
        choices=list(STAPPEN.keys()),
        help="Voer één specifieke stap uit"
    )
    parser.add_argument(
        "--gemeenten",
        help="Komma-gescheiden CBS gemeente codes (bijv. 1900,0090)"
    )
    parser.add_argument(
        "--provincie",
        help="Provincie filter voor geometrie stap (bijv. Fryslan)"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Toon database status"
    )
    parser.add_argument(
        "--vanaf",
        choices=list(STAPPEN.keys()),
        help="Start pipeline vanaf een specifieke stap (slaat eerdere stappen over)"
    )
    parser.add_argument(
        "--tot",
        choices=list(STAPPEN.keys()),
        help="Stop pipeline na een specifieke stap"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🌍 D-OmniTwin — ETL Pipeline Runner")
    print("=" * 60)
    print(f"   Scripts: {LOCAL_DIR}")
    print()

    if args.status:
        show_status()
        return

    if not args.alle and not args.stap:
        parser.print_help()
        return

    # Bouw extra argumenten op die doorgegeven worden aan de sub-scripts
    gedeelde_args = []
    if args.gemeenten:
        gedeelde_args.extend(["--gemeenten", args.gemeenten])
    if args.provincie:
        gedeelde_args.extend(["--provincie", args.provincie])

    # Bepaal welke stappen uitgevoerd worden
    if args.stap:
        te_uitvoeren = [args.stap]
    else:
        # Alle stappen, met optionele vanaf/tot afkapping
        te_uitvoeren = list(STAP_VOLGORDE)

        if args.vanaf:
            idx = STAP_VOLGORDE.index(args.vanaf)
            te_uitvoeren = STAP_VOLGORDE[idx:]

        if args.tot:
            idx = STAP_VOLGORDE.index(args.tot)
            te_uitvoeren = [s for s in te_uitvoeren if STAP_VOLGORDE.index(s) <= idx]

    print(f"📋 Geplande stappen: {' → '.join(te_uitvoeren)}")
    if gedeelde_args:
        print(f"   Gemeenten: {args.gemeenten or '(alle)'}")

    # Stap-specifieke args (niet alle sub-scripts accepteren dezelfde flags)
    STAP_ARGS = {
        "schema":      [],
        "geometrie":   gedeelde_args,
        "indicatoren": [],
        "cbs":         gedeelde_args,
        "kompas":      [],
        "admin":       [],
    }

    # Uitvoeren
    totaal_start = time.time()
    resultaten = {}

    for stap in te_uitvoeren:
        ok = run_stap(stap, STAP_ARGS.get(stap, []))
        resultaten[stap] = ok
        if not ok:
            print(f"\n⛔ Pipeline gestopt bij stap '{stap}' (fout)")
            break

    # Eindsamenvatting
    totaal_elapsed = time.time() - totaal_start
    print(f"\n{'='*60}")
    print(f"📊 Pipeline samenvatting ({totaal_elapsed:.0f}s totaal):")
    print()
    for stap in te_uitvoeren:
        if stap in resultaten:
            symbool = "✅" if resultaten[stap] else "❌"
        else:
            symbool = "⏭️ "
        print(f"  {symbool}  {stap}")

    alle_ok = all(resultaten.values())
    print()
    if alle_ok:
        print("🎉 Pipeline succesvol voltooid!")
        print()
        print("   Volgende stap: start de applicatie")
        print("   cd <project_root>")
        print("   python run_dev.py")
    else:
        print("⚠️  Pipeline voltooid met fouten. Controleer de output hierboven.")
    print("=" * 60)


if __name__ == "__main__":
    main()
