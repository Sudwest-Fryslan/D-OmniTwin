"""
Embeddingmodel voor AI-zoeken en de chat: de enige plek waar model en revisie staan (#118).

Model:   sentence-transformers/all-MiniLM-L6-v2 (384 dimensies)
Licentie: Apache-2.0 (https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
Revisie: vastgepind op een commit van de HuggingFace-repository, zodat embeddings
         reproduceerbaar zijn. Bijwerken: zie docs/9-beheer/installatie.md.

In de Docker-image staat het model al in MODEL_PAD (download tijdens `docker build`,
via `python src/omnitwin/services/embedding_model.py`). De container draait met HF_HUB_OFFLINE=1:
geen download en geen telemetrie bij het starten.

Buiten Docker (lokaal ontwikkelen) ontbreekt MODEL_PAD meestal. Dan wordt het model
met dezelfde revisie uit de HuggingFace-cache geladen, of gedownload als dat mag.
Met HF_HUB_OFFLINE=1 en zonder lokale kopie volgt een duidelijke foutmelding.

Dit bestand importeert bij het laden alleen de standaardbibliotheek, zodat het
Dockerfile het vóór `COPY . .` los kan draaien.
"""
import os
from pathlib import Path

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISIE = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"  # 2026-06-01
MODEL_NAAM = "all-MiniLM-L6-v2"  # korte naam, opgeslagen in indicator_embeddings.model_naam

# Map met de modelbestanden. Buiten /app, zodat de bind-mount in dev hem niet verbergt.
MODEL_PAD = Path(os.environ.get("EMBEDDING_MODEL_PAD", "/opt/models/all-MiniLM-L6-v2"))

# Alleen wat sentence-transformers met PyTorch nodig heeft; geen ONNX/OpenVINO/TF-varianten
_BESTANDEN = ["*.json", "model.safetensors", "vocab.txt", "README.md", "1_Pooling/*"]


class ModelNietBeschikbaar(RuntimeError):
    """Het embeddingmodel staat niet lokaal en mag niet gedownload worden."""


def offline() -> bool:
    return os.environ.get("HF_HUB_OFFLINE", "").lower() in ("1", "true", "yes", "on")


def lokaal_aanwezig() -> bool:
    return (MODEL_PAD / "model.safetensors").is_file() and (MODEL_PAD / "modules.json").is_file()


def status() -> dict:
    """Status voor /api/ai/health: staat het model lokaal en draait de container offline."""
    return {
        "model": MODEL_ID,
        "revisie": MODEL_REVISIE,
        "pad": str(MODEL_PAD),
        "lokaal": lokaal_aanwezig(),
        "offline": offline(),
    }


def laad_model():
    """
    Laadt het SentenceTransformer-model: uit MODEL_PAD als dat er is, anders met de
    gepinde revisie via HuggingFace (alleen als offline-modus uit staat).
    Gooit ModelNietBeschikbaar met een uitleg als het model er niet is.
    """
    from sentence_transformers import SentenceTransformer

    if lokaal_aanwezig():
        return SentenceTransformer(str(MODEL_PAD), device="cpu", local_files_only=True)
    try:
        return SentenceTransformer(MODEL_ID, revision=MODEL_REVISIE, device="cpu",
                                   local_files_only=offline())
    except Exception as e:
        raise ModelNietBeschikbaar(
            f"Embeddingmodel {MODEL_ID}@{MODEL_REVISIE[:8]} niet gevonden in {MODEL_PAD}"
            + (" en offline-modus staat aan (HF_HUB_OFFLINE=1)" if offline() else "")
            + f". In Docker: bouw de image opnieuw (docker compose build). "
            f"Lokaal: zet HF_HUB_OFFLINE uit (eenmalige download naar de HuggingFace-cache), "
            f"of download naar een map met EMBEDDING_MODEL_PAD=<map> python src/omnitwin/services/embedding_model.py. "
            f"Oorzaak: {e}"
        ) from e


def download(doel: Path = MODEL_PAD) -> None:
    """Downloadt de gepinde revisie naar doel (gebruikt door het Dockerfile)."""
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=MODEL_ID, revision=MODEL_REVISIE, local_dir=str(doel),
                      allow_patterns=_BESTANDEN)
    print(f"Model {MODEL_ID}@{MODEL_REVISIE} staat in {doel}")


if __name__ == "__main__":
    download()
