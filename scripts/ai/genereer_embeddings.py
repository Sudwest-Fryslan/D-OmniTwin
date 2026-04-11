import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np

# Voeg project root toe aan python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.database import SessionLocal

# Zorg dat we sentence-transformers kunnen importeren
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("❌ sentence-transformers niet gevonden. Installeer deze eerst.")
    sys.exit(1)

def generate_embeddings(force_all=False):
    """
    Genereert embeddings voor indicatoren die een ontologische beschrijving hebben.
    
    Args:
        force_all: Indien True, verwerk ook 'beoordeeld_ai' status. 
                   Indien False, alleen 'goedgekeurd_mens'.
    """
    db = SessionLocal()
    
    # 1. Model laden (local cache)
    print("⏳ Laden van sentence-transformers model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 2. Query indicatoren die een beschrijving hebben maar nog geen embedding
    # We sluiten indicatoren uit die al een embedding hebben voor dit specifieke model
    status_filter = "('goedgekeurd_mens')"
    if force_all:
        status_filter = "('goedgekeurd_mens', 'beoordeeld_ai')"
        
    query = text(f"""
        SELECT i.uuid, i.naam, i.ontologische_beschrijving 
        FROM indicatoren i
        LEFT JOIN indicator_embeddings e ON i.uuid = e.indicator_uuid
        WHERE i.ontologische_beschrijving IS NOT NULL 
          AND i.ontologie_status IN {status_filter}
          AND e.id IS NULL
    """)
    
    indicatoren = db.execute(query).fetchall()
    
    if not indicatoren:
        print("✅ Geen nieuwe indicatoren om te vectoriseren (of status niet op 'goedgekeurd_mens').")
        db.close()
        return

    print(f"🚀 Start vectorisatie van {len(indicatoren)} indicatoren...")
    
    for row in indicatoren:
        uuid, naam, description = row
        print(f"--- Vectoriseren: {naam} ---")
        
        # Embedding genereren
        embedding = model.encode(description)
        
        # Converteren naar list voor pgvector (SQLAlchemy text)
        embedding_list = embedding.tolist()
        
        # Opslaan in database
        # We gebruiken de vector(384) kolom
        insert_query = text("""
            INSERT INTO indicator_embeddings (indicator_uuid, embedding, model_naam)
            VALUES (:uuid, :emb, 'all-MiniLM-L6-v2')
            ON CONFLICT (indicator_uuid) DO UPDATE 
            SET embedding = :emb, updated_at = CURRENT_TIMESTAMP
        """)
        
        db.execute(insert_query, {
            "uuid": uuid,
            "emb": embedding_list
        })
        db.commit()
        print(f"✅ Embedding opgeslagen voor {naam}")

    db.close()
    print("\n🏁 Vectorisatie voltooid.")

if __name__ == "__main__":
    # In dev mode staan we force_all toe om de 5 test indicatoren te verwerken
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Process all indicators with AI status too")
    args = parser.parse_args()
    
    generate_embeddings(force_all=args.all)
