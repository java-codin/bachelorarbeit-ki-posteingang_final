"""Embedding-Zugriff der Pipeline v5.

Das Modul stellt die v5-Embedding-Schnittstelle bereit und kapselt lokale sowie
OpenAI-basierte Embedding-Erzeugung für Retrieval und Indexaufbau.
"""

import os
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
from prototype.shared.local_embedding_models import (
    get_local_embedding_model,
    local_embedding_model_path,
    resolve_local_embedding_model_name,
)
from prototype.shared.paths import ENV_PATH
from prototype.shared.model_profiles import EMBEDDING_STEP_RETRIEVAL, active_embedding_step_metadata
from src.v5.core.constants import FALLBACK_TEXT
from src.v5.core.response_messages import ERR_OPENAI_KEY_MISSING

from openai import OpenAI

# Laden der Umgebungsvariablen (.env)
load_dotenv(ENV_PATH)

# Konfiguration des Embedding-Providers (local oder online/openai)
EMBEDDING_PROVIDER = os.getenv(ENV_EMBEDDING_PROVIDER, PROVIDER_LOCAL).lower()

# Globale Instanzen für Lazy Loading
_openai_client = None

OPENAI_EMBEDDING_MAX_BATCH_ITEMS = 64
OPENAI_EMBEDDING_MAX_BATCH_CHARS = 120_000


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


def _resolve_local_embedding_model_name(model_name: str) -> str:
    return resolve_local_embedding_model_name(model_name)


def _local_embedding_model_path(model_name: str) -> str:
    return str(local_embedding_model_path(model_name))


def get_embedding_metadata() -> dict[str, str]:
    provider = _current_embedding_provider()
    if provider in [PROVIDER_ONLINE, PROVIDER_OPENAI]:
        model_name = (
            active_embedding_step_metadata(EMBEDDING_STEP_RETRIEVAL).get("embedding_model")
            or os.getenv(ENV_OPENAI_EMBEDDING_MODEL, DEFAULT_OPENAI_EMBEDDING_MODEL)
        ).strip()
    else:
        model_name = _current_local_embedding_model()

    return {
        "embedding_provider": provider,
        "embedding_model": model_name,
    }


def _get_local_model():
    """
    Lädt ein vortrainiertes Modell lokal oder von HuggingFace und speichert es bei Bedarf.

    Diese Funktion stellt sicher, dass das Modell `SentenceTransformer` lokal verfügbar ist. Falls
    es nicht existiert, wird das Modell von HuggingFace geladen, in einem festgelegten Verzeichnis
    gespeichert und anschließend verwendet. Andernfalls wird das Modell aus dem lokalen Pfad
    eingelesen.

    :return: Das geladene oder bereits vorhandene lokale Embedding-Modell.
    """
    return get_local_embedding_model(_current_local_embedding_model())


def _get_openai_embedding(text: str) -> np.ndarray:
    """
    Erzeugt ein OpenAI-Embedding für den Eingabetext mithilfe des konfigurierten Modells und Clients.

    Diese Funktion verwendet die OpenAI-API, um ein numerisches Embedding basierend auf dem
    gegebenen `text` zu berechnen. Der zu verwendende Modellname wird aus der Umgebungsvariable
    `ENV_OPENAI_EMBEDDING_MODEL` bezogen oder auf den Standardwert `DEFAULT_OPENAI_EMBEDDING_MODEL`
    (`"text-similarity-babbage-001"`) zurückgegriffen, falls kein Wert angegeben ist.
    Falls der globale OpenAI-Client `_openai_client` noch nicht initialisiert ist, wird er innerhalb
    der Funktion mit dem API-Schlüssel aus der Umgebungsvariable `ENV_OPENAI_API_KEY` erstellt.

    Fehler werden geworfen, wenn:
    - Der erforderliche API-Schlüssel nicht in den Umgebungsvariablen definiert wurde
      (`ValueError` mit dem Fehlertext `ERR_OPENAI_KEY_MISSING`).
    - Der OpenAI-Embeddings-API-Aufruf fehlgeschlagen ist, abhängig von der Konfiguration der API.

    :param text: Der Eingabetext, für den ein Embedding erzeugt werden soll.
    :return: Ein `np.ndarray`, das das berechnete numerische Embedding für den Eingabetext darstellt.
    """
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv(ENV_OPENAI_API_KEY)
        if not api_key:
            raise ValueError(ERR_OPENAI_KEY_MISSING)
        _openai_client = OpenAI(api_key=api_key)

    # Modellname aus Config oder Default
    model_name = (
        active_embedding_step_metadata(EMBEDDING_STEP_RETRIEVAL).get("embedding_model")
        or os.getenv(ENV_OPENAI_EMBEDDING_MODEL, DEFAULT_OPENAI_EMBEDDING_MODEL)
    )
    
    response = _openai_client.embeddings.create(
        input=[text],
        model=model_name
    )
    return np.array(response.data[0].embedding)


def _normalize_embedding_text(text: str) -> str:
    """
    Normalisiert einen Eingabetext für die Einbettungsverarbeitung.

    Diese Funktion überprüft, ob der Eingabetext ein gültiger `str` ist, und gibt
    eine fallback-Option zurück, falls der Text ungültig ist oder nicht zur
    Verarbeitung geeignet ist.

    :param text: Der Eingabetext, der für die Einbettung verarbeitet werden soll.
    :return: Der normalisierte Text, falls gültig, oder ein Fallback-Text.
    """
    if not text or not isinstance(text, str):
        return FALLBACK_TEXT

    return text


