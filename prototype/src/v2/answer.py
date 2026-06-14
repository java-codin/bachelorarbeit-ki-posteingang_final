"""RAG-basierte Antwortgenerierung der Pipeline v2.

Das Modul erstellt Antwortentwürfe aus abgerufenen Wissensbasis-Chunks und
kennzeichnet verwendete Quellen für die spätere Evaluation.
"""

from prototype.shared.model_profiles import LLM_STEP_ANSWER_GENERATION
from src.core.llm_client import chat_text, current_llm_step_model
from src.v2.core import constants as c
from src.v2.core.prompt_templates import ANSWER_SYSTEM_PROMPT, ANSWER_USER_PROMPT, CONTEXT_CHUNK_TEMPLATE
from src.v2.core.response_messages import MSG_NO_KNOWLEDGE_FOUND


def generate_answer(inquiry_text, retrieved_chunks):
    """
    Generiert eine Antwort auf die gegebene Anfrage basierend auf abgerufenen Informationseinheiten.
    Falls keine abgerufenen Informationseinheiten vorhanden sind, wird eine vordefinierte Rückmeldung
    ohne Antwortinhalte zurückgegeben. Andernfalls wird ein Antworttext durch Kontextaufbereitung
    und Interaktion mit einem Chatmodell erstellt. Die Methode liefert zusätzlich auch verwendete
    Quellen und genutzte Informationseinheiten zurück.

    :param inquiry_text: Der Text der Anfrage, für die eine Antwort generiert werden soll.
    :type inquiry_text: str
    :param retrieved_chunks: Eine Liste von abgerufenen Informationseinheiten, die als Kontext
        für die Antwortgenerierung verwendet werden.
    :type retrieved_chunks: list[dict]
    :return: Ein Wörterbuch mit folgenden Schlüsseln:
        - c.K_ANSWER: Die generierte Antwort als Text.
        - c.K_SOURCES: Eine Liste von eindeutigen Quellen, die in den abgerufenen Informationseinheiten
          enthalten sind.
        - c.K_USED_CHUNKS: Eine Liste der verwendeten Informationseinheiten, die für die Kontextgenerierung
          genutzt wurden.
    :rtype: dict
    """
    if not retrieved_chunks:
        return {
            c.K_ANSWER: MSG_NO_KNOWLEDGE_FOUND,
            c.K_SOURCES: [],
            c.K_USED_CHUNKS: [],
        }

    context = c.SEP_NL2.join([
        CONTEXT_CHUNK_TEMPLATE.format(
            index=index,
            source=chunk[c.K_SOURCE],
            category=chunk.get(c.K_CATEGORY, c.V_UNKNOWN),
            content=chunk[c.K_CONTENT],
        )
        for index, chunk in enumerate(retrieved_chunks, start=1)
    ])

    prompt = ANSWER_USER_PROMPT.format(
        inquiry_text=inquiry_text,
        context=context,
    )

    provider, model, temperature = current_llm_step_model(LLM_STEP_ANSWER_GENERATION)
    answer = chat_text([
        {c.K_ROLE: c.ROLE_SYSTEM, c.K_CONTENT: ANSWER_SYSTEM_PROMPT},
        {c.K_ROLE: c.ROLE_USER, c.K_CONTENT: prompt},
    ], provider=provider, model=model, temperature=temperature)

    return {
        c.K_ANSWER: answer,
        c.K_SOURCES: list({chunk[c.K_SOURCE] for chunk in retrieved_chunks}),
        c.K_USED_CHUNKS: retrieved_chunks,
    }
