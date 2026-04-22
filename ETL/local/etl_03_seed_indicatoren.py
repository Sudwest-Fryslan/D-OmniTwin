#!/usr/bin/env python3
"""
D-OmniTwin ETL — Stap 3: Indicatoren Seeden
=============================================
Laadt de indicator-definitie JSON (naam, code, eenheid, score_type)
naar de indicatoren tabel.

Gebruik:
    cd ETL/local
    python etl_03_seed_indicatoren.py

    # Alleen tellen wat er al is:
    python etl_03_seed_indicatoren.py --check

    # Alternatief seed bestand:
    python etl_03_seed_indicatoren.py --bestand /pad/naar/mijn_indicatoren.json

    # Droog draaien (wat zou er gebeuren, zonder DB wijzigingen):
    python etl_03_seed_indicatoren.py --dry-run

Configuratie:
    Zie ETL/local/db.ini.example → kopieer naar ETL/local/db.ini

Seed bestand formaat (JSON array):
    [
      {
        "naam":       "Koopwoningen",
        "code":       "IND_KOOPWONINGEN",
        "eenheid":    "%",
        "score_type": "+/+",
        "bron":       "CBS Kerncijfers wijken en buurten",
        "omschrijving": "Percentage koopwoningen in de buurt"
      },
      ...
    ]
"""

import sys
import json
import argparse
from pathlib import Path

LOCAL_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT = LOCAL_DIR.parent.parent
DEFAULT_SEED = PROJECT_ROOT / "init_data" / "indicatoren" / "indicatoren_seed.json"

sys.path.insert(0, str(LOCAL_DIR))
from db_connect import get_connection

# Toegestane score_type waarden (moet overeenkomen met DB constraint)
VALID_SCORE_TYPES = {"+/+", "+/-", "-/+", "-/-", "-=-"}


def load_seed(pad: Path) -> list:
    """Laad en valideer de indicator seed JSON."""
    if not pad.exists():
        print(f"❌ Seed bestand niet gevonden: {pad}")
        sys.exit(1)

    with open(pad, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f"❌ Seed bestand moet een JSON array zijn, niet {type(data).__name__}")
        sys.exit(1)

    print(f"  📂 {len(data)} indicatoren geladen uit: {pad.name}")
    return data


