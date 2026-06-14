"""Quellengebundene Antwortgenerierung der Pipeline v3.

Das Modul erstellt Antwortentwürfe aus Retrieval-Kontext und ergänzt gegenüber
v2 robustere Fallbacks für unbeantwortbare oder sicherheitskritische Fälle.
"""

from prototype.shared.model_profiles import LLM_STEP_ANSWER_GENERATION
from src.core.llm_client import chat_text, current_llm_step_model
from src.v3.core import constants as c
from src.v3.core.prompt_templates import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_USER_PROMPT,
    CONTEXT_CHUNK_TEMPLATE,
)
from src.v3.core.response_messages import (
    MSG_BLOCKED_ANSWER,
    MSG_NO_ANSWER,
    MSG_NO_KNOWLEDGE_FOUND,
)


def generate_answer(inquiry_text: str, retrieved_chunks: list[dict]) -> dict:
    """
    Generiert eine Antwort basierend auf einer Anfrage (`inquiry_text`) und
    einem Satz an abgerufenen Datenstücken (`retrieved_chunks`). Falls keine
    Datenstücke vorliegen, wird eine Antwort ohne Inhalt erzeugt. Die 
    Quelldaten der verwendeten Datenstücke werden extrahiert und zurückgegeben.

    :param inquiry_text: Ein `str`, das den Text der Anfrage enthält, der 
        beantwortet werden soll.
    :param retrieved_chunks: Eine `list[dict]`, die die abgerufenen Datenstücke
        enthält. Jedes Stück repräsentiert einen Kontext mit Metadaten wie Quelle,
        Kategorie und Inhalt.
    :return: Ein `dict` mit den Schlüsseln:
        - `c.K_ANSWER`: Die generierte Antwort als `str`.
        - `c.K_SOURCES`: Eine `list` eindeutiger Quellennamen der verwendeten 
            Datenstücke.
        - `c.K_USED_CHUNKS`: Die ursprüngliche Liste der verwendeten 
            Datenstücke (`retrieved_chunks`).
    """
    if not retrieved_chunks:
        return {
            c.K_ANSWER: MSG_NO_KNOWLEDGE_FOUND,
            c.K_SOURCES: [],
            c.K_USED_CHUNKS: [],
        }

    context = c.SEP_NL2.join([
        CONTEXT_CHUNK_TEMPLATE.format(
            source=chunk[c.K_SOURCE],
            category=chunk.get(c.K_CATEGORY, c.V_UNKNOWN),
            content=chunk[c.K_CONTENT],
        )
        for chunk in retrieved_chunks
    ])

    prompt = ANSWER_USER_PROMPT.format(
        inquiry_text=inquiry_text,
        context=context,
    )

    provider, model, temperature = current_llm_step_model(LLM_STEP_ANSWER_GENERATION)
    answer = chat_text([
        {
            c.K_ROLE: c.ROLE_SYSTEM,
            c.K_CONTENT: ANSWER_SYSTEM_PROMPT,
        },
        {
            c.K_ROLE: c.ROLE_USER,
            c.K_CONTENT: prompt,
        },
    ], provider=provider, model=model, temperature=temperature)

    return {
        c.K_ANSWER: answer,
        c.K_SOURCES: list({chunk[c.K_SOURCE] for chunk in retrieved_chunks}),
        c.K_USED_CHUNKS: retrieved_chunks,
    }


def generate_no_answer():
    return {
        c.K_ANSWER: MSG_NO_ANSWER,
        c.K_SOURCES: [],
        c.K_USED_CHUNKS: [],
    }


def generate_blocked_answer():
    return {
        c.K_ANSWER: MSG_BLOCKED_ANSWER,
        c.K_SOURCES: [],
        c.K_USED_CHUNKS: [],
    }
