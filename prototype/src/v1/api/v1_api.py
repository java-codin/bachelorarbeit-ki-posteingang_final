"""API-Orchestrierung der Pipeline v1.

Die Funktion verbindet Klassifikation, Routing, Antwortentwurf und Evaluation
zu einem einheitlichen Ergebnisobjekt für Batch-Läufe und Web-Oberflächen.
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
from src.v1.answer import generate_answer
from src.v1.classifier import classify
from src.v1.core import constants as c
from src.v1.router import route


logger = get_logger(__name__)


def run_v1_pipeline(
        inquiry_text: str,
        config: dict[str, Any],
        row_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Führt die Verarbeitung eines Anfrage-Textes durch die Pipeline-Version v1 durch. Die Pipeline umfasst
    die Klassifikation, das Routing und die Generierung eines Antwortentwurfs. Ergebnisse werden protokolliert,
    einschließlich Laufzeitmetriken für jeden Schritt.

    :param inquiry_text: Der Anfrage-Text, der von der Pipeline verarbeitet werden soll.
    :param config: Konfigurationseinstellungen für die Pipeline in Form eines `dict`.
    :param row_metadata: Zusätzliche Metadaten zur gegebenen Anfrage, falls verfügbar. Optional.
    :return: Ein `dict`, das die Ergebnisse der Pipeline-Verarbeitung enthält, darunter die Klassifikations-
        und Routing-Ergebnisse, Schrittzeiten, die Prozessierungsdauer und zusätzliche Statusinformationen.
    """
    start = time.perf_counter()
    step_timings = {}
    case_id = safe_case_id(row_metadata, c.K_CASE_ID)

    log_pipeline_start(logger, version=c.PIPELINE_VERSION_V1, case_id=case_id)

    t0 = time.perf_counter()
    classification = classify(inquiry_text, config)
    step_timings[c.T_CLASSIFICATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V1,
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
        version=c.PIPELINE_VERSION_V1,
        case_id=case_id,
        step=c.T_ROUTING,
        duration=step_timings[c.T_ROUTING],
        target_team=routing[c.K_TARGET_TEAM],
        routing_status=routing[c.K_ROUTING_STATUS],
    )

    t0 = time.perf_counter()
    answer = generate_answer(classification, routing)
    step_timings[c.T_ANSWER_GENERATION] = round(time.perf_counter() - t0, 4)
    log_step_result(
        logger,
        version=c.PIPELINE_VERSION_V1,
        case_id=case_id,
        step=c.T_ANSWER_GENERATION,
        duration=step_timings[c.T_ANSWER_GENERATION],
        used_sources_count=0,
        used_chunks_count=0,
        response_mode="draft",
        draft_created=bool(answer),
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
        c.K_DRAFT_ANSWER: answer,
        c.K_STEP_TIMINGS: step_timings,
        c.K_PROCESSING_TIME: processing_time,
        c.K_VERSION: c.PIPELINE_VERSION_V1,
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
        version=c.PIPELINE_VERSION_V1,
        case_id=case_id,
        duration=processing_time,
        predicted_team=classification[c.K_TOP_TEAM],
        target_team=routing[c.K_TARGET_TEAM],
        routing_status=routing[c.K_ROUTING_STATUS],
        response_mode="draft",
    )

    return result
