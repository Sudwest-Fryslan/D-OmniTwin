#!/usr/bin/env python3
"""
D-OmniTwin — Admin Gebruiker Aanmaken
======================================
Stap 6 van de database initialisatie.
Maakt de eerste admin gebruiker aan.

Gebruik:
    python init_data/scripts/create_admin.py
    python init_data/scripts/create_admin.py --username admin --reset-password

Vereisten:
    pip install psycopg2-binary python-dotenv passlib[bcrypt]
    Database ingesteld via .env (zie .env.example)

Gedrag:
    - Leest ADMIN_USER en ADMIN_PASSWORD uit .env
    - Als ADMIN_PASSWORD leeg is: interactief vragen
    - Idempotent: veilig meerdere keren te draaien
    - Exitcode 1 bij een fout: db-init stopt dan (docker-entrypoint.sh, #201)
    - Geen API-key: X-Admin-Key gebruikt ADMIN_API_KEY uit .env, die je zelf zet
      (zie .env.example). Er komen geen secrets in de log.
"""

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path

# Laad .env bestand vanuit projectroot
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass  # python-dotenv optioneel, env-vars worden direct gelezen

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 niet gevonden. Installeer met: pip install psycopg2-binary")
    sys.exit(1)

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    print("❌ passlib niet gevonden. Installeer met: pip install passlib[bcrypt]")
    sys.exit(1)


# ─────────────────────────────────────────────────────────
# Database verbinding
# ─────────────────────────────────────────────────────────
def get_db_connection():
    """Database connectie via environment variabelen."""
    return psycopg2.connect(
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
    )


# ─────────────────────────────────────────────────────────
# Wachtwoord ophalen (env of interactief)
# ─────────────────────────────────────────────────────────
def get_admin_password(username: str, force_reset: bool = False) -> str:
    """
    Haalt admin-wachtwoord op:
    1. Uit ADMIN_PASSWORD in .env (als aanwezig en niet leeg)
    2. Interactief vragen (met bevestiging)
    """
    if not force_reset:
        env_password = os.environ.get("ADMIN_PASSWORD", "").strip()
        if env_password:
            print(f"   📋 Wachtwoord geladen uit .env (ADMIN_PASSWORD)")
            return env_password

    # Interactief vragen
    print(f"   ⌨️  Stel een wachtwoord in voor '{username}':")
    while True:
        password = getpass("   Wachtwoord: ")
        if len(password) < 6:
            print("   ❌ Wachtwoord moet minimaal 6 tekens bevatten. Probeer opnieuw.")
            continue
        confirm = getpass("   Bevestig wachtwoord: ")
        if password != confirm:
            print("   ❌ Wachtwoorden komen niet overeen. Probeer opnieuw.")
            continue
        return password


# ─────────────────────────────────────────────────────────
# Hoofd functie
# ─────────────────────────────────────────────────────────
def create_admin(username: str, force_reset: bool = False):
    """
    Maakt een admin gebruiker aan (of update bestaande bij --reset-password).
    """
    print()
    print("=" * 60)
    print("👤 D-OmniTwin — Admin Gebruiker Initialisatie")
    print("=" * 60)

    # Database verbinding
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        print("✅ Database verbinding OK")
    except Exception as e:
        print(f"❌ Database verbinding mislukt: {e}")
        print("   Controleer je .env bestand en of de database actief is.")
        sys.exit(1)

    # ── Stap 1: Controleer of tabellen bestaan ──
    try:
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'users'
        """)
        table_count = cur.fetchone()[0]
        if table_count < 1:
            print("❌ User management tabellen niet gevonden!")
            print("   Voer eerst het schema script uit:")
            print(f"   bash init_data/scripts/init_database.sh")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Fout bij controleren tabellen: {e}")
        sys.exit(1)

    # ── Stap 2: Controleer of gebruiker al bestaat  ──
    cur.execute("SELECT id, is_admin FROM users WHERE username = %s", (username,))
    existing_user = cur.fetchone()

    if existing_user and not force_reset:
        user_id = existing_user[0]
        print(f"\n✅ Gebruiker '{username}' bestaat al (id: {user_id})")
        print("   Gebruik --reset-password om het wachtwoord te resetten.")
        cur.close()
        conn.close()
        return

    # ── Stap 3: Wachtwoord ophalen ──
    print()
    password = get_admin_password(username, force_reset=force_reset)
    hashed_password = pwd_context.hash(password)

    # ── Stap 4: Gebruiker aanmaken of updaten ──
    print()
    if existing_user and force_reset:
        user_id = existing_user[0]
        cur.execute("""
            UPDATE users
            SET hashed_password = %s, is_admin = TRUE, is_active = TRUE, updated_at = NOW()
            WHERE id = %s
        """, (hashed_password, user_id))
        print(f"🔄 Wachtwoord gereset voor gebruiker '{username}'")
    else:
        cur.execute("""
            INSERT INTO users (username, hashed_password, is_admin, is_active)
            VALUES (%s, %s, TRUE, TRUE)
            RETURNING id
        """, (username, hashed_password))
        user_id = cur.fetchone()[0]
        print(f"✅ Admin gebruiker aangemaakt: {username} (id: {user_id})")

    conn.commit()

    cur.close()
    conn.close()

    print()
    print("=" * 60)
    print("✅ Admin initialisatie voltooid!")
    print()
    print(f"   🌐 Admin Panel:      /admin/ (bijv. http://localhost/admin/)")
    print(f"   👤 Gebruikersnaam:   {username}")
    print(f"   🔐 Wachtwoord:       [zoals ingesteld]")
    print("=" * 60)
    print()


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Admin gebruiker aanmaken / resetten"
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("ADMIN_USER", "admin"),
        help="Gebruikersnaam voor de admin (default: ADMIN_USER uit .env, anders 'admin')"
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Bestaand wachtwoord resetten (ook als gebruiker al bestaat)"
    )
    args = parser.parse_args()

    create_admin(username=args.username, force_reset=args.reset_password)


if __name__ == "__main__":
    main()
