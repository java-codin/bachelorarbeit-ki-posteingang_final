"""API-Orchestrierung der Pipeline v4.

Die Funktion verbindet Klassifikation, Retrieval, Guardrails, Risikobewertung,
Response-Policy und Workflow-Status zu einem reproduzierbaren Ergebnisobjekt.
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
from src.v4.answer import generate_answer
from src.v4.classifier import classify
from src.v4.core.constants import (
    K_ALLOW_GENERATION,
    K_ANSWER,
    K_CASE_ID,
    K_CHUNK_ID,
    K_CONFIDENCE,
    K_DETECTED,
    K_DRAFT_ANSWER,
    K_ESCALATION_REQUIRED,
    K_FLAGS,
    K_GROUND_TRUTH_TEAM,
    K_GUARDRAIL_FLAGS,
    K_GUARDRAIL_TRIGGERED,
    K_HAS_RETRIEVED_SOURCES,
    K_HAS_USED_SOURCES,
    K_HUMAN_REVIEW_REASONS,
    K_HUMAN_REVIEW_REQUIRED,
    K_INJECTION_DETECTED,
    K_INJECTION_PATTERNS,
    K_MATCHED_PATTERNS,
    K_NO_ANSWER_TRIGGERED,
    K_POLICY_ALLOWS_GENERATION,
    K_PREDICTED_TEAM,
    K_PROCESSING_TIME,
    K_REASON,
    K_REASONS,
    K_REQUIRED,
    K_RESPONSE_MODE,
    K_RETRIEVED_CHUNK_IDS,
    K_RETRIEVED_SOURCES,
    K_RISK_REASONS,
    K_RISK_SCORE,
    K_ROUTING_STATUS,
    K_SCORE,
    K_SOURCES,
    K_SOURCE,
    K_STEP_TIMINGS,
    K_TARGET_EMAIL,
    K_TARGET_TEAM,
    K_TEXT,
    K_TIMESTAMP,
    K_TOP1_CORRECT,
    K_TOP3,
    K_TOP3_CORRECT,
    K_TOP_TEAM,
    K_USED_CHUNK_IDS,
    K_USED_CHUNKS,
    K_USED_SOURCES,
    K_VERSION,
    K_WORKFLOW_STATUS,
    PIPELINE_VERSION_V4,
    RETRIEVAL_K,
    T_CLASSIFICATION,
    T_EVALUATION,
    T_GENERATION,
    T_INJECTION,
    T_RETRIEVAL,
    T_ROUTING,
    V_UNKNOWN,
)
from src.v4.guardrails import validate_answer
from src.v4.injection_detection import detect_prompt_injection
from src.v4.no_answer import should_trigger_no_answer
from src.v4.oversight import require_human_review
from src.v4.response_policy import determine_response_mode, get_response_policy
from src.v4.risk_aware_answer import generate_policy_answer
from src.v4.risk_scoring import calculate_risk_score
from src.v4.router import route
from src.v4.source_extraction import (
    extract_used_chunks_from_sources,
    extract_used_sources_from_answer,
)
from src.v4.workflow import determine_workflow_status
from src.v4.core.response_messages import SECURITY_CLASSIFICATION_REASON


logger = get_logger(__name__)


def _apply_security_classification_fallback(
        classification: dict[str, Any],
        injection_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Übersteuert die Klassifikation bei erkannter Injection defensiv.
    """
    if not injection_result[K_DETECTED]:
        return classification

    return {
        K_TOP_TEAM: V_UNKNOWN,
        K_TOP3: [],
        K_CONFIDENCE: 0.0,
        K_REASON: SECURITY_CLASSIFICATION_REASON,
    }


