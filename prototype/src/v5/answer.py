"""Antwortgenerierung und finale Textaufbereitung der Pipeline v5.

Das Modul erzeugt quellengebundene Antwortentwürfe, entfernt technische
Quellenmarker aus dem Bürgertext und ergänzt nur erlaubte Postprocessing-
Bestandteile wie Signatur und konfigurierte Hinweise.
"""

import json
import re
from typing import Any, List

from prototype.shared.model_profiles import LLM_STEP_ANSWER_GENERATION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v5.source_extraction import attach_source_ids, resolve_used_sources
from src.v5.core.prompt_templates import ANSWER_GENERATION_SYSTEM_PROMPT, ANSWER_GENERATION_USER_PROMPT
from src.v5.core.response_messages import (
    MSG_NO_KNOWLEDGE_FOUND,
    CONTEXT_CHUNK_TEMPLATE, MSG_TECHNICAL_ERROR
)
from src.v5.core.constants import (
    K_ANSWER, K_SOURCES, K_USED_CHUNKS, K_SOURCE, K_CONTENT, K_CATEGORY,
    K_ROLE, K_CONTENT_MSG,
    V_UNKNOWN, ROLE_SYSTEM, ROLE_USER, SEP_NL2,
    K_USED_SOURCES, K_INVALID_SOURCE_IDS, K_USED_SOURCE_IDS, K_SOURCE_ID
)


SOURCE_MARKER_PATTERN = re.compile(r"\s*\[(S\d+)\]")
EXCESSIVE_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")
EXCESSIVE_BULLET_SPACING_PATTERN = re.compile(r"(?m)^(- .+)\n\n(?=- )")

def normalize_answer_text(answer: str) -> str:
    """
    Vereinheitlicht die Textform eines Antwortentwurfs, ohne fachliche Inhalte zu
    verändern. Die Ausgabe soll als editierbarer E-Mail-Text und in HTML-Preview
    gleichermaßen lesbar bleiben.
    """
    text = str(answer or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not text:
        return ""

    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines).strip()
    text = EXCESSIVE_BLANK_LINES_PATTERN.sub(SEP_NL2, text)
    text = re.sub(r"\n{3,}", SEP_NL2, text)
    text = EXCESSIVE_BULLET_SPACING_PATTERN.sub(r"\1\n", text)

    return text.strip()


def coerce_answer_text(answer: Any) -> str:
    """
    Führt uneinheitliche LLM-Antwortformen auf den erwarteten Antworttext zurück.

    Lokale Modelle liefern trotz JSON-Anweisung gelegentlich ein Objekt im Feld
    `answer`. Für die Pipeline ist ein stabiler Textvertrag wichtiger als ein
    Abbruch des gesamten Experiments.
    """
    if isinstance(answer, str):
        return answer

    if answer is None:
        return ""

    if isinstance(answer, dict):
        for key in (K_ANSWER, "draft_answer", "text", "content", "message", "response", "body"):
            value = answer.get(key)
            if value:
                return coerce_answer_text(value)

        return json.dumps(answer, ensure_ascii=False)

    if isinstance(answer, list):
        return "\n".join(
            text for item in answer
            if (text := coerce_answer_text(item))
        )

    return str(answer)


def strip_inline_source_markers(answer: Any) -> str:
    """
    Entfernt interne Quellenmarker aus dem Bürgertext.

    Die Quellenbindung bleibt über used_source_ids und used_chunks erhalten. Der
    Antwortentwurf selbst soll dadurch wie ein lesbares Verwaltungsschreiben
    wirken und keine technischen RAG-Marker enthalten.
    """
    answer_text = coerce_answer_text(answer)
    return normalize_answer_text(SOURCE_MARKER_PATTERN.sub("", answer_text))


def append_official_closing(
        answer: str,
        team_name: str | None = None,
        subteam_name: str | None = None,
        application_notice: str | None = None
) -> str:
    """
    Fügt einem Antwort-Text eine abschließende Grußformel sowie eine Angabe zur
    Fachabteilung hinzu. Der abschließende Text wird an den bereits bestehenden
    Antwort-Text angefügt und ersetzt keine bestehenden Absätze.

    Falls kein Name der Fachabteilung angegeben wurde, wird ein Platzhalter
    `"[Name der Fachabteilung]"` verwendet.

    :param answer: Der ursprüngliche Antwort-Text, an den die Grußformel
        angefügt werden soll.
    :type answer: str
    :param team_name: Optionaler Name der Fachabteilung, die in der Grußformel
        erscheinen soll. Falls nicht angegeben, wird ein Platzhalter verwendet.
    :type team_name: str | None
    :param subteam_name: Optionaler Name des zuständigen Subteams. Falls angegeben,
        wird es unterhalb der Fachabteilung in der Signatur ergänzt.
    :type subteam_name: str | None
    :return: Der vollständige Antwort-Text inklusive der angefügten Grußformel.
    :rtype: str
    """
    department_name = team_name or "[Name der Fachabteilung]"
    signature_lines = [
        "[Name der Sachbearbeitung]",
        department_name,
    ]

    if subteam_name and subteam_name != department_name:
        signature_lines.append(subteam_name)
    signature_text = "\n".join(signature_lines)

    closing = (
        "\n\nMit freundlichen Grüßen\n\n"
        f"{signature_text}\n\n"
    )

    application_notice = normalize_answer_text(application_notice or "")
    if application_notice:
        closing = f"{closing}\n\n{application_notice}"

    answer = normalize_answer_text(answer)

    if not answer:
        return closing.strip()

    return answer + closing