def import_indicatoren(conn, indicatoren: list, dry_run: bool = False) -> dict:
    """
    Importeer indicatoren naar de database.

    Returns:
        Dict met statistieken
    """
    stats = {"ingevoegd": 0, "bijgewerkt": 0, "overgeslagen": 0, "fouten": 0, "fouten_detail": []}
    cur = conn.cursor()

    for ind in indicatoren:
        naam = (ind.get("naam") or "").strip()
        if not naam:
            stats["overgeslagen"] += 1
            continue

        # Code normaliseren of genereren
        code = (ind.get("code") or "").strip()
        if not code:
            code = "IND_" + naam.upper()[:40].replace(" ", "_").replace("/", "_").replace(",", "").replace("-", "_")

        # Score type: haal op, fallback op heuristiek
        score_type = ind.get("score_type", "").strip()
        if score_type not in VALID_SCORE_TYPES:
            naam_lower = naam.lower()
            if any(kw in naam_lower for kw in ["afstand", "overlast", "criminaliteit",
                                                 "diefstal", "inbraak", "eenzaam",
                                                 "werkloos", "moeite"]):
                score_type = "+/-"
            else:
                score_type = "+/+"

        eenheid     = (ind.get("eenheid") or "").strip()
        bron        = (ind.get("bron") or "").strip()
        omschrijving = (ind.get("omschrijving") or "").strip()

        # Bouw omschrijving uit hiërarchie als leeg
        if not omschrijving:
            delen = [ind.get("titel", ""), ind.get("thema", ""), ind.get("onderdeel", "")]
            delen = [d for d in delen if d]
            if delen:
                omschrijving = " → ".join(delen)

        if dry_run:
            cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
            exists = cur.fetchone()
            if exists:
                print(f"  🔄 Zou bijwerken: {naam} ({code})")
                stats["bijgewerkt"] += 1
            else:
                print(f"  ✅ Zou aanmaken:  {naam} ({code})")
                stats["ingevoegd"] += 1
            continue

        try:
            cur.execute("SAVEPOINT sp_ind")
            cur.execute("""
                INSERT INTO indicatoren
                    (uuid, naam, code, eenheid, omschrijving, bron, score_type, status)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, 'O')
                ON CONFLICT (code) DO UPDATE SET
                    naam         = EXCLUDED.naam,
                    eenheid      = COALESCE(NULLIF(EXCLUDED.eenheid, ''), indicatoren.eenheid),
                    omschrijving = COALESCE(NULLIF(EXCLUDED.omschrijving, ''), indicatoren.omschrijving),
                    bron         = COALESCE(NULLIF(EXCLUDED.bron, ''), indicatoren.bron),
                    score_type   = EXCLUDED.score_type,
                    updated_at   = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS ingevoegd
            """, (naam, code, eenheid, omschrijving, bron, score_type))

            row = cur.fetchone()
            cur.execute("RELEASE SAVEPOINT sp_ind")

            if row and row[0]:
                stats["ingevoegd"] += 1
            else:
                stats["bijgewerkt"] += 1

        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_ind")
            stats["fouten"] += 1
            detail = f"{naam} ({code}): {e}"
            stats["fouten_detail"].append(detail)
            if stats["fouten"] <= 5:
                print(f"  ⚠️  Fout: {detail}")

    if not dry_run:
        conn.commit()

    cur.close()
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Indicatoren seeden",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python etl_03_seed_indicatoren.py
  python etl_03_seed_indicatoren.py --check
  python etl_03_seed_indicatoren.py --dry-run
  python etl_03_seed_indicatoren.py --bestand /data/mijn_indicatoren.json
        """
    )
    parser.add_argument(
        "--bestand",
        help=f"Pad naar indicator seed JSON (standaard: {DEFAULT_SEED.name})"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Alleen tellen wat er in de DB zit"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simuleer import zonder DB wijzigingen"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("📊 D-OmniTwin — Stap 3: Indicatoren Seeden")
    print("=" * 60)

    conn = get_connection()

    if args.check:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM indicatoren")
        print(f"\n📊 Indicatoren in database: {cur.fetchone()[0]}")
        cur.execute("SELECT score_type, COUNT(*) FROM indicatoren GROUP BY score_type ORDER BY COUNT(*) DESC")
        print("\n   Verdeling score_type:")
        for row in cur.fetchall():
            print(f"   {row[0]:<6}  {row[1]} indicatoren")
        cur.close()
        conn.close()
        return

    # Bepaal seed bestand
    seed_pad = Path(args.bestand) if args.bestand else DEFAULT_SEED

    print(f"\n📂 Seed bestand:")
    indicatoren = load_seed(seed_pad)

    print(f"\n{'🔍 DRY RUN — geen DB wijzigingen' if args.dry_run else '💾 Importeren naar database'}:")
    stats = import_indicatoren(conn, indicatoren, dry_run=args.dry_run)

    print(f"\n📊 Resultaat:")
    print(f"  ✅ Nieuw ingevoegd:  {stats['ingevoegd']:,}")
    print(f"  🔄 Bijgewerkt:       {stats['bijgewerkt']:,}")
    print(f"  ⏭️  Overgeslagen:     {stats['overgeslagen']:,}")
    print(f"  ❌ Fouten:           {stats['fouten']:,}")

    if stats["fouten_detail"]:
        print("\n   Fout details:")
        for d in stats["fouten_detail"]:
            print(f"   • {d}")

    if not args.dry_run:
        print("\n" + "=" * 60)
        print("✅ Stap 3 voltooid!")
        print()
        print("   Volgende stap:")
        print("   python etl_04_import_kompas.py")
        print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
