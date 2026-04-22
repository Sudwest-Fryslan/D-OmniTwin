#!/usr/bin/env python3
"""
D-OmniTwin ETL — Stap 6: Admin Gebruiker Aanmaken
==================================================
Maakt een admin gebruiker en API key aan in de database.
Kan ook gebruikt worden om het wachtwoord te resetten.

Gebruik:
    cd ETL/local
    python etl_06_maak_admin.py

    # Wachtwoord via commandline (niet aanbevolen voor productie):
    python etl_06_maak_admin.py --gebruiker admin --wachtwoord MijnWachtwoord123

    # Forceer reset van bestaande admin:
    python etl_06_maak_admin.py --reset

    # Overzicht van bestaande gebruikers:
    python etl_06_maak_admin.py --check

Configuratie:
    Zie ETL/local/db.ini.example → kopieer naar ETL/local/db.ini
"""

import sys
import secrets
import argparse
import getpass
from pathlib import Path
from datetime import datetime, timedelta

LOCAL_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT = LOCAL_DIR.parent.parent

sys.path.insert(0, str(LOCAL_DIR))
from db_connect import get_connection


def hash_wachtwoord(wachtwoord: str) -> str:
    """Hasheer wachtwoord met bcrypt via passlib."""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(wachtwoord)
    except ImportError:
        print("❌ passlib niet gevonden. Installeer met:")
        print("   pip install passlib[bcrypt] bcrypt==4.0.1")
        sys.exit(1)


def genereer_api_key(prefix: str = "omnitwin") -> str:
    """Genereer een veilige API key."""
    token = secrets.token_hex(32)
    return f"{prefix}_{token}"


