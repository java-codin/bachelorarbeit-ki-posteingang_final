"""Vollständigkeitsbewertung für Antwortentwürfe der Pipeline v5.

Das Modul prüft mit einem separaten Bewertungsschritt, ob ein Antwortentwurf die
wesentlichen Anliegenaspekte abdeckt und ob menschliche Nachbearbeitung nötig ist.
"""

from typing import Union, Any

from prototype.shared.model_profiles import LLM_STEP_ANSWER_COMPLETENESS, active_llm_step_metadata
from src.core.llm_client import chat_json, current_llm_step_model
from src.v5.core.prompt_templates import ANSWER_COMPLETENESS_SYSTEM_PROMPT, ANSWER_COMPLETENESS_USER_PROMPT
from src.v5.core.constants import (
    K_COMPLETENESS_SCORE, K_COMPLETENESS_LABEL, K_COMPLETENESS_REASON,
    K_COVERED_ASPECTS, K_MISSING_ASPECTS, K_UNCERTAIN_ASPECTS, K_HUMAN_REQUIRED,
    K_INJECTION_DETECTED, K_INJECTION_REASONING, K_RESPONSE_MODE, K_NO_ANSWER_TRIGGERED,
    K_SOURCE, K_CONTENT, K_CATEGORY,
    K_ROLE, K_CONTENT_MSG,
    V_UNKNOWN, ROLE_SYSTEM, ROLE_USER,
    LABEL_HIGH, LABEL_MEDIUM, LABEL_LOW, LABEL_NONE,
    MODE_BLOCKED, MODE_ESCALATION, MODE_NO_ANSWER,
    SEP_DASHES_EXT, ANSWER_COMPLETENESS_REVIEW_THRESHOLD,
    ANSWER_COMPLETENESS_HIGH_THRESHOLD, ANSWER_COMPLETENESS_MEDIUM_THRESHOLD,
    ANSWER_COMPLETENESS_MIN_SCORE, ANSWER_COMPLETENESS_MAX_SCORE
)
from src.v5.core.response_messages import (
    DEFAULT_NO_REASON,
    EVAL_REASON_INJECTION,
    EVAL_REASON_INJECTION_DETAILS,
    EVAL_REASON_BLOCKED,
    EVAL_REASON_NO_ANSWER,
    EVAL_REASON_NO_DRAFT,
    EVAL_REASON_EXCEPTION,
    EVAL_REASON_POLICY_ANSWER,
    SOURCE_CONTEXT_TEMPLATE, SOURCE_LIST_HEADER, SOURCE_LIST_ITEM, SOURCE_CONTEXT_EMPTY
)


