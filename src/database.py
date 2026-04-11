from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root resolution
project_root = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(project_root / '.env')

# Get database config from environment
db_host = os.getenv('DATABASE_HOST', 'localhost')
db_port = os.getenv('DATABASE_PORT', '5432')
db_name = os.getenv('DATABASE_NAME', 'omnitwin_db')
db_user = os.getenv('DATABASE_USER', 'omnitwin_user')
db_password = os.getenv('DATABASE_PASSWORD', '')
db_ssl_mode = os.getenv('DATABASE_SSLMODE', 'prefer')  # 'require' for production, 'prefer' for dev

# Construct Database URL with SSL support
# Format: postgresql://user:password@host:port/dbname?sslmode=MODE
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode={db_ssl_mode}"

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

