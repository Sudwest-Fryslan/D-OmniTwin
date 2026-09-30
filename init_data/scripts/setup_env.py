#!/usr/bin/env python3
"""
D-OmniTwin — Setup Environment Wizard
=====================================
Dit script genereert interactief een veilig .env configuratiebestand 
voor de applicatie.

Gebruik:
    python init_data/scripts/setup_env.py
"""

import os
import secrets
import string
from pathlib import Path
import getpass

ROOT = Path(__file__).parent.parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def generate_password(length=16):
    """Genereer een veilig, willekeurig wachtwoord."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for i in range(length))


def prompt(text, default=""):
    """Vraag om input met een standaardwaarde."""
    prompt_text = f"{text} [{default}]: " if default else f"{text}: "
    response = input(prompt_text).strip()
    return response if response else default


def prompt_password(text, auto_generate=True):
    """Vraag om een wachtwoord of genereer er een automatisch als het leeg wordt gelaten."""
    prompt_text = f"{text} (laat leeg voor auto-generatie): " if auto_generate else f"{text}: "
    response = getpass.getpass(prompt_text).strip()
    
    if not response and auto_generate:
        response = generate_password()
        print(f"   ↳ Gegenereerd wachtwoord: {response}")
    
    return response


def main():
    print("\n" + "="*50)
    print("🪄  D-OmniTwin — .env Configuratie Wizard")
    print("="*50 + "\n")

    if ENV_FILE.exists():
        print(f"⚠️  Er bestaat al een .env bestand op {ENV_FILE.absolute()}")
        if input("   Wil je dit overschrijven? (y/N): ").strip().lower() != 'y':
            print("Geannuleerd. Je huidige .env is ongewijzigd.")
            return

    if not ENV_EXAMPLE.exists():
        print(f"❌ Kan {ENV_EXAMPLE.name} niet vinden! Zorg dat je in de root van de repository bent.")
        return

    print("We gaan nu de benodigde instellingen invullen.\n")

    # Verzamel inputs
    db_name = prompt("1. Database naam", "omnitwin_db")
    db_user = prompt("2. Database gebruiker", "omnitwin_user")
    db_pass = prompt_password(f"3. Wachtwoord voor {db_user}", auto_generate=True)
    
    admin_user = prompt("4. Applicatie Admin gebruikersnaam", "admin")
    admin_pass = prompt_password(f"5. Wachtwoord voor {admin_user}", auto_generate=True)

    # Genereer secure keys
    secret_key = secrets.token_urlsafe(32)
    admin_api_key = secrets.token_hex(32)

    # Lees template en vervang
    with open(ENV_EXAMPLE, "r", encoding="utf-8") as f:
        env_content = f.read()

    # Vervang placeholders (dit is robuuster dan exact string matchen omdat we keys vervangen)
    import re
    
    replacements = {
        r"DATABASE_NAME=.*": f"DATABASE_NAME={db_name}",
        r"DATABASE_USER=.*": f"DATABASE_USER={db_user}",
        r"DATABASE_PASSWORD=.*": f"DATABASE_PASSWORD={db_pass}",
        r"SECRET_KEY=.*": f"SECRET_KEY={secret_key}",
        r"ADMIN_USER=.*": f"ADMIN_USER={admin_user}",
        r"ADMIN_PASSWORD=.*": f"ADMIN_PASSWORD={admin_pass}",
        r"ADMIN_API_KEY=.*": f"ADMIN_API_KEY={admin_api_key}",
    }

    for pattern, replacement in replacements.items():
        env_content = re.sub(pattern, replacement, env_content)

    # Schrijf naar .env
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(env_content)

    print("\n" + "="*50)
    print("✅ .env bestand is succesvol aangemaakt!")
    print("="*50)
    print(f"\n🔑 Bewaar deze inloggegevens goed:")
    print(f"   Applicatie url:  http://localhost:8000/admin")
    print(f"   Gebruikersnaam:  {admin_user}")
    print(f"   Wachtwoord:      {admin_pass}\n")
    print(f"   (Deze logingegevens staan ook in het .env bestand)")
    print("\nVolgende stap: Voer het database init script uit (indien je dit nog niet hebt gedaan):")
    print("   bash init_data/scripts/init_database.sh")


if __name__ == "__main__":
    main()
