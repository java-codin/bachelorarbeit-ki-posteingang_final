"""Zentrale Embedding-Erzeugung für lokale und OpenAI-basierte Anbieter.

Das Modul kapselt Provider-Auswahl, Lazy Loading und Batch-Verarbeitung, damit
die Pipeline-Versionen keine eigene Download- oder API-Logik duplizieren
müssen.
"""

import os
from typing import Any

import numpy as np
from dotenv import load_dotenv

from prototype.shared.constants import (
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    ENV_EMBEDDING_PROVIDER,
    ENV_LOCAL_EMBEDDING_MODEL,
    ENV_OPENAI_API_KEY,
    ENV_OPENAI_EMBEDDING_MODEL,
    MODEL_ALL_MINILM_L6_V2,
    PROVIDER_LOCAL,
    PROVIDER_ONLINE,
    PROVIDER_OPENAI,
)
from prototype.shared.local_embedding_models import get_local_embedding_model
from prototype.shared.model_profiles import (
    EMBEDDING_STEP_RETRIEVAL,
    active_embedding_step_metadata,
)
from prototype.shared.paths import ENV_PATH

load_dotenv(ENV_PATH)

FALLBACK_TEXT = "Leerer Eingabetext."
OPENAI_EMBEDDING_MAX_BATCH_ITEMS = 64
OPENAI_EMBEDDING_MAX_BATCH_CHARS = 120_000

_openai_client = None


def _current_embedding_provider() -> str:
    return (
        active_embedding_step_metadata(EMBEDDING_STEP_RETRIEVAL).get("embedding_provider")
        or os.getenv(ENV_EMBEDDING_PROVIDER, PROVIDER_LOCAL)
    ).strip().lower()


def _current_local_embedding_model() -> str:
    return (
        active_embedding_step_metadata(EMBEDDING_STEP_RETRIEVAL).get("embedding_model")
        or os.getenv(ENV_LOCAL_EMBEDDING_MODEL, MODEL_ALL_MINILM_L6_V2)
    ).strip()


def _current_openai_embedding_model() -> str:
    return (
        active_embedding_step_metadata(EMBEDDING_STEP_RETRIEVAL).get("embedding_model")
        or os.getenv(ENV_OPENAI_EMBEDDING_MODEL, DEFAULT_OPENAI_EMBEDDING_MODEL)
    ).strip()


def get_embedding_metadata() -> dict[str, str]:
    provider = _current_embedding_provider()
    model = _current_openai_embedding_model() if provider in {PROVIDER_ONLINE, PROVIDER_OPENAI} else _current_local_embedding_model()
    return {"embedding_provider": provider, "embedding_model": model}


def _get_openai_client():
    global _openai_client

    if _openai_client is None:
        api_key = os.getenv(ENV_OPENAI_API_KEY)
        if not api_key:
            raise ValueError(f"{ENV_OPENAI_API_KEY} ist nicht gesetzt.")

        from openai import OpenAI
        _openai_client = OpenAI(api_key=api_key)

    return _openai_client


def _normalize_embedding_text(text: Any) -> str:
    return text if isinstance(text, str) and text.strip() else FALLBACK_TEXT


def _get_openai_embedding(text: str) -> np.ndarray:
    response = _get_openai_client().embeddings.create(
        input=[text],
        model=_current_openai_embedding_model(),
    )
    return np.array(response.data[0].embedding)


def _get_openai_embeddings(texts: list[str]) -> list[np.ndarray]:
    client = _get_openai_client()
    model_name = _current_openai_embedding_model()
    embeddings: list[np.ndarray] = []
    batch: list[str] = []
    batch_chars = 0

    def flush_batch() -> None:
        nonlocal batch, batch_chars
        if not batch:
            return

        response = client.embeddings.create(input=batch, model=model_name)
        embeddings.extend(np.array(item.embedding) for item in response.data)
        batch = []
        batch_chars = 0

    for text in texts:
        if len(batch) >= OPENAI_EMBEDDING_MAX_BATCH_ITEMS or (
            batch and batch_chars + len(text) > OPENAI_EMBEDDING_MAX_BATCH_CHARS
        ):
            flush_batch()

        batch.append(text)
        batch_chars += len(text)

    flush_batch()
    return embeddings


def create_embedding(text: Any) -> np.ndarray:
    normalized_text = _normalize_embedding_text(text)

    if _current_embedding_provider() in {PROVIDER_ONLINE, PROVIDER_OPENAI}:
        return _get_openai_embedding(normalized_text)

    model = get_local_embedding_model(_current_local_embedding_model())
    return np.array(model.encode(normalized_text, convert_to_numpy=True))


def create_embeddings(texts: list[Any]) -> list[np.ndarray]:
    normalized_texts = [_normalize_embedding_text(text) for text in texts]

    if _current_embedding_provider() in {PROVIDER_ONLINE, PROVIDER_OPENAI}:
        return _get_openai_embeddings(normalized_texts)

    model = get_local_embedding_model(_current_local_embedding_model())
    return [np.array(embedding) for embedding in model.encode(normalized_texts, convert_to_numpy=True)]
