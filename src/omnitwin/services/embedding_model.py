"""
Embeddingmodel voor AI-zoeken en de chat: de enige plek waar model en revisie staan (#118).

Model:   intfloat/multilingual-e5-small (384 dimensies, meertalig, ook Nederlands; #233)
Licentie: MIT (https://huggingface.co/intfloat/multilingual-e5-small)
Revisie: vastgepind op een commit van de HuggingFace-repository, zodat embeddings
         reproduceerbaar zijn. Bijwerken: zie docs/9-beheer/installatie.md.
Opslag:  de gewichten staan als float16 in de image (225 MB in plaats van 450 MB; bij het
         laden weer float32). Het verschil in embeddings is verwaarloosbaar (< 0,001 cosinus).

Tot #233 was het model all-MiniLM-L6-v2 (Engelstalig). Op de Nederlandse evaluatievragen
(tests/data/assistent_evaluatie.json) vond dat model de juiste indicator veel minder vaak.

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
import threading
from pathlib import Path

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISIE = "614241f622f53c4eeff9890bdc4f31cfecc418b3"  # 2026-10-02
MODEL_NAAM = "multilingual-e5-small"  # korte naam, opgeslagen in indicator_embeddings.model_naam

# E5-modellen verwachten een voorvoegsel: 'query: ' voor de vraag, 'passage: ' voor de indicator
VRAAG_VOORVOEGSEL = "query: "
TEKST_VOORVOEGSEL = "passage: "

# Gelijkenis schalen (services/zoektaal.py): per vraag ten opzichte van de mediane gelijkenis
# met alle indicatoren. E5 geeft hoge cosinussen voor bijna alles (mediaan rond 0,79); wat telt
# is hoeveel een indicator boven die mediaan uitkomt. Op of onder mediaan + ONDER telt als geen
# gelijkenis, op of boven mediaan + BOVEN als volledige. Afgestemd op de evaluatieset (#233).
GELIJKENIS_MARGE_ONDER = 0.0
GELIJKENIS_MARGE_BOVEN = 0.07

# Map met de modelbestanden. Buiten /app, zodat de bind-mount in dev hem niet verbergt.
MODEL_PAD = Path(os.environ.get("EMBEDDING_MODEL_PAD", "/opt/models/multilingual-e5-small"))

# Alleen wat sentence-transformers met PyTorch nodig heeft; geen ONNX/OpenVINO/TF-varianten
_BESTANDEN = ["config.json", "modules.json", "sentence_bert_config.json", "special_tokens_map.json",
             "tokenizer.json", "tokenizer_config.json", "model.safetensors", "sentencepiece.bpe.model",
             "1_Pooling/*"]


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
        # .float(): de gewichten staan als float16 in de image; rekenen in float32 op de CPU
        return SentenceTransformer(str(MODEL_PAD), device="cpu", local_files_only=True).float()
    try:
        return SentenceTransformer(MODEL_ID, revision=MODEL_REVISIE, device="cpu",
                                   local_files_only=offline()).float()
    except Exception as e:
        raise ModelNietBeschikbaar(
            f"Embeddingmodel {MODEL_ID}@{MODEL_REVISIE[:8]} niet gevonden in {MODEL_PAD}"
            + (" en offline-modus staat aan (HF_HUB_OFFLINE=1)" if offline() else "")
            + f". In Docker: bouw de image opnieuw (docker compose build). "
            f"Lokaal: zet HF_HUB_OFFLINE uit (eenmalige download naar de HuggingFace-cache), "
            f"of download naar een map met EMBEDDING_MODEL_PAD=<map> python src/omnitwin/services/embedding_model.py. "
            f"Oorzaak: {e}"
        ) from e


_gedeeld = None
_slot = threading.Lock()


def gedeeld_model():
    """Eén geladen model per proces (AI-zoeken, chat en herberekenen na een levering)."""
    global _gedeeld
    with _slot:
        if _gedeeld is None:
            _gedeeld = laad_model()
        return _gedeeld


def naar_float16(doel: Path = MODEL_PAD) -> None:
    """Slaat de gewichten op als float16: de helft van de ruimte in de image (#233)."""
    from safetensors.torch import load_file, save_file

    pad = Path(doel) / "model.safetensors"
    gewichten = load_file(str(pad))
    save_file({k: (v.half() if v.is_floating_point() else v) for k, v in gewichten.items()},
              str(pad), metadata={"format": "pt"})
    os.chmod(pad, 0o644)  # save_file maakt het bestand alleen leesbaar voor root; de app draait als gewone gebruiker


def download(doel: Path = MODEL_PAD) -> None:
    """Downloadt de gepinde revisie naar doel en zet de gewichten om naar float16 (Dockerfile)."""
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=MODEL_ID, revision=MODEL_REVISIE, local_dir=str(doel),
                      allow_patterns=_BESTANDEN)
    naar_float16(doel)
    print(f"Model {MODEL_ID}@{MODEL_REVISIE} staat in {doel} (float16)")


if __name__ == "__main__":
    download()
