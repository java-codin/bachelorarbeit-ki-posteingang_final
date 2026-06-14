"""API-Orchestrierung der Pipeline v3.

Die Funktion verbindet Klassifikation, Injection-Erkennung, No-Answer-Logik,
Retrieval, Antwortentwurf, Guardrails und Human-Oversight-Metadaten.
"""

import time
from datetime import datetime
from typing import Any

from prototype.shared.api_logging import (
    log_pipeline_complete,
    log_pipeline_start,
    log_step_result,
    safe_case_id,
)
from prototype.shared.logging_config import get_logger
from src.v3.answer import generate_answer, generate_blocked_answer, generate_no_answer
from src.v3.classifier import classify
from src.v3.core import constants as c
from src.v3.guardrails import validate_answer
from src.v3.injection_detection import detect_prompt_injection
from src.v3.no_answer import should_trigger_no_answer
from src.v3.oversight import require_human_review
from src.v3.router import route
from src.v3.core.response_messages import SECURITY_CLASSIFICATION_REASON


logger = get_logger(__name__)


def _apply_security_classification_fallback(
        classification: dict[str, Any],
        injection_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Setzt V3 bei erkannter Injection defensiv auf manuelle Prüfung.
    """
    if not injection_result[c.K_DETECTED]:
        return classification

    return {
        c.K_TOP_TEAM: c.V_UNKNOWN,
        c.K_TOP3: [],
        c.K_CONFIDENCE: 0.0,
        c.K_REASON: SECURITY_CLASSIFICATION_REASON,
    }


def run_v3_pipeline(
        inquiry_text: str,
        config: dict[str, Any],
        vector_store: Any,
        row_metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Führt die Version 3 der Pipeline für die Anfragebearbeitung aus. Die Pipeline beinhaltet
    Schritte wie Erkennung von Prompt-Injektion, Klassifikation, Routing, Retrieval,
    Antwortgenerierung sowie Evaluation durch Guardrails und menschliche Überprüfung.

    :param inquiry_text: Der Text der eingehenden Anfrage, der verarbeitet wird.
    :param config: Konfigurationseinstellungen für Klassifikation, Routing und andere Schritte.
    :param vector_store: Ein Vektorspeicher, der zur Retrieval-Phase verwendet wird.
    :param row_metadata: Optionales Metadaten-Dictionary, das unter anderem Referenzinformationen wie
        die Case-ID oder die Ground-Truth-Klassifikation enthalten kann.
    :return: Ein Ergebnis-Dictionary, das unter anderem die Klassifikationsergebnisse,
        Routing-Entscheidungen, verwendete Quellen, generierte Antwort und Evaluationsindikatoren
        wiedergibt.
    """
    start = time.perf_counter()
    step_timings = {}
    case_id = safe_case_id(row_metadata, c.K_CASE_ID)

    log_pipeline_start(logger, version=c.PIPELINE_VERSION_V3, case_id=case_id)

    t0 = time.perf_counter()
    injection_result = detect_prompt_injection(inquiry_text)
    step_timings[c.T_INJECTION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        step=c.T_INJECTION,
        duration=step_timings[c.T_INJECTION],
        injection_detected=injection_result[c.K_DETECTED],
        matched_patterns_count=len(injection_result[c.K_MATCHED_PATTERNS]),
    )

    t0 = time.perf_counter()
    classification = classify(inquiry_text, config)
    classification = _apply_security_classification_fallback(
        classification,
        injection_result,
    )
    step_timings[c.T_CLASSIFICATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        step=c.T_CLASSIFICATION,
        duration=step_timings[c.T_CLASSIFICATION],
        predicted_team=classification[c.K_TOP_TEAM],
        confidence=classification[c.K_CONFIDENCE],
        top3_count=len(classification[c.K_TOP3]),
    )

    t0 = time.perf_counter()
    routing = route(classification, config)
    step_timings[c.T_ROUTING] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        step=c.T_ROUTING,
        duration=step_timings[c.T_ROUTING],
        target_team=routing[c.K_TARGET_TEAM],
        routing_status=routing[c.K_ROUTING_STATUS],
    )

    t0 = time.perf_counter()
    retrieved_chunks = vector_store.search(inquiry_text, k=c.RETRIEVAL_K)
    retrieved_sources = list({chunk[c.K_SOURCE] for chunk in retrieved_chunks})
    no_answer_triggered = should_trigger_no_answer(retrieved_chunks, classification)
    step_timings[c.T_RETRIEVAL] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        step=c.T_RETRIEVAL,
        duration=step_timings[c.T_RETRIEVAL],
        retrieved_chunks=len(retrieved_chunks),
        retrieved_sources_count=len(retrieved_sources),
        retrieval_k=c.RETRIEVAL_K,
        no_answer_triggered=no_answer_triggered,
    )

    t0 = time.perf_counter()
    if injection_result[c.K_DETECTED]:
        generated = generate_blocked_answer()
    elif no_answer_triggered:
        generated = generate_no_answer()
    else:
        generated = generate_answer(inquiry_text, retrieved_chunks)
    response_mode = "blocked" if injection_result[c.K_DETECTED] else "no_answer" if no_answer_triggered else "draft"

    step_timings[c.T_GENERATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        step=c.T_GENERATION,
        duration=step_timings[c.T_GENERATION],
        used_sources_count=len(generated[c.K_SOURCES]),
        used_chunks_count=len(generated[c.K_USED_CHUNKS]),
        response_mode=response_mode,
    )

    t0 = time.perf_counter()
    guardrail_result = validate_answer(
        generated[c.K_ANSWER],
        generated[c.K_SOURCES],
    )

    oversight_result = require_human_review(
        classification,
        injection_result,
        guardrail_result,
        no_answer_triggered,
    )

    step_timings[c.T_EVALUATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        step=c.T_EVALUATION,
        duration=step_timings[c.T_EVALUATION],
        guardrail_triggered=len(guardrail_result[c.K_FLAGS]) > 0,
        guardrail_flags_count=len(guardrail_result[c.K_FLAGS]),
        human_review_required=oversight_result[c.K_REQUIRED],
        human_review_reasons_count=len(oversight_result[c.K_REASONS]),
    )

    processing_time = round(time.perf_counter() - start, 4)

    result = {
        c.K_CASE_ID: row_metadata.get(c.K_CASE_ID) if row_metadata is not None else None,
        c.K_TEXT: inquiry_text,
        c.K_GROUND_TRUTH_TEAM: (
            row_metadata.get(c.K_GROUND_TRUTH_TEAM) if row_metadata is not None else None
        ),

        c.K_PREDICTED_TEAM: classification[c.K_TOP_TEAM],
        c.K_TOP3: classification[c.K_TOP3],
        c.K_CONFIDENCE: classification[c.K_CONFIDENCE],
        c.K_REASON: classification[c.K_REASON],

        c.K_TARGET_TEAM: routing[c.K_TARGET_TEAM],
        c.K_TARGET_EMAIL: routing[c.K_TARGET_EMAIL],
        c.K_ROUTING_STATUS: routing[c.K_ROUTING_STATUS],

        c.K_RETRIEVED_SOURCES: retrieved_sources,
        c.K_RETRIEVED_CHUNK_IDS: [chunk[c.K_CHUNK_ID] for chunk in retrieved_chunks],

        c.K_USED_SOURCES: generated[c.K_SOURCES],
        c.K_USED_CHUNK_IDS: [
            chunk[c.K_CHUNK_ID] for chunk in generated[c.K_USED_CHUNKS]
        ],

        c.K_HAS_RETRIEVED_SOURCES: len(retrieved_chunks) > 0,
        c.K_HAS_USED_SOURCES: len(generated[c.K_SOURCES]) > 0,
        c.K_HAS_SOURCES: len(generated[c.K_SOURCES]) > 0,

        c.K_DRAFT_ANSWER: generated[c.K_ANSWER],

        c.K_INJECTION_DETECTED: injection_result[c.K_DETECTED],
        c.K_INJECTION_PATTERNS: injection_result[c.K_MATCHED_PATTERNS],

        c.K_NO_ANSWER_TRIGGERED: no_answer_triggered,

        c.K_GUARDRAIL_TRIGGERED: len(guardrail_result[c.K_FLAGS]) > 0,
        c.K_GUARDRAIL_FLAGS: guardrail_result[c.K_FLAGS],

        c.K_HUMAN_REVIEW_REQUIRED: oversight_result[c.K_REQUIRED],
        c.K_HUMAN_REVIEW_REASONS: oversight_result[c.K_REASONS],

        c.K_STEP_TIMINGS: step_timings,
        c.K_PROCESSING_TIME: processing_time,
        c.K_VERSION: c.PIPELINE_VERSION_V3,
        c.K_TIMESTAMP: datetime.now().isoformat(),
    }

    if row_metadata is not None and c.K_GROUND_TRUTH_TEAM in row_metadata:
        result[c.K_TOP1_CORRECT] = (
            classification[c.K_TOP_TEAM] == row_metadata[c.K_GROUND_TRUTH_TEAM]
        )
        result[c.K_TOP3_CORRECT] = (
            row_metadata[c.K_GROUND_TRUTH_TEAM] in classification[c.K_TOP3]
        )

    log_pipeline_complete(
        logger,
        version=c.PIPELINE_VERSION_V3,
        case_id=case_id,
        duration=processing_time,
        predicted_team=classification[c.K_TOP_TEAM],
        target_team=routing[c.K_TARGET_TEAM],
        routing_status=routing[c.K_ROUTING_STATUS],
        injection_detected=injection_result[c.K_DETECTED],
        no_answer_triggered=no_answer_triggered,
        response_mode=response_mode,
        human_review_required=oversight_result[c.K_REQUIRED],
    )

    return result