def run_v4_pipeline(
        inquiry_text: str,
        config: dict[str, Any],
        vector_store: Any,
        row_metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Führt die Version-4-Pipeline zur Anfrageverarbeitung aus. Die Pipeline verarbeitet
    die übergebene Anfrage anhand mehrerer Schritte, darunter Klassifizierung,
    Routing, Abruf verknüpfter Daten, Antwortgenerierung, Validierung und
    Risikobewertung. Ergebnisse werden entsprechend geloggt und aggregiert.

    :param inquiry_text: Der Text der Benutzeranfrage, der verarbeitet werden soll.
    :param config: Konfigurationsdaten als `dict`, die die Pipeline-Schritte steuern.
    :param vector_store: Ein Suchdienst oder Vektor-Datenstore, der zur Datenabrufarbeit verwendet wird.
    :param row_metadata: Zusätzliche Metadaten zur Verarbeitung; kann `None` sein.
    :return: Ein `dict`, das die Ergebnisse der Verarbeitungs-Pipeline enthält, einschließlich
        Klassifikation, Routing-Entscheidungen, genutzten Quellen, Antwortentwurf,
        Risikobewertung und Workflow-Status.
    """
    start = time.perf_counter()
    step_timings = {}
    case_id = safe_case_id(row_metadata, K_CASE_ID)

    log_pipeline_start(logger, version=PIPELINE_VERSION_V4, case_id=case_id)

    t0 = time.perf_counter()
    injection_result = detect_prompt_injection(inquiry_text)
    step_timings[T_INJECTION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        step=T_INJECTION,
        duration=step_timings[T_INJECTION],
        injection_detected=injection_result[K_DETECTED],
        matched_patterns_count=len(injection_result[K_MATCHED_PATTERNS]),
    )

    t0 = time.perf_counter()
    classification = classify(inquiry_text, config)
    classification = _apply_security_classification_fallback(
        classification,
        injection_result,
    )
    step_timings[T_CLASSIFICATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        step=T_CLASSIFICATION,
        duration=step_timings[T_CLASSIFICATION],
        predicted_team=classification[K_TOP_TEAM],
        confidence=classification[K_CONFIDENCE],
        top3_count=len(classification[K_TOP3]),
    )

    t0 = time.perf_counter()
    routing = route(classification, config)
    step_timings[T_ROUTING] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        step=T_ROUTING,
        duration=step_timings[T_ROUTING],
        target_team=routing[K_TARGET_TEAM],
        routing_status=routing[K_ROUTING_STATUS],
    )

    t0 = time.perf_counter()
    retrieved_chunks = vector_store.search(inquiry_text, k=RETRIEVAL_K)
    retrieved_sources = list({chunk[K_SOURCE] for chunk in retrieved_chunks})
    no_answer_triggered = should_trigger_no_answer(retrieved_chunks, classification)
    step_timings[T_RETRIEVAL] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        step=T_RETRIEVAL,
        duration=step_timings[T_RETRIEVAL],
        retrieved_chunks=len(retrieved_chunks),
        retrieved_sources_count=len(retrieved_sources),
        retrieval_k=RETRIEVAL_K,
        no_answer_triggered=no_answer_triggered,
    )

    t0 = time.perf_counter()
    if not injection_result[K_DETECTED] and not no_answer_triggered:
        initial_generated = generate_answer(inquiry_text, retrieved_chunks)
    else:
        initial_generated = {K_ANSWER: "", K_SOURCES: [], K_USED_CHUNKS: []}

    initial_used_sources = (
        extract_used_sources_from_answer(initial_generated[K_ANSWER], retrieved_chunks)
        if initial_generated.get(K_ANSWER)
        else []
    )

    initial_guardrail_result = validate_answer(
        initial_generated[K_ANSWER],
        initial_used_sources
    )

    risk_result = calculate_risk_score(
        inquiry_text,
        classification,
        injection_result,
        initial_guardrail_result,
        no_answer_triggered
    )

    response_mode = determine_response_mode(
        risk_result[K_SCORE],
        injection_result,
        no_answer_triggered
    )
    response_policy = get_response_policy(response_mode)

    policy_answer = generate_policy_answer(response_mode)
    generated = policy_answer if policy_answer is not None else initial_generated

    used_sources = (
        extract_used_sources_from_answer(generated[K_ANSWER], retrieved_chunks)
        if generated.get(K_ANSWER)
        else []
    )
    used_chunks = extract_used_chunks_from_sources(used_sources, retrieved_chunks)

    step_timings[T_GENERATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        step=T_GENERATION,
        duration=step_timings[T_GENERATION],
        used_sources_count=len(used_sources),
        used_chunks_count=len(used_chunks),
        response_mode=response_mode,
        policy_allows_generation=response_policy[K_ALLOW_GENERATION],
    )

    t0 = time.perf_counter()
    guardrail_result = validate_answer(generated[K_ANSWER], used_sources)

    risk_result = calculate_risk_score(
        inquiry_text,
        classification,
        injection_result,
        guardrail_result,
        no_answer_triggered
    )

    response_mode = determine_response_mode(
        risk_result[K_SCORE],
        injection_result,
        no_answer_triggered
    )
    response_policy = get_response_policy(response_mode)

    oversight_result = require_human_review(
        classification,
        injection_result,
        guardrail_result,
        no_answer_triggered
    )

    human_review_required = (
        response_policy[K_HUMAN_REVIEW_REQUIRED] or oversight_result[K_REQUIRED]
    )

    workflow_status = determine_workflow_status(response_mode, response_policy)
    step_timings[T_EVALUATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        step=T_EVALUATION,
        duration=step_timings[T_EVALUATION],
        guardrail_triggered=len(guardrail_result[K_FLAGS]) > 0,
        guardrail_flags_count=len(guardrail_result[K_FLAGS]),
        risk_score=risk_result[K_SCORE],
        risk_reasons_count=len(risk_result[K_REASONS]),
        response_mode=response_mode,
        human_review_required=human_review_required,
        workflow_status=workflow_status,
    )

    processing_time = round(time.perf_counter() - start, 4)

    result = {
        K_CASE_ID: row_metadata.get(K_CASE_ID) if row_metadata is not None else None,
        K_TEXT: inquiry_text,
        K_GROUND_TRUTH_TEAM: (
            row_metadata.get(K_GROUND_TRUTH_TEAM) if row_metadata is not None else None
        ),

        K_PREDICTED_TEAM: classification[K_TOP_TEAM],
        K_TOP3: classification[K_TOP3],
        K_CONFIDENCE: classification[K_CONFIDENCE],
        K_REASON: classification[K_REASON],

        K_TARGET_TEAM: routing[K_TARGET_TEAM],
        K_TARGET_EMAIL: routing[K_TARGET_EMAIL],
        K_ROUTING_STATUS: routing[K_ROUTING_STATUS],

        K_RETRIEVED_SOURCES: retrieved_sources,
        K_RETRIEVED_CHUNK_IDS: [chunk[K_CHUNK_ID] for chunk in retrieved_chunks],
        K_USED_SOURCES: used_sources,
        K_USED_CHUNK_IDS: [chunk[K_CHUNK_ID] for chunk in used_chunks],
        K_HAS_RETRIEVED_SOURCES: len(retrieved_chunks) > 0,
        K_HAS_USED_SOURCES: len(used_sources) > 0,

        K_DRAFT_ANSWER: generated[K_ANSWER],

        K_INJECTION_DETECTED: injection_result[K_DETECTED],
        K_INJECTION_PATTERNS: injection_result[K_MATCHED_PATTERNS],

        K_NO_ANSWER_TRIGGERED: no_answer_triggered,
        K_GUARDRAIL_TRIGGERED: len(guardrail_result[K_FLAGS]) > 0,
        K_GUARDRAIL_FLAGS: guardrail_result[K_FLAGS],

        K_RISK_SCORE: risk_result[K_SCORE],
        K_RISK_REASONS: risk_result[K_REASONS],

        K_RESPONSE_MODE: response_mode,
        K_POLICY_ALLOWS_GENERATION: response_policy[K_ALLOW_GENERATION],
        K_ESCALATION_REQUIRED: response_policy[K_ESCALATION_REQUIRED],

        K_HUMAN_REVIEW_REQUIRED: human_review_required,
        K_HUMAN_REVIEW_REASONS: oversight_result[K_REASONS],

        K_WORKFLOW_STATUS: workflow_status,

        K_STEP_TIMINGS: step_timings,
        K_PROCESSING_TIME: processing_time,
        K_VERSION: PIPELINE_VERSION_V4,
        K_TIMESTAMP: datetime.now().isoformat(),
    }

    if row_metadata is not None and K_GROUND_TRUTH_TEAM in row_metadata:
        result[K_TOP1_CORRECT] = (
            classification[K_TOP_TEAM] == row_metadata[K_GROUND_TRUTH_TEAM]
        )
        result[K_TOP3_CORRECT] = row_metadata[K_GROUND_TRUTH_TEAM] in classification[K_TOP3]

    log_pipeline_complete(
        logger,
        version=PIPELINE_VERSION_V4,
        case_id=case_id,
        duration=processing_time,
        predicted_team=classification[K_TOP_TEAM],
        target_team=routing[K_TARGET_TEAM],
        routing_status=routing[K_ROUTING_STATUS],
        injection_detected=injection_result[K_DETECTED],
        no_answer_triggered=no_answer_triggered,
        risk_score=risk_result[K_SCORE],
        response_mode=response_mode,
        human_review_required=human_review_required,
        workflow_status=workflow_status,
    )

    return result
