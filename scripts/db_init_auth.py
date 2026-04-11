#!/usr/bin/env python3
"""
Initialize Auth Tables
Aanmaken van de database tabellen voor het Beheerscherm Authenticatie Model (Sessies + Gebruikers).
Voegt standaardgebruiker `admin` met wachtwoord `admin` toe.
"""

from src.database import engine
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run():
    print("🚀 Initialiseren Auth Tabellen...")
    
    with engine.connect() as conn:
        with conn.begin():
            # 1. Users Tabel
            print("  -> Aanmaken tabel: users")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    username VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    is_admin BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 2. Sessions Tabel
            print("  -> Aanmaken tabel: sessions")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(255) PRIMARY KEY,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # 3. Voeg de default admin toe (indien niet bestaat)
            result = conn.execute(text("SELECT id FROM users WHERE username = 'admin'")).fetchone()
            
            if not result:
                print("  -> Aanmaken default beheerder account ('admin')")
                hashed_pw = pwd_context.hash("admin")
                conn.execute(text("""
                    INSERT INTO users (username, hashed_password, is_admin)
                    VALUES ('admin', :password, true)
                """), {"password": hashed_pw})
                print("  ✅ Gebruiker 'admin' aangemaakt (Wachtwoord = 'admin').")
            else:
                print("  ✅ Gebruiker 'admin' bestaat al.")
                
    print("\n✅ Auth database migratie voltooid!")

if __name__ == "__main__":
    run()
