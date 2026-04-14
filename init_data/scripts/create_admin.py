#!/usr/bin/env python3
"""
D-OmniTwin — Admin Gebruiker Aanmaken
======================================
Stap 6 van de database initialisatie.
Maakt de eerste admin gebruiker en API key aan.

Gebruik:
    python init_data/scripts/create_admin.py
    python init_data/scripts/create_admin.py --username admin --reset-password

Vereisten:
    pip install psycopg2-binary python-dotenv passlib[bcrypt]
    Database ingesteld via .env (zie .env.example)

Gedrag:
    - Leest ADMIN_USER en ADMIN_PASSWORD uit .env
    - Als ADMIN_PASSWORD leeg is: interactief vragen
    - Genereert een ADMIN_API_KEY en slaat hash op in api_keys tabel
    - Biedt aan om ADMIN_API_KEY in .env bij te werken
    - Idempotent: veilig meerdere keren te draaien
"""

import argparse
import hashlib
import os
import re
import secrets
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

ROOT = Path(__file__).parent.parent.parent
ENV_FILE = ROOT / ".env"


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
# .env bijwerken
# ─────────────────────────────────────────────────────────
def update_env_key(key: str, value: str) -> bool:
    """Schrijft of overschrijft een key=value in het .env bestand."""
    if not ENV_FILE.exists():
        return False

    content = ENV_FILE.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)

    if pattern.search(content):
        new_content = pattern.sub(f"{key}={value}", content)
    else:
        new_content = content.rstrip("\n") + f"\n{key}={value}\n"

    ENV_FILE.write_text(new_content, encoding="utf-8")
    return True


# ─────────────────────────────────────────────────────────
# Hoofd functie
# ─────────────────────────────────────────────────────────
def create_admin(username: str, force_reset: bool = False):
    """
    Maakt een admin gebruiker aan (of update bestaande bij --reset-password).
    Genereert altijd een nieuwe API key.
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
            AND table_name IN ('users', 'sessions', 'api_keys')
        """)
        table_count = cur.fetchone()[0]
        if table_count < 3:
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
        _generate_api_key(cur, conn, user_id, username)
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

    # ── Stap 5: API Key genereren ──
    _generate_api_key(cur, conn, user_id, username)

    cur.close()
    conn.close()

    print()
    print("=" * 60)
    print("✅ Admin initialisatie voltooid!")
    print()
    print(f"   🌐 Admin Panel:      http://localhost:8000/admin")
    print(f"   👤 Gebruikersnaam:   {username}")
    print(f"   🔐 Wachtwoord:       [zoals ingesteld]")
    print("=" * 60)
    print()


def _generate_api_key(cur, conn, user_id, username: str):
    """Genereert een nieuwe API key, slaat de hash op, toont de plain key éénmalig."""
    print()
    print("────────────────────────────────────────────────────────────")
    print("🔑 API Key genereren")
    print("────────────────────────────────────────────────────────────")

    # Deactiveer oude keys voor deze user
    cur.execute("""
        UPDATE api_keys SET is_active = FALSE
        WHERE user_id = %s AND is_active = TRUE
    """, (user_id,))
    old_count = cur.rowcount
    if old_count > 0:
        print(f"   ♻️  {old_count} oude API key(s) gedeactiveerd")

    # Genereer nieuwe key (256-bit hex)
    plain_key = secrets.token_hex(32)
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

    cur.execute("""
        INSERT INTO api_keys (key_hash, label, user_id, is_active)
        VALUES (%s, %s, %s, TRUE)
    """, (key_hash, f"admin-key-{username}", user_id))
    conn.commit()

    # Aanbod om .env bij te werken
    if ENV_FILE.exists():
        try:
            answer = input("\n   📝 ADMIN_API_KEY bijwerken in .env? [J/n]: ").strip().lower()
            if answer in ("", "j", "ja", "y", "yes"):
                if update_env_key("ADMIN_API_KEY", plain_key):
                    print("   ✅ ADMIN_API_KEY bijgewerkt in .env")
                else:
                    print("   ⚠️  .env bestand niet gevonden — sla de key handmatig op!")
            else:
                print("   ⏭️  .env niet bijgewerkt — sla de key hieronder handmatig op!")
        except (EOFError, KeyboardInterrupt):
            # Niet-interactieve modus (bijv. CI/Docker) — key altijd tonen
            update_env_key("ADMIN_API_KEY", plain_key)
            print("   ✅ ADMIN_API_KEY automatisch bijgewerkt in .env (niet-interactief)")

    print()
    print("   ┌─────────────────────────────────────────────────────┐")
    print("   │ ⚠️  BEWAAR DEZE KEY — WORDT NIET OPNIEUW GETOOND!   │")
    print("   │                                                     │")
    print(f"   │  ADMIN_API_KEY={plain_key[:24]}...  │")
    print("   │                                                     │")
    print("   │  (Volledige key staat in je .env als je J koos)     │")
    print("   └─────────────────────────────────────────────────────┘")
    print()
    print(f"   Gebruik in HTTP header:  X-Admin-Key: {plain_key}")


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