def generate_answer(
        inquiry_text: str,
        retrieved_chunks: List[dict[str, Any]],
        team_role: str | None = None,
) -> dict[str, Any]:
    """
    Generiert eine Antwort basierend auf der Anfrage und den bereitgestellten Chunks.

    Diese Funktion nimmt eine Anfrage (`inquiry_text`) und eine Liste von
    `retrieved_chunks` entgegen und generiert basierend auf den bereitgestellten
    Informationen eine Antwort. Falls keine Chunks bereitgestellt werden, wird eine
    Standardantwort zurückgegeben, die darauf hinweist, dass keine Informationen
    gefunden wurden. Wenn Chunks zur Verfügung stehen, werden diese verarbeitet,
    um eine kontextuelle Antwort zu erstellen. Zu den Rückgabewerten gehören die
    generierte Antwort, die verwendeten Quellinformationen sowie Metadaten über
    verwendete und ungültige Quell-IDs.

    :param inquiry_text: Der Benutzertext, auf dem die Antwort basieren soll.
    :param retrieved_chunks: Eine Liste von Wissens-Chunks, die aus einer Quelle
        abgerufen wurden, dargestellt als Liste von Wörterbüchern.
        Jedes Wörterbuch enthält unter anderem Informationen über den Inhalt,
        die Quelle und eine Quell-ID.
    :return: Ein Wörterbuch mit der generierten Antwort, den relevanten Quellen,
        verwendeten und ungültigen Quell-IDs, sowie den verwendeten Chunks.
    """
    if not retrieved_chunks:
        return {
            K_ANSWER: MSG_NO_KNOWLEDGE_FOUND,
            K_SOURCES: [],
            K_USED_SOURCES: [],
            K_USED_CHUNKS: [],
            K_USED_SOURCE_IDS: [],
            K_INVALID_SOURCE_IDS: []
        }

    chunks_with_ids = attach_source_ids(retrieved_chunks)

    context = SEP_NL2.join([
        CONTEXT_CHUNK_TEMPLATE.format(
            source=chunk[K_SOURCE],
            category=chunk.get(K_CATEGORY, V_UNKNOWN),
            content=f"Quellen-ID: {chunk[K_SOURCE_ID]}\n{chunk[K_CONTENT]}"
        )
        for chunk in chunks_with_ids
    ])

    user_prompt = ANSWER_GENERATION_USER_PROMPT.format(
        inquiry_text=inquiry_text,
        context=context,
        team_role=team_role or (
            "Antworte als sachbearbeitende Person des zuständigen kommunalen "
            "Fachbereichs. Bleibe bei der fachlichen Rolle des zugeordneten "
            "Teams und übernimm keine Aufgaben anderer Fachbereiche."
        ),
    )

    try:
        answer_provider, answer_model, answer_temperature = current_llm_step_model(
            LLM_STEP_ANSWER_GENERATION
        )
        raw_result = chat_json([
            {
                K_ROLE: ROLE_SYSTEM,
                K_CONTENT_MSG: ANSWER_GENERATION_SYSTEM_PROMPT
            },
            {
                K_ROLE: ROLE_USER,
                K_CONTENT_MSG: user_prompt
            }
        ], provider=answer_provider, model=answer_model, temperature=answer_temperature)
    except Exception:
        return {
            K_ANSWER: (
                MSG_TECHNICAL_ERROR
            ),
            K_SOURCES: [],
            K_USED_SOURCES: [],
            K_USED_CHUNKS: [],
            K_USED_SOURCE_IDS: [],
            K_INVALID_SOURCE_IDS: []
        }

    answer = strip_inline_source_markers(raw_result.get(K_ANSWER, ""))
    used_source_ids = raw_result.get(K_USED_SOURCE_IDS, [])

    if not isinstance(used_source_ids, list):
        used_source_ids = []

    resolved = resolve_used_sources(
        used_source_ids=used_source_ids,
        retrieved_chunks=chunks_with_ids
    )

    return {
        K_ANSWER: answer,
        K_SOURCES: resolved[K_USED_SOURCES],
        K_USED_SOURCES: resolved[K_USED_SOURCES],
        K_USED_CHUNKS: resolved[K_USED_CHUNKS],
        K_USED_SOURCE_IDS: resolved[K_USED_SOURCE_IDS],
        K_INVALID_SOURCE_IDS: resolved[K_INVALID_SOURCE_IDS]
    }
