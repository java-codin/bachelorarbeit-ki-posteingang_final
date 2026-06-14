"""Antwortgenerierung der Pipeline v4.

Das Modul erzeugt quellengebundene Entwürfe und stellt zusätzlich strukturierte
Quelleninformationen für Risiko-, Policy- und Workflow-Bewertungen bereit.
"""

from typing import Any

from prototype.shared.model_profiles import LLM_STEP_ANSWER_GENERATION
from src.core.llm_client import chat_text, current_llm_step_model
from src.v4.core.constants import (
    K_ANSWER,
    K_CATEGORY,
    K_CONTENT,
    K_ROLE,
    K_SOURCE,
    K_SOURCES,
    K_USED_CHUNKS,
    ROLE_SYSTEM,
    ROLE_USER,
    V_UNKNOWN, SEP_NL2,
)
from src.v4.core.prompt_templates import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_USER_PROMPT,
    CONTEXT_CHUNK_TEMPLATE,
)
from src.v4.core.response_messages import (
    MSG_BLOCKED_ANSWER,
    MSG_NO_ANSWER,
    MSG_NO_KNOWLEDGE_FOUND,
)


def generate_answer(inquiry_text: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generiert eine Antwort basierend auf der Anfrage und den bereitgestellten
    Informationen, die aus den `retrieved_chunks` extrahiert wurden. Die Antwort enthält
    die generierte Antwort, eine Liste verwendeter Quellen und die genutzten Chunks.
    Falls keine `retrieved_chunks` verfügbar sind, wird eine Standardantwort
    zurückgegeben, die anzeigt, dass keine relevanten Informationen gefunden wurden.

    :param inquiry_text: Die Benutzeranfrage, die verarbeitet werden soll.
    :param retrieved_chunks: Eine Liste von Chunks, die relevante Informationen zur
        Anfrage enthalten. Jeder Chunk ist ein `dict` mit Details wie Quelle,
        Kategorie und Inhalt.
    :return: Ein `dict` mit den Schlüsseln:
        - `K_ANSWER`: Die generierte Antwort als Text.
        - `K_SOURCES`: Eine Liste eindeutiger Quellen (`str`), die zur Erstellung
          der Antwort verwendet wurden.
        - `K_USED_CHUNKS`: Eine Liste der Chunks, die tatsächlich verwendet wurden,
          um den Kontext für die Antwort zu erstellen.
    """
    if not retrieved_chunks:
        return {
            K_ANSWER: MSG_NO_KNOWLEDGE_FOUND,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    context = SEP_NL2.join([
        CONTEXT_CHUNK_TEMPLATE.format(
            source=chunk[K_SOURCE],
            category=chunk.get(K_CATEGORY, V_UNKNOWN),
            content=chunk[K_CONTENT]
        )
        for chunk in retrieved_chunks
    ])

    prompt = ANSWER_USER_PROMPT.format(
        inquiry_text=inquiry_text,
        context=context
    )

    provider, model, temperature = current_llm_step_model(LLM_STEP_ANSWER_GENERATION)
    answer = chat_text([
        {
            K_ROLE: ROLE_SYSTEM,
            K_CONTENT: ANSWER_SYSTEM_PROMPT
        },
        {
            K_ROLE: ROLE_USER,
            K_CONTENT: prompt
        }
    ], provider=provider, model=model, temperature=temperature)

    return {
        K_ANSWER: answer,
        K_SOURCES: list({chunk[K_SOURCE] for chunk in retrieved_chunks}),
        K_USED_CHUNKS: retrieved_chunks
    }


def generate_no_answer() -> dict[str, Any]:
    """
    Generiert eine Standardantwort für Fälle, in denen keine Antwort gefunden wurde.

    Diese Funktion erstellt und gibt ein `dict[str, Any]` zurück, das eine vordefinierte
    Nachricht unter Verwendung des Schlüssels `K_ANSWER` sowie leere Listen für die
    zugeordneten Quellen (`K_SOURCES`) und verwendeten Textabschnitte (`K_USED_CHUNKS`) enthält.
    Die Rückgabewerte sind für die weitere Verarbeitung oder Protokollierung gedacht.

    :rtype: dict[str, Any]
    :return: Ein Wörterbuch mit den folgenden Schlüsseln:
        - `K_ANSWER`: Beinhaltet die vordefinierte Nachricht `MSG_NO_ANSWER`.
        - `K_SOURCES`: Eine leere Liste, da keine Quellen gefunden wurden.
        - `K_USED_CHUNKS`: Eine leere Liste, da keine Textabschnitte verwendet wurden.
    """
    return {
        K_ANSWER: MSG_NO_ANSWER,
        K_SOURCES: [],
        K_USED_CHUNKS: []
    }


def generate_blocked_answer() -> dict[str, Any]:
    """
    Erzeugt eine blockierte Antwort mit leeren Quellen und benutzten Chunks.

    Diese Funktion generiert eine standardisierte Antwortstruktur zur Verwendung
    bei blockierten Anfragen. Die Antwort besteht aus einem festen Nachrichtentext,
    sowie leeren Listen für die Felder `K_SOURCES` und `K_USED_CHUNKS`.

    :return: Ein `dict` mit den Schlüsseln `K_ANSWER`, `K_SOURCES` und `K_USED_CHUNKS`.
             Der Wert von `K_ANSWER` ist die blockierte Nachricht, während die anderen
             beiden Listen leer sind.
    :rtype: dict[str, Any]
    """
    return {
        K_ANSWER: MSG_BLOCKED_ANSWER,
        K_SOURCES: [],
        K_USED_CHUNKS: []
    }
