"""Lokale Verwaltung von Sentence-Transformer-Modellen.

Die Funktionen lösen Modellnamen auf, speichern heruntergeladene Modelle im
Projektverzeichnis und stellen einen gemeinsamen Ladepfad für alle Pipeline-
Versionen bereit.
"""

from pathlib import Path

from sentence_transformers import SentenceTransformer

from prototype.shared.constants import MODEL_ALL_MINILM_L6_V2
from prototype.shared.logging_config import get_logger
from prototype.shared.paths import LOCAL_EMBEDDING_MODEL_PATH, MODELS_DIR


logger = get_logger(__name__)

LOCAL_EMBEDDING_MODEL_ALIASES = {
    "bge-m3": "BAAI/bge-m3",
}

_models: dict[str, SentenceTransformer] = {}


def resolve_local_embedding_model_name(model_name: str) -> str:
    normalized_name = model_name.strip()
    return LOCAL_EMBEDDING_MODEL_ALIASES.get(normalized_name.lower(), normalized_name)


def local_embedding_model_path(model_name: str) -> Path:
    resolved_model_name = resolve_local_embedding_model_name(model_name)
    if model_name == MODEL_ALL_MINILM_L6_V2:
        return LOCAL_EMBEDDING_MODEL_PATH

    safe_model_name = resolved_model_name.replace("/", "__").replace("\\", "__")
    return MODELS_DIR / safe_model_name


def get_local_embedding_model(model_name: str) -> SentenceTransformer:
    normalized_model_name = model_name.strip()
    resolved_model_name = resolve_local_embedding_model_name(normalized_model_name)
    local_model_path = local_embedding_model_path(normalized_model_name)

    if normalized_model_name in _models:
        return _models[normalized_model_name]

    if not local_model_path.exists():
        logger.info("Lokales Embedding-Modell nicht gefunden: %s", local_model_path)
        logger.info("Lade Embedding-Modell von HuggingFace: %s", resolved_model_name)
        temp_model = SentenceTransformer(resolved_model_name)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        temp_model.save(str(local_model_path))
        _models[normalized_model_name] = temp_model
        logger.info("Embedding-Modell gespeichert unter: %s", local_model_path)
    else:
        _models[normalized_model_name] = SentenceTransformer(str(local_model_path))

    return _models[normalized_model_name]
