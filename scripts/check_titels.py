from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

# Database connection
db_user = os.getenv('DATABASE_USER', 'omnitwin_user')
db_password = os.getenv('DATABASE_PASSWORD', '')
db_host = os.getenv('DATABASE_HOST', 'localhost')
db_port = os.getenv('DATABASE_PORT', '5432')
db_name = os.getenv('DATABASE_NAME', 'omnitwin_db')

db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(db_url)

with engine.connect() as conn:
    print("Querying unique titel_naam from v_kompas_hierarchie...")
    result = conn.execute(text("SELECT DISTINCT titel_naam FROM v_kompas_hierarchie ORDER BY titel_naam"))
    rows = result.fetchall()
    print("Found titles:")
    for row in rows:
        print(f"- {row[0]}")
