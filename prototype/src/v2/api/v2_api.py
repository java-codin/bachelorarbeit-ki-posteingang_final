"""API-Orchestrierung der Pipeline v2.

Die Funktion verbindet Klassifikation, Routing, Retrieval, Antwortgenerierung
und Metrikdaten zu einem reproduzierbaren Ergebnisobjekt.
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
from src.v2.answer import generate_answer
from src.v2.classifier import classify
from src.v2.core import constants as c
from src.v2.router import route


logger = get_logger(__name__)


def run_v2_pipeline(
        inquiry_text: str,
        config: dict[str, Any],
        vector_store: Any,
        row_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Führt eine Pipeline aus, die Eingaben klassifiziert, weiterleitet, relevante Inhalte abruft
    und einen Antwortvorschlag generiert. Diese Pipeline-Version ist darauf ausgelegt, mehrere
    Schritte durchzuführen, einschließlich Klassifikation, Routing, Retrieval und Antwortgenerierung.
    Zudem werden alle Verarbeitungsschritte protokolliert.

    :param inquiry_text: Der Eingabetext, der klassifiziert, geroutet und verarbeitet werden soll.
    :param config: Konfigurationsinformationen als Wörterbuch, die die Logik der Pipeline steuern.
    :param vector_store: Eine Komponente, die für die Suche nach relevanten Inhalten basierend
        auf der Anfrage zuständig ist.
    :param row_metadata: Metadaten zu der jeweiligen Anfrage. Optional, kann unter anderem
        Informationen wie den Ground-Truth-Team-Namen enthalten.
    :return: Ein Wörterbuch mit den Ergebnissen aller Pipeline-Schritte, darunter Klassifikations-
        und Routing-Informationen, abgerufene und genutzte Quellen, der Antwortentwurf sowie
        Zeitmessungen und Metadaten zur Verarbeitung.
    """
    start = time.perf_counter()
    step_timings = {}
    case_id = safe_case_id(row_metadata, c.K_CASE_ID)

    log_pipeline_start(logger, version=c.PIPELINE_VERSION_V2, case_id=case_id)

    t0 = time.perf_counter()
    classification = classify(inquiry_text, config)
    step_timings[c.T_CLASSIFICATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V2,
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
        version=c.PIPELINE_VERSION_V2,
        case_id=case_id,
        step=c.T_ROUTING,
        duration=step_timings[c.T_ROUTING],
        target_team=routing[c.K_TARGET_TEAM],
        routing_status=routing[c.K_ROUTING_STATUS],
    )

    t0 = time.perf_counter()
    retrieved_chunks = vector_store.search(inquiry_text, k=c.RETRIEVAL_K)
    retrieved_sources = list({chunk[c.K_SOURCE] for chunk in retrieved_chunks})
    step_timings[c.T_RETRIEVAL] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V2,
        case_id=case_id,
        step=c.T_RETRIEVAL,
        duration=step_timings[c.T_RETRIEVAL],
        retrieved_chunks=len(retrieved_chunks),
        retrieved_sources_count=len(retrieved_sources),
        retrieval_k=c.RETRIEVAL_K,
    )

    t0 = time.perf_counter()
    generated = generate_answer(inquiry_text, retrieved_chunks)
    response_mode = "draft" if retrieved_chunks else "no_answer"
    step_timings[c.T_GENERATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V2,
        case_id=case_id,
        step=c.T_GENERATION,
        duration=step_timings[c.T_GENERATION],
        used_sources_count=len(generated[c.K_SOURCES]),
        used_chunks_count=len(generated[c.K_USED_CHUNKS]),
        response_mode=response_mode,
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
        c.K_RETRIEVED_SOURCES: generated[c.K_SOURCES],
        c.K_USED_SOURCES: generated[c.K_SOURCES],
        c.K_RETRIEVED_CHUNK_IDS: [
            chunk[c.K_CHUNK_ID] for chunk in generated[c.K_USED_CHUNKS]
        ],
        c.K_HAS_SOURCES: len(generated[c.K_SOURCES]) > 0,
        c.K_DRAFT_ANSWER: generated[c.K_ANSWER],
        c.K_STEP_TIMINGS: step_timings,
        c.K_PROCESSING_TIME: processing_time,
        c.K_VERSION: c.PIPELINE_VERSION_V2,
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
        version=c.PIPELINE_VERSION_V2,
        case_id=case_id,
        duration=processing_time,
        predicted_team=classification[c.K_TOP_TEAM],
        target_team=routing[c.K_TARGET_TEAM],
        routing_status=routing[c.K_ROUTING_STATUS],
        retrieved_chunks=len(retrieved_chunks),
        retrieved_sources_count=len(retrieved_sources),
        used_sources_count=len(generated[c.K_SOURCES]),
        response_mode=response_mode,
        no_answer_triggered=response_mode == "no_answer",
    )

    return result