def maak_admin(conn, gebruikersnaam: str, wachtwoord: str, email: str = None, force_reset: bool = False) -> dict:
    """
    Maak admin gebruiker aan of update bestaande.

    Returns:
        Dict met aangemaakte gegevens
    """
    cur = conn.cursor()

    # Controleer of gebruiker al bestaat
    cur.execute("SELECT id, username FROM users WHERE username = %s", (gebruikersnaam,))
    bestaand = cur.fetchone()

    if bestaand and not force_reset:
        print(f"  ℹ️  Gebruiker '{gebruikersnaam}' bestaat al (ID: {bestaand[0]})")
        print(f"     Gebruik --reset om het wachtwoord te overschrijven")
        cur.close()
        return {"bestaand": True, "user_id": bestaand[0]}

    wachtwoord_hash = hash_wachtwoord(wachtwoord)
    gebruiker_email = email or f"{gebruikersnaam}@omnitwin.local"

    if bestaand:
        # Update bestaande gebruiker
        cur.execute("""
            UPDATE users SET
                password_hash = %s,
                updated_at    = CURRENT_TIMESTAMP
            WHERE username = %s
            RETURNING id
        """, (wachtwoord_hash, gebruikersnaam))
        user_id = cur.fetchone()[0]
        print(f"  🔄 Wachtwoord bijgewerkt voor '{gebruikersnaam}' (ID: {user_id})")
        actie = "bijgewerkt"
    else:
        # Nieuwe gebruiker aanmaken
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, is_active)
            VALUES (%s, %s, %s, true, true)
            RETURNING id
        """, (gebruikersnaam, gebruiker_email, wachtwoord_hash))
        user_id = cur.fetchone()[0]
        print(f"  ✅ Gebruiker aangemaakt: '{gebruikersnaam}' (ID: {user_id})")
        actie = "aangemaakt"

    # Maak API key aan
    api_key = genereer_api_key()
    verloopt = datetime.now() + timedelta(days=365)

    cur.execute("""
        INSERT INTO api_keys (user_id, key_hash, naam, verloopt_op, is_actief)
        VALUES (%s, %s, %s, %s, true)
        ON CONFLICT (user_id, naam) DO UPDATE SET
            key_hash  = EXCLUDED.key_hash,
            verloopt_op = EXCLUDED.verloopt_op,
            is_actief = true
        RETURNING id
    """, (user_id, api_key, "Beheer API Key", verloopt))
    api_key_id = cur.fetchone()[0]

    conn.commit()
    cur.close()

    return {
        "actie":         actie,
        "user_id":       user_id,
        "gebruikersnaam": gebruikersnaam,
        "email":         gebruiker_email,
        "api_key":       api_key,
        "api_key_id":    api_key_id,
        "api_verloopt":  verloopt.strftime("%Y-%m-%d"),
    }


def show_gebruikers(conn):
    """Toon overzicht van gebruikers in de database."""
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.email, u.is_admin, u.is_active,
               COUNT(k.id) as n_keys
        FROM users u
        LEFT JOIN api_keys k ON k.user_id = u.id AND k.is_actief = true
        GROUP BY u.id, u.username, u.email, u.is_admin, u.is_active
        ORDER BY u.is_admin DESC, u.username
    """)
    gebruikers = cur.fetchall()
    cur.close()

    print(f"\n👥 Gebruikers in database: {len(gebruikers)}")
    print("─" * 60)
    for uid, uname, email, is_admin, is_active, n_keys in gebruikers:
        status = "✅ actief" if is_active else "🔴 inactief"
        rol    = "🔑 admin" if is_admin else "👤 gebruiker"
        print(f"  {rol:<14} {uname:<20} {status}  ({n_keys} API keys)")
        if email:
            print(f"  {'':14} {email}")


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Admin gebruiker aanmaken",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python etl_06_maak_admin.py
  python etl_06_maak_admin.py --gebruiker admin --wachtwoord Veilig@123
  python etl_06_maak_admin.py --reset
  python etl_06_maak_admin.py --check
        """
    )
    parser.add_argument("--gebruiker", default="admin",
                        help="Gebruikersnaam (standaard: admin)")
    parser.add_argument("--wachtwoord",
                        help="Wachtwoord (als niet opgegeven: interactieve prompt)")
    parser.add_argument("--email",
                        help="E-mailadres (standaard: <gebruiker>@omnitwin.local)")
    parser.add_argument("--reset", action="store_true",
                        help="Bestaande admin overschrijven")
    parser.add_argument("--check", action="store_true",
                        help="Overzicht van bestaande gebruikers")
    args = parser.parse_args()

    print("=" * 60)
    print("👤 D-OmniTwin — Stap 6: Admin Gebruiker Aanmaken")
    print("=" * 60)

    conn = get_connection()

    if args.check:
        show_gebruikers(conn)
        conn.close()
        return

    # Wachtwoord ophalen
    wachtwoord = args.wachtwoord
    if not wachtwoord:
        print(f"\nNieuw wachtwoord voor '{args.gebruiker}':")
        wachtwoord = getpass.getpass("  Wachtwoord: ")
        bevestig   = getpass.getpass("  Bevestig:   ")
        if wachtwoord != bevestig:
            print("❌ Wachtwoorden komen niet overeen")
            conn.close()
            sys.exit(1)

    if len(wachtwoord) < 8:
        print("❌ Wachtwoord moet minimaal 8 tekens bevatten")
        conn.close()
        sys.exit(1)

    print(f"\n👤 Gebruiker aanmaken: {args.gebruiker}")
    result = maak_admin(conn, args.gebruiker, wachtwoord, args.email, args.reset)

    if not result.get("bestaand"):
        print()
        print("  ─" * 30)
        print("  📋 BEWAAR DEZE GEGEVENS VEILIG:")
        print()
        print(f"  Gebruikersnaam: {result['gebruikersnaam']}")
        print(f"  API Key:        {result['api_key']}")
        print(f"  API Verloopt:   {result['api_verloopt']}")
        print()
        print("  Voeg toe aan .env:")
        print(f"  ADMIN_USER={result['gebruikersnaam']}")
        print(f"  ADMIN_API_KEY={result['api_key']}")
        print("  ─" * 30)

    print("\n" + "=" * 60)
    print("✅ Stap 6 voltooid!")
    print()
    print("   🌐 Start de applicatie:")
    print("   cd <project_root>")
    print("   python run_dev.py")
    print()
    print("   🔗 Open in browser: http://localhost:8000")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
