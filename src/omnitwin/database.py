from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from omnitwin.config import instellingen

# Databaseverbinding uit de omgeving of .env (zie src/omnitwin/config.py).
# Format: postgresql+psycopg2://user:password@host:port/dbname?sslmode=MODE
# DATABASE_SSLMODE: 'require' for production, 'prefer' for dev
DATABASE_URL = instellingen().database_url

engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Basis connecties in de pool (was: 5)
    max_overflow=20,        # Extra connecties bij piek (was: 10)
    pool_pre_ping=True,     # Detecteer dode connecties automatisch
    pool_recycle=1800,      # Recycle connecties na 30 minuten
    pool_timeout=30,        # Timeout voor het wachten op een connectie
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