def _get_openai_embeddings(texts: list[str]) -> list[np.ndarray]:
    """
    Berechnet die OpenAI-Embeddings für eine gegebene Liste von Texten.

    Diese Funktion nutzt die OpenAI-API, um Embeddings für die übergebenen
    Texte zu generieren. Sie benötigt eine gültige API-Schlüssel-Umgebung,
    die in `ENV_OPENAI_API_KEY` definiert ist. Das zu verwendende Modell
    kann optional über die Umgebungsvariable `ENV_OPENAI_EMBEDDING_MODEL`
    angepasst werden. Falls kein Modell spezifiziert ist, wird das
    Standardmodell `DEFAULT_OPENAI_EMBEDDING_MODEL` verwendet.

    :param texts: Die Liste der Texte, für die Embeddings berechnet
        werden sollen.
    :type texts: list[str]
    :return: Eine Liste von `numpy.ndarray`, die die berechneten Embeddings
        für die Eingabetexte enthalten.
    :rtype: list[np.ndarray]
    """
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv(ENV_OPENAI_API_KEY)
        if not api_key:
            raise ValueError(ERR_OPENAI_KEY_MISSING)
        _openai_client = OpenAI(api_key=api_key)

    model_name = (
        active_embedding_step_metadata(EMBEDDING_STEP_RETRIEVAL).get("embedding_model")
        or os.getenv(ENV_OPENAI_EMBEDDING_MODEL, DEFAULT_OPENAI_EMBEDDING_MODEL)
    )
    embeddings: list[np.ndarray] = []
    batch: list[str] = []
    batch_chars = 0

    def flush_batch() -> None:
        nonlocal batch, batch_chars

        if not batch:
            return

        response = _openai_client.embeddings.create(
            input=batch,
            model=model_name
        )
        embeddings.extend(np.array(item.embedding) for item in response.data)
        batch = []
        batch_chars = 0

    for text in texts:
        text_chars = len(text)
        batch_full_by_count = len(batch) >= OPENAI_EMBEDDING_MAX_BATCH_ITEMS
        batch_full_by_size = batch and batch_chars + text_chars > OPENAI_EMBEDDING_MAX_BATCH_CHARS

        if batch_full_by_count or batch_full_by_size:
            flush_batch()

        batch.append(text)
        batch_chars += text_chars

    flush_batch()

    return embeddings


def create_embedding(text: str) -> np.ndarray:
    """
    Erstellt einen numerischen Embedding-Vektor aus einem Eingabetext. Dieses Embedding kann für
    Downstream-Aufgaben wie Klassifikation, Information Retrieval oder andere Anwendungen verwendet werden.

    Die Funktion unterstützt mehrere Embedding-Anbieter, darunter OpenAI und ein lokales Modell.
    Falls der Eingabetext leer oder ungültig ist, wird ein Fallback-Text verwendet, dessen Länge und
    Qualität von der Konfiguration abhängen.

    :param text: Der Eingabetext, der zu einem Embedding verarbeitet werden soll.
    :type text: str
    :return: Ein numpy-Array, das den erzeugten Embedding-Vektor repräsentiert.
    :rtype: np.ndarray
    """
    if not text or not isinstance(text, str):
        # Fallback für leere oder ungültige Texte.
        # MiniLM-L6-v2 hat 384 Dimensionen.
        # OpenAI text-embedding-3-small hat 1536 Dimensionen.
        # Da hier nicht bekannt ist, welche Dimension erwartet wird,
        # läuft der Fehler ggf. später auf oder das Modell wird kurz geladen.
        text = FALLBACK_TEXT

    if _current_embedding_provider() in [PROVIDER_ONLINE, PROVIDER_OPENAI]:
        return _get_openai_embedding(text)
    else:
        # Standard: Lokales Modell
        model = _get_local_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return np.array(embedding)


def create_embeddings(texts: list[str]) -> list[np.ndarray]:
    """
    Erzeugt Embeddings für eine Liste von Texten.

    Diese Funktion erstellt Embeddings (numerische Darstellungen) für die
    übergebenen Textdaten basierend auf dem konfigurierten
    Embedding-Anbieter. Unterstützt werden sowohl Online-Anbieter
    (z. B. OpenAI) als auch lokale Modelle. Die Texte werden vor dem
    Erstellen der Embeddings normalisiert.

    :param texts: Eine Liste von Texten, die in Embeddings
        umgewandelt werden sollen.
    :type texts: list[str]

    :return: Eine Liste von Embeddings, wobei jedes Embedding durch
        einen `np.ndarray` repräsentiert wird.
    :rtype: list[np.ndarray]
    """
    normalized_texts = [
        _normalize_embedding_text(text)
        for text in texts
    ]

    if _current_embedding_provider() in [PROVIDER_ONLINE, PROVIDER_OPENAI]:
        return _get_openai_embeddings(normalized_texts)

    model = _get_local_model()
    embeddings = model.encode(normalized_texts, convert_to_numpy=True)
    return [
        np.array(embedding)
        for embedding in embeddings
    ]