def clamp_score(value: Union[int, float, str, None]) -> float:
    """
    Konvertiert einen Eingabewert zu einem Float und begrenzt ihn auf einen definierten Wertebereich.

    Diese Funktion versucht, den Eingabewert in einen `float`-Wert zu konvertieren.
    Falls der Eingabewert ungültig oder nicht konvertierbar ist, wird ein Minimalwert
    zurückgegeben. Eingabewerte, die außerhalb des erlaubten Bereichs liegen, werden
    auf den Minimal- bzw. Maximalwert begrenzt.

    :param value: Der Eingabewert, der in einen `float` konvertiert werden soll. Es kann
        sich dabei um einen numerischen Wert (`int` oder `float`), eine Zeichenkette (`str`),
        oder `None` handeln.
    :return: Ein `float`-Wert, der entweder der konvertierte Wert ist oder auf den minimalen
        bzw. maximalen Bereichswert begrenzt wurde.
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ANSWER_COMPLETENESS_MIN_SCORE

    return max(ANSWER_COMPLETENESS_MIN_SCORE, min(ANSWER_COMPLETENESS_MAX_SCORE, score))


def label_from_score(score: float) -> str:
    """
    Bestimmt ein Label basierend auf einem numerischen Score.

    Diese Funktion ordnet einem numerischen `score` ein Label zu, das dessen
    Qualitätsbewertung oder Vollständigkeitsgrad repräsentiert. Die Labelzuweisung
    erfolgt basierend auf vordefinierten Schwellenwerten, die durch die Konstanten
    `ANSWER_COMPLETENESS_HIGH_THRESHOLD`, `ANSWER_COMPLETENESS_MEDIUM_THRESHOLD`
    und `ANSWER_COMPLETENESS_MIN_SCORE` definiert sind.

    :param score: Ein numerischer Score, der die Vollständigkeit oder Qualität
        einer Antwort misst.
    :return: Ein Label (`str`), das den Score klassifiziert. Die möglichen Werte
        sind `LABEL_HIGH`, `LABEL_MEDIUM`, `LABEL_LOW` oder `LABEL_NONE`.
    """
    if score >= ANSWER_COMPLETENESS_HIGH_THRESHOLD:
        return LABEL_HIGH
    if score >= ANSWER_COMPLETENESS_MEDIUM_THRESHOLD:
        return LABEL_MEDIUM
    if score > ANSWER_COMPLETENESS_MIN_SCORE:
        return LABEL_LOW
    return LABEL_NONE


def build_source_context(used_chunks: list[dict[str, Any]] | None = None, used_sources: list[str] | None = None) -> str:
    """
    Erstellt einen zusammenfassenden Kontext basierend auf verwendeten Quellen
    oder Chunks. Diese Funktion generiert einen summarischen Text basierend
    auf den bereitgestellten Inhalten und ihrer jeweiligen Herkunft bzw. Kategorie.
    Falls keine Daten angegeben sind, wird ein leerer Kontext-String erzeugt.

    :param used_chunks: Eine optionale Liste von `dict`-Objekten, die
        Metainformationen wie Quelle, Kategorie und Inhalt der Chunks enthalten.
    :param used_sources: Eine optionale Liste von `str`, die Quellen referenziert,
        die in der Verarbeitung verwendet wurden.
    :return: Ein `str`, der den zusammengefügten Kontexttext repräsentiert. Falls
        keine Eingaben vorhanden sind, wird ein leerer String zurückgegeben.
    """
    used_chunks = used_chunks or []
    used_sources = used_sources or []

    if used_chunks:
        parts = []

        for index, chunk in enumerate(used_chunks, start=1):
            source = chunk.get(K_SOURCE, V_UNKNOWN)
            category = chunk.get(K_CATEGORY, V_UNKNOWN)
            content = chunk.get(K_CONTENT, "")

            parts.append(
                SOURCE_CONTEXT_TEMPLATE.format(
                    index=index,
                    source=source,
                    category=category,
                    content=content
                )
            )

        return SEP_DASHES_EXT.join(parts)

    if used_sources:
        return SOURCE_LIST_HEADER + "\n" + "\n".join(
            SOURCE_LIST_ITEM.format(source=source) for source in used_sources
        )

    return SOURCE_CONTEXT_EMPTY


def zero_result(reason: str) -> dict[str, Any]:
    """
    Generiert ein Ergebnis, das die minimale Vollständigkeit anzeigt, wenn keine Antwort erstellt
    werden kann. Alle Aspekte des Ergebnisses sind leer oder ungewiss, und es wird immer
    eine menschliche Überprüfung erforderlich gemacht.

    :param reason: Der Grund, warum kein Ergebnis erstellt werden kann. Dieser wird in der
        Eigenschaft `K_COMPLETENESS_REASON` des Ergebnisses gespeichert.
    :return: Ein Wörterbuch, das die Schlüssel `K_COMPLETENESS_SCORE`, `K_COMPLETENESS_LABEL`,
        `K_COMPLETENESS_REASON`, `K_COVERED_ASPECTS`, `K_MISSING_ASPECTS`,
        `K_UNCERTAIN_ASPECTS` und `K_HUMAN_REQUIRED` enthält. Die Werte des Wörterbuchs
        spiegeln wider, dass keine Bewertung oder Antwort möglich ist.
    """
    return {
        **_answer_completeness_model_metadata(),
        K_COMPLETENESS_SCORE: ANSWER_COMPLETENESS_MIN_SCORE,
        K_COMPLETENESS_LABEL: LABEL_NONE,
        K_COMPLETENESS_REASON: reason,
        K_COVERED_ASPECTS: [],
        K_MISSING_ASPECTS: [],
        K_UNCERTAIN_ASPECTS: [],
        K_HUMAN_REQUIRED: True
    }


def _answer_completeness_model_metadata() -> dict[str, str]:
    metadata = active_llm_step_metadata(LLM_STEP_ANSWER_COMPLETENESS)
    return {
        "answer_completeness_llm_provider": metadata.get("llm_provider", ""),
        "answer_completeness_llm_model": metadata.get("llm_model", ""),
        "answer_completeness_temperature": metadata.get("temperature", ""),
    }


def evaluate_answer_completeness(
        inquiry_text: str,
        draft_answer: str,
        used_chunks: list[dict[str, Any]] | None = None,
        used_sources: list[str] | None = None,
        result_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Evaluiert die Vollständigkeit eines Antwortentwurfs auf eine Benutzeranfrage.

    Diese Funktion bewertet, ob ein gegebener Antwortentwurf für eine Anfrage
    ausreichend vollständig ist. Sie berücksichtigt dabei die genutzten Datenquellen,
    Einschätzungen einer LLM-gestützten Bewertung und heuristische Regeln, um
    festzustellen, ob menschliches Eingreifen erforderlich ist.

    Die Analyse erfolgt in mehreren Schritten:
    - Prüfung auf mögliche Filterbedingungen, wie Injection Detection oder Eskalation.
    - Generierung und Bewertung eines Prompt-basierten Modells zur Vollständigkeit.
    - Analyse der Rückgabe, um fehlende, unklare oder behandelte Aspekte zu identifizieren.
    - Heuristische Bestimmung, ob menschliche Intervention notwendig ist.

    Alle relevanten Ergebnisse wie Score, Begründungen sowie fehlende oder unklare
    Aspekte werden in dem Ergebnisobjekt zurückgegeben.

    :param inquiry_text: Die ursprüngliche Anfrage, die beantwortet werden soll.
    :param draft_answer: Der Entwurf der Antwort, der auf Vollständigkeit geprüft wird.
    :param used_chunks: Optional. Eine Liste von Chunks (Datenblöcke), die zur
        Generierung der Antwort verwendet wurden. Jeder Chunk ist ein `dict`.
    :param used_sources: Optional. Eine Liste von Quellendaten, die zur Generierung
        der Antwort herangezogen wurden. Als Zeichenketten spezifiziert.
    :param result_context: Optional. Ein `dict`, das Kontexte und Ergebnisse früherer
        Modell- oder Heuristik-Analysen enthält. Verwendung für deduktive Entscheidungen.
    :return: Ein `dict`, das die Vollständigkeitsbewertung enthält, inklusive Score,
        Labels, behandelte, fehlende und unklare Aspekte sowie eine Kennzeichnung,
        ob menschliche Überprüfung erforderlich ist.
    """
    result_context = result_context or {}

    if result_context.get(K_INJECTION_DETECTED):
        if result_context.get(K_INJECTION_REASONING):
            reason = EVAL_REASON_INJECTION_DETAILS.format(
                details=result_context[K_INJECTION_REASONING]
            )
        else:
            reason = EVAL_REASON_INJECTION

        return zero_result(reason)

    response_mode = result_context.get(K_RESPONSE_MODE)

    if response_mode == MODE_BLOCKED:
        return zero_result(EVAL_REASON_BLOCKED)

    if response_mode == MODE_NO_ANSWER or result_context.get(K_NO_ANSWER_TRIGGERED):
        return zero_result(EVAL_REASON_NO_ANSWER)

    if response_mode == MODE_ESCALATION:
        return zero_result(EVAL_REASON_POLICY_ANSWER)

    if not draft_answer or not draft_answer.strip():
        return zero_result(EVAL_REASON_NO_DRAFT)

    source_context = build_source_context(used_chunks=used_chunks, used_sources=used_sources)

    user_prompt = ANSWER_COMPLETENESS_USER_PROMPT.format(
        inquiry_text=inquiry_text,
        draft_answer=draft_answer,
        source_context=source_context,
        ANSWER_COMPLETENESS_MIN_SCORE=ANSWER_COMPLETENESS_MIN_SCORE
    )

    try:
        provider, model, temperature = current_llm_step_model(LLM_STEP_ANSWER_COMPLETENESS)
        raw_result = chat_json([
            {
                K_ROLE: ROLE_SYSTEM,
                K_CONTENT_MSG: ANSWER_COMPLETENESS_SYSTEM_PROMPT
            },
            {
                K_ROLE: ROLE_USER,
                K_CONTENT_MSG: user_prompt
            }
        ], provider=provider, model=model, temperature=temperature)

    except Exception as exc:
        return {
            **_answer_completeness_model_metadata(),
            K_COMPLETENESS_SCORE: ANSWER_COMPLETENESS_MIN_SCORE,
            K_COMPLETENESS_LABEL: LABEL_NONE,
            K_COMPLETENESS_REASON: EVAL_REASON_EXCEPTION.format(
                exc_type=type(exc).__name__,
                exc_msg=str(exc)
            ),
            K_COVERED_ASPECTS: [],
            K_MISSING_ASPECTS: [],
            K_UNCERTAIN_ASPECTS: [],
            K_HUMAN_REQUIRED: True
        }

    score = clamp_score(
        raw_result.get(K_COMPLETENESS_SCORE, ANSWER_COMPLETENESS_MIN_SCORE),
    )

    missing_aspects = raw_result.get(K_MISSING_ASPECTS, [])
    uncertain_aspects = raw_result.get(K_UNCERTAIN_ASPECTS, [])

    if not isinstance(missing_aspects, list):
        missing_aspects = []

    if not isinstance(uncertain_aspects, list):
        uncertain_aspects = []

    # Bestimmung, ob menschliches Eingreifen erforderlich ist.
    # Kombination des Urteils vom LLM mit einer sicherheitsorientierten Heuristik.
    llm_requires_completion = raw_result.get(K_HUMAN_REQUIRED)

    # Heuristische Gründe für menschliches Eingreifen
    has_missing_aspects = len(missing_aspects) > 0
    has_uncertainties = len(uncertain_aspects) > 0
    low_score = score < ANSWER_COMPLETENESS_REVIEW_THRESHOLD

    if llm_requires_completion is not None:
        # Wenn das LLM explizit "false" sagt, aber der Score sehr niedrig ist,
        # wird im Sinne des Human Oversight übersteuert.
        # Oberhalb der Review-Schwelle wird dem LLM stärker vertraut, es sei denn,
        # es gibt explizit als 'fehlend' markierte Aspekte.
        if low_score:
            requires_human_completion = True
        else:
            requires_human_completion = bool(llm_requires_completion) or has_missing_aspects
    else:
        # Fallback, falls das Feld im JSON fehlte
        requires_human_completion = low_score or has_missing_aspects or has_uncertainties

    return {
        **_answer_completeness_model_metadata(),
        K_COMPLETENESS_SCORE: round(score, 4),
        K_COMPLETENESS_LABEL: label_from_score(score),
        K_COMPLETENESS_REASON: raw_result.get(
            K_COMPLETENESS_REASON,
            DEFAULT_NO_REASON
        ),
        K_COVERED_ASPECTS: raw_result.get(K_COVERED_ASPECTS, []),
        K_MISSING_ASPECTS: missing_aspects,
        K_UNCERTAIN_ASPECTS: uncertain_aspects,
        K_HUMAN_REQUIRED: bool(requires_human_completion)
    }
