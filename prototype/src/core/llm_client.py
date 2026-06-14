"""Gemeinsamer LLM-Client für Ollama- und OpenAI-Aufrufe.

Die Funktionen kapseln Provider-Auswahl, JSON-Antworten und
Modellprofil-Metadaten, damit die Pipeline-Versionen ein einheitliches
Aufrufverhalten nutzen.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv

from prototype.shared.constants import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_OPENAI_MODEL,
    ENV_LLM_PROVIDER,
    ENV_OLLAMA_MODEL,
    ENV_OLLAMA_REQUEST_TIMEOUT_SECONDS,
    ENV_OPENAI_API_KEY,
    ENV_OPENAI_MODEL,
    ENV_TEMPERATURE,
    LLM_PROVIDER_OLLAMA,
    LLM_PROVIDER_OPENAI,
)
from prototype.shared.logging_config import get_logger
from prototype.shared.model_profiles import (
    active_llm_step_metadata,
    active_model_metadata,
)
from prototype.shared.paths import ENV_PATH

load_dotenv(ENV_PATH)

logger = get_logger(__name__)

LLM_PROVIDER = os.getenv(ENV_LLM_PROVIDER, DEFAULT_LLM_PROVIDER).strip().lower()
OLLAMA_MODEL = os.getenv(ENV_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL).strip()
OPENAI_MODEL = os.getenv(ENV_OPENAI_MODEL, DEFAULT_OPENAI_MODEL).strip()

_openai_client = None


def _get_temperature() -> float:
    """
    Liest die konfigurierte Temperatur aus einer Umgebungsvariablen und gibt
    diese als `float` zurück. Falls die konfigurierte Temperatur kein gültiger
    `float`-Wert ist, wird ein `ValueError` ausgelöst.

    Die Temperatur kann z. B. für die Steuerung der Kreativität in generativen
    KI-Modellen verwendet werden.

    :return: Die konfigurierte Temperatur als `float`.
    :rtype: float
    :raises ValueError: Wenn der Wert der Umgebungsvariablen für die Temperatur
        kein gültiger `float`-Wert ist.
    """
    configured_temperature = active_model_metadata().get(
        "temperature",
        os.getenv(ENV_TEMPERATURE, DEFAULT_LLM_TEMPERATURE),
    )

    try:
        return float(configured_temperature)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Ungültiger Wert für {ENV_TEMPERATURE}: {configured_temperature!r}"
        ) from exc


def _current_llm_provider(provider: str | None = None) -> str:
    if provider:
        return provider.strip().lower()

    return (
        active_model_metadata().get("llm_provider")
        or os.getenv(ENV_LLM_PROVIDER, DEFAULT_LLM_PROVIDER)
    ).strip().lower()


def _current_llm_model(provider: str | None = None, model: str | None = None) -> str:
    if model:
        return model.strip()

    current_provider = _current_llm_provider(provider)
    metadata = active_model_metadata()
    if metadata.get("llm_provider") == current_provider and metadata.get("llm_model"):
        return metadata["llm_model"].strip()

    if current_provider == LLM_PROVIDER_OPENAI:
        return os.getenv(ENV_OPENAI_MODEL, DEFAULT_OPENAI_MODEL).strip()

    if current_provider == LLM_PROVIDER_OLLAMA:
        return os.getenv(ENV_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL).strip()

    return ""


def current_llm_step_model(step_name: str) -> tuple[str, str, float]:
    metadata = active_llm_step_metadata(step_name)
    provider = metadata.get("llm_provider", DEFAULT_LLM_PROVIDER).strip().lower()
    model = metadata.get("llm_model", "").strip()
    temperature = metadata.get("temperature", DEFAULT_LLM_TEMPERATURE)

    try:
        parsed_temperature = float(temperature)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Ungueltiger Temperatur-Wert fuer LLM-Schritt {step_name!r}: {temperature!r}"
        ) from exc

    return provider, model, parsed_temperature



def get_llm_metadata() -> dict[str, str]:
    provider = _current_llm_provider()
    metadata = active_model_metadata()
    return {
        "llm_provider": provider,
        "llm_model": _current_llm_model(provider),
        "temperature": metadata.get(
            "temperature",
            os.getenv(ENV_TEMPERATURE, DEFAULT_LLM_TEMPERATURE),
        ).strip(),
    }


def chat_json(
        messages: list[dict[str, str]],
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
) -> dict[str, Any]:
    """
    Verarbeitet eine Liste von Nachrichten und ruft die entsprechende
    Verarbeitungsmethode basierend auf dem angegebenen Large Language Model (LLM)
    auf. Unterstützt wird aktuell entweder `OLLAMA` oder `OPENAI` als Anbieter.

    :param messages: Die Eingabedaten, eine Liste von Wörterbüchern, wobei jede
        Nachricht als Wörterbuch mit Schlüssel-Wert-Paaren repräsentiert ist.
        Die Struktur jedes Wörterbuchs muss mit den Anforderungen der
        spezifischen LLM-Verarbeitungsmethode übereinstimmen.
    :return: Ein Wörterbuch, das die Antwort des jeweiligen LLM-Anbieters
        enthält. Die genaue Struktur hängt vom verwendeten Anbieter ab.
    """
    current_provider = _current_llm_provider(provider)
    current_model = _current_llm_model(current_provider, model)

    if current_provider == LLM_PROVIDER_OLLAMA:
        return _chat_json_ollama(messages, current_model, temperature)

    if current_provider == LLM_PROVIDER_OPENAI:
        return _chat_json_openai(messages, current_model, temperature)

    raise ValueError(f"Unbekannter LLM_PROVIDER: {current_provider}")


def chat_text(
        messages: list[dict[str, str]],
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
) -> str:
    """
    Ruft die passende Textgenerierungsfunktion basierend auf dem aktuellen Wert
    des Konstanten `LLM_PROVIDER` auf. Unterstützt derzeit die Anbieter
    OLLAMA und OpenAI.

    :param messages: Eine Liste von Nachrichten, wobei jede Nachricht durch
        ein Wörterbuch repräsentiert wird, das Informationen wie Text und
        Absender enthält. Der Schlüssel entspricht dem Typ `str`, und die
        Werte sind ebenfalls vom Typ `str`.
    :return: Der generierte Text als eine Zeichenkette, entsprechend der
        Verarbeitung durch den spezifischen Anbieter.
    """
    current_provider = _current_llm_provider(provider)
    current_model = _current_llm_model(current_provider, model)

    if current_provider == LLM_PROVIDER_OLLAMA:
        return _chat_text_ollama(messages, current_model, temperature)

    if current_provider == LLM_PROVIDER_OPENAI:
        return _chat_text_openai(messages, current_model, temperature)

    raise ValueError(f"Unbekannter LLM_PROVIDER: {current_provider}")


def _parse_json_response(content: str) -> dict[str, Any]:
    """
    Parst eine JSON-Response und überprüft, ob diese ein JSON-Objekt des Typs `dict` ist.

    Diese Funktion nimmt eine JSON-kodierte Zeichenkette entgegen, dekodiert sie und stellt
    sicher, dass das Ergebnis ein `dict` ist, bevor es zurückgegeben wird. Wenn das Parsing
    fehlschlägt oder das Ergebnis kein `dict` ist, wird eine entsprechende Fehlermeldung ausgegeben.

    :param content: Die JSON-kodierte Zeichenkette, die geparst werden soll.
    :return: Das geparste JSON-Objekt als `dict[str, Any]`.
    """
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM-Antwort konnte nicht als JSON geparst werden.") from exc

    if not isinstance(result, dict):
        raise ValueError("LLM-JSON-Antwort muss ein Objekt sein.")

    return result


def _get_openai_client():
    """
    Erstellt und liefert eine Instanz des OpenAI-Clients. Diese Funktion überprüft, ob der
    Client bereits initialisiert wurde, und gibt in diesem Fall den existierenden Client
    zurück. Falls der Client noch nicht initialisiert wurde, wird ein neuer Client mit
    einem API-Schlüssel aus der Umgebungsvariable erstellt und initialisiert.

    Wenn die Umgebungsvariable für den API-Schlüssel (`ENV_OPENAI_API_KEY`) nicht gesetzt
    ist, wird eine Ausnahme ausgelöst.

    :raise RuntimeError: Falls die Umgebungsvariable `ENV_OPENAI_API_KEY` nicht gesetzt ist.
    :return: Eine Instanz des OpenAI-Clients.
    """
    global _openai_client

    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv(ENV_OPENAI_API_KEY)
    if not api_key:
        raise RuntimeError(f"{ENV_OPENAI_API_KEY} ist nicht gesetzt.")

    from openai import OpenAI

    _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_ollama_timeout_seconds() -> float:
    configured_timeout = os.getenv(
        ENV_OLLAMA_REQUEST_TIMEOUT_SECONDS,
        DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS,
    )

    try:
        timeout_seconds = float(configured_timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Ungültiger Wert für {ENV_OLLAMA_REQUEST_TIMEOUT_SECONDS}: "
            f"{configured_timeout!r}"
        ) from exc

    if timeout_seconds <= 0:
        raise ValueError(
            f"{ENV_OLLAMA_REQUEST_TIMEOUT_SECONDS} muss größer als 0 sein."
        )

    return timeout_seconds


def _build_ollama_client():
    import ollama

    return ollama.Client(timeout=_get_ollama_timeout_seconds())


def _resolve_temperature(temperature: float | None = None) -> float:
    return _get_temperature() if temperature is None else temperature


def _chat_json_ollama(
        messages: list[dict[str, str]],
        model: str,
        temperature: float | None = None,
) -> dict[str, Any]:
    """
    Diese Funktion führt einen LLM-Aufruf durch und verarbeitet die Antwort als JSON.

    Die Funktion verwendet die `ollama`-Bibliothek, um Nachrichten an ein in `OLLAMA_MODEL`
    spezifiziertes Modell zu senden. Der Funktionsaufruf generiert eine Antwort im JSON-Format.
    Die Antwort wird anschließend durch `_parse_json_response` weiterverarbeitet, bevor sie
    zurückgegeben wird. Zusätzlich werden relevante Ereignisse protokolliert, um die Nachvollziehbarkeit
    sicherzustellen.

    :param messages: Eine Liste von Nachrichten, die an das LLM-Modell gesendet werden. Jede Nachricht
        ist als ein Wörterbuch mit `str`-Typ-Schlüsseln und Werten zu strukturieren.
    :return: Ein Wörterbuch, welches die verarbeitete Antwort des LLM-Modells enthält.
    """
    logger.info(
        "LLM-Aufruf gestartet: provider=%s, model=%s, format=json, timeout=%ss",
        LLM_PROVIDER_OLLAMA,
        model,
        _get_ollama_timeout_seconds(),
    )

    response = _build_ollama_client().chat(
        model=model,
        messages=messages,
        format="json",
        options={
            "temperature": _resolve_temperature(temperature)
        }
    )

    content = response["message"]["content"]

    result = _parse_json_response(content)
    logger.info(
        "LLM-Aufruf abgeschlossen: provider=%s, model=%s, format=json",
        LLM_PROVIDER_OLLAMA,
        model,
    )
    return result


def _chat_text_ollama(
        messages: list[dict[str, str]],
        model: str,
        temperature: float | None = None,
) -> str:
    """
    Ruft das spezifizierte Large Language Model (LLM) von Ollama mit den bereitgestellten
    Nachrichten auf und gibt die generierte Antwort zurück.

    Der Funktionsaufruf wird zweifach protokolliert: Vor Beginn des LLM-Aufrufs und nach
    dessen Abschluss. Dabei werden der Anbieter, das Modell und das Ausgabeformat dokumentiert.

    :param messages: Eine Liste von Nachrichten, welche an das LLM übergeben werden. Jede
        Nachricht ist ein Dictionary mit Schlüssel-Wert-Paaren, die die Struktur und den
        Inhalt der Nachrichten definieren.
    :return: Die vom LLM generierte Antwort als `str`, die unter dem Schlüssel
        `"message"]["content"` des Rückgabeobjekts zu finden ist.
    """
    logger.info(
        "LLM-Aufruf gestartet: provider=%s, model=%s, format=text, timeout=%ss",
        LLM_PROVIDER_OLLAMA,
        model,
        _get_ollama_timeout_seconds(),
    )

    response = _build_ollama_client().chat(
        model=model,
        messages=messages,
        options={
            "temperature": _resolve_temperature(temperature)
        }
    )

    logger.info(
        "LLM-Aufruf abgeschlossen: provider=%s, model=%s, format=text",
        LLM_PROVIDER_OLLAMA,
        model,
    )
    return response["message"]["content"]


def _chat_text_openai(
        messages: list[dict[str, str]],
        model: str,
        temperature: float | None = None,
) -> str:
    """
    Erzeugt einen Text basierend auf einer Unterhaltung, die durch `messages` repräsentiert wird.
    Die Funktion verwendet ein Large Language Model (LLM) von OpenAI, um eine Antwort auf die
    gegebenen Eingaben zu generieren.

    :param messages: Liste von Nachrichten, die jeweils durch ein Wörterbuch mit den Schlüsseln
        "role" (z. B. "user" oder "assistant") und "content" (Nachrichteninhalt) repräsentiert werden.
    :type messages: list[dict[str, str]]
    :return: Generierter Textinhalt als Antwort des LLM.
    :rtype: str
    """
    client = _get_openai_client()

    logger.info(
        "LLM-Aufruf gestartet: provider=%s, model=%s, format=text",
        LLM_PROVIDER_OPENAI,
        model,
    )

    response = client.chat.completions.create(
        model=model,
        temperature=_resolve_temperature(temperature),
        messages=messages
    )

    logger.info(
        "LLM-Aufruf abgeschlossen: provider=%s, model=%s, format=text",
        LLM_PROVIDER_OPENAI,
        model,
    )
    return response.choices[0].message.content


def _chat_json_openai(
        messages: list[dict[str, str]],
        model: str,
        temperature: float | None = None,
) -> dict[str, Any]:
    """
    Führt einen LLM-Aufruf durch, indem spezifische Nachrichten (`messages`)
    an das OpenAI-Modell gesendet werden. Die Kommunikation wird in JSON-Format
    durchgeführt, wobei die Resultate geparst und zurückgegeben werden.

    :param messages:
        Eine Liste von Nachrichten, die an das LLM gesendet werden. Jede Nachricht
        enthält Schlüssel-Wert-Paare, die Inhalte wie Rollen oder Inhalte
        definieren.
    :return:
        Ein geparstes JSON-Objekt, das die Antwort des LLM repräsentiert.
    """
    client = _get_openai_client()

    logger.info(
        "LLM-Aufruf gestartet: provider=%s, model=%s, format=json",
        LLM_PROVIDER_OPENAI,
        model,
    )

    response = client.chat.completions.create(
        model=model,
        temperature=_resolve_temperature(temperature),
        response_format={"type": "json_object"},
        messages=messages
    )

    result = _parse_json_response(response.choices[0].message.content)
    logger.info(
        "LLM-Aufruf abgeschlossen: provider=%s, model=%s, format=json",
        LLM_PROVIDER_OPENAI,
        model,
    )
    return result
