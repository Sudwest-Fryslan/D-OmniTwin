"""
Genereert embeddings (all-MiniLM-L6-v2, 384 dimensies) voor AI-zoeken in het Kompas.

Standaard worden alle actieve indicatoren zonder embedding gevectoriseerd, ook
concepten (#139): zonder embeddings vinden AI-zoeken en de chat niets. De zoekfunctie
geeft de ontologie_status per resultaat mee, zodat concepten herkenbaar blijven.

Tekst per indicator: naam + beste beschikbare beschrijving
(ontologische_beschrijving > beschrijving_ai > omschrijving).

Gebruik:
    python scripts/ai/genereer_embeddings.py                       # alle indicatoren zonder embedding
    python scripts/ai/genereer_embeddings.py --alleen-goedgekeurd  # alleen status goedgekeurd_mens
    python scripts/ai/genereer_embeddings.py --opnieuw             # ook bestaande embeddings herberekenen

Exitcode 1 als het model niet geladen kan worden (niet in de image, offline, package ontbreekt).
Model en revisie: services/embedding_model.py (#118).
docker-entrypoint.sh vangt dat af: db-init geeft dan een waarschuwing en gaat door.
"""
import sys
from pathlib import Path

from sqlalchemy import text

# Voeg src/ (pakket omnitwin) toe aan python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root / "src"))

from omnitwin.database import SessionLocal
from omnitwin.services import embedding_model
from omnitwin.services.embedding_model import MODEL_NAAM


def laad_model():
    """Laadt het model (lokaal, gepinde revisie), of geeft None met een waarschuwing."""
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print("⚠️ sentence-transformers niet geïnstalleerd; embeddings niet gegenereerd.")
        return None
    bron = embedding_model.MODEL_PAD if embedding_model.lokaal_aanwezig() else "HuggingFace-cache/download"
    print(f"⏳ Laden van model {embedding_model.MODEL_ID}@{embedding_model.MODEL_REVISIE[:8]} uit {bron}...")
    try:
        return embedding_model.laad_model()
    except Exception as e:
        print(f"⚠️ {e}")
        return None


def generate_embeddings(alleen_goedgekeurd=False, opnieuw=False):
    """
    Genereert embeddings voor actieve indicatoren.

    Args:
        alleen_goedgekeurd: alleen indicatoren met status 'goedgekeurd_mens'.
        opnieuw: ook indicatoren die al een embedding hebben opnieuw berekenen.

    Returns:
        True bij succes (ook als er niets te doen was), False als het model ontbreekt.
    """
    db = SessionLocal()
    try:
        filters = ["i.is_actief = true"]
        if alleen_goedgekeurd:
            filters.append("i.ontologie_status = 'goedgekeurd_mens'")
        if not opnieuw:
            filters.append("e.id IS NULL")

        indicatoren = db.execute(text(f"""
            SELECT i.uuid, i.naam,
                   COALESCE(NULLIF(i.ontologische_beschrijving, ''),
                            NULLIF(i.beschrijving_ai, ''),
                            NULLIF(i.omschrijving, '')) AS beschrijving
            FROM indicatoren i
            LEFT JOIN indicator_embeddings e ON i.uuid = e.indicator_uuid
            WHERE {' AND '.join(filters)}
            ORDER BY i.naam
        """)).fetchall()

        if not indicatoren:
            print("✅ Geen nieuwe indicatoren om te vectoriseren.")
            return True

        model = laad_model()
        if model is None:
            return False

        print(f"🚀 Vectoriseren van {len(indicatoren)} indicatoren...")
        teksten = [f"{naam}. {beschrijving}" if beschrijving else naam
                   for _, naam, beschrijving in indicatoren]
        vectoren = model.encode(teksten, batch_size=32, show_progress_bar=False)

        insert_query = text("""
            INSERT INTO indicator_embeddings (indicator_uuid, embedding, model_naam)
            VALUES (:uuid, CAST(:emb AS vector), :model)
            ON CONFLICT (indicator_uuid) DO UPDATE
            SET embedding = EXCLUDED.embedding, model_naam = EXCLUDED.model_naam,
                updated_at = CURRENT_TIMESTAMP
        """)
        for (uuid, _, _), vector in zip(indicatoren, vectoren):
            db.execute(insert_query, {"uuid": uuid, "emb": vector.tolist(), "model": MODEL_NAAM})
        db.commit()
        print(f"✅ {len(indicatoren)} embeddings opgeslagen.")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Genereer embeddings voor AI-zoeken")
    parser.add_argument("--alleen-goedgekeurd", action="store_true",
                        help="Alleen indicatoren met status goedgekeurd_mens")
    parser.add_argument("--opnieuw", action="store_true",
                        help="Ook bestaande embeddings herberekenen")
    args = parser.parse_args()

    ok = generate_embeddings(alleen_goedgekeurd=args.alleen_goedgekeurd, opnieuw=args.opnieuw)
    sys.exit(0 if ok else 1)
