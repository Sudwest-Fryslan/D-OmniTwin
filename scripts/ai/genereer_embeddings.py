"""
Genereert embeddings (multilingual-e5-small, 384 dimensies) voor AI-zoeken en de chat.

Standaard worden alle actieve indicatoren gevectoriseerd die nog geen embedding hebben of
waarvan de tekst of het model veranderd is (#233), ook concepten (#139): zonder embeddings
vinden AI-zoeken en de chat minder. De zoekfunctie geeft de ontologie_status per resultaat
mee, zodat concepten herkenbaar blijven.

Tekst per indicator: naam, kompaspad, eenheid, synoniemen (db/stuurdata/synoniemen.json) en de
beste beschikbare beschrijving; zie services/indicator_embeddings.py.

Gebruik:
    python scripts/ai/genereer_embeddings.py                       # nieuwe en gewijzigde indicatoren
    python scripts/ai/genereer_embeddings.py --alleen-goedgekeurd  # alleen status goedgekeurd_mens
    python scripts/ai/genereer_embeddings.py --opnieuw             # alles herberekenen

Exitcode 1 als het model niet geladen kan worden (niet in de image, offline, package ontbreekt).
Model en revisie: services/embedding_model.py (#118).
docker-entrypoint.sh vangt dat af: db-init geeft dan een waarschuwing en gaat door.
"""
import sys
from pathlib import Path

# Voeg src/ (pakket omnitwin) toe aan python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root / "src"))

from omnitwin.database import SessionLocal  # noqa: E402
from omnitwin.services import embedding_model  # noqa: E402
from omnitwin.services.indicator_embeddings import herbereken_embeddings  # noqa: E402


def generate_embeddings(alleen_goedgekeurd=False, opnieuw=False):
    """True bij succes (ook als er niets te doen was), False als het model ontbreekt."""
    db = SessionLocal()
    try:
        bron = embedding_model.MODEL_PAD if embedding_model.lokaal_aanwezig() else "HuggingFace-cache/download"
        print(f"⏳ Embeddings bijwerken met {embedding_model.MODEL_ID}@{embedding_model.MODEL_REVISIE[:8]} ({bron})...")
        try:
            r = herbereken_embeddings(db, opnieuw=opnieuw, alleen_goedgekeurd=alleen_goedgekeurd)
        except ImportError:
            print("⚠️ sentence-transformers niet geïnstalleerd; embeddings niet gegenereerd.")
            return False
        except Exception as e:  # ModelNietBeschikbaar, of modelbestanden onleesbaar
            print(f"⚠️ Embeddingmodel niet te laden: {e}")
            return False
        print(f"✅ {r['berekend']} embeddings berekend, {r['ongewijzigd']} ongewijzigd.")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Genereer embeddings voor AI-zoeken")
    parser.add_argument("--alleen-goedgekeurd", action="store_true",
                        help="Alleen indicatoren met status goedgekeurd_mens")
    parser.add_argument("--opnieuw", action="store_true",
                        help="Ook ongewijzigde embeddings herberekenen")
    args = parser.parse_args()

    ok = generate_embeddings(alleen_goedgekeurd=args.alleen_goedgekeurd, opnieuw=args.opnieuw)
    sys.exit(0 if ok else 1)
