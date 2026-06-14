"""Confidence-Kalibrierung der Pipeline v5.

Die Funktionen reduzieren oder stabilisieren Klassifikationsvertrauen anhand von
Retrieval-Ergebnissen, Guardrails, Self-Evaluation und Antwortvollständigkeit.
"""
from typing import Any

from src.v5.core.constants import (
    K_COMPLETENESS_SCORE,
    K_ISSUES,
    K_PASSED,
    MODE_BLOCKED,
    MODE_ESCALATION,
    MODE_NO_ANSWER,
    MODE_NORMAL,
    MODE_REVIEW,
    RISK_ESCALATION_THRESHOLD,
)


SOURCE_SUPPORT_WITH_USED_SOURCES = 1.0
SOURCE_SUPPORT_WITHOUT_USED_SOURCES = 0.35


def _bounded_score(value, default: float = 0.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default

    return max(0.0, min(1.0, score))


def _risk_penalty(risk_score: float | int | None) -> float:
    if risk_score is None:
        return 0.0

    try:
        score = float(risk_score)
    except (TypeError, ValueError):
        return 0.0

    if score <= 0:
        return 0.0

    return min(0.3, (score / max(RISK_ESCALATION_THRESHOLD, 1)) * 0.3)


def calibrate_confidence(
    original_confidence: float | int | str | None,
    retrieval_expanded: bool,
    self_evaluation_result: dict[str, Any],
    response_mode: str,
    used_sources: bool | list[Any],
    answer_completeness: dict[str, Any] | None = None,
    risk_score: float | int | None = None
) -> float:
    """
    Kalibriert den ursprünglichen Vertrauenswert der Klassifikation basierend auf zusätzlichen Faktoren wie
    Erweiterung der Abfrage, Quellenverwendung, Modus der Antwortgenerierung und der
    Ergebnisbewertung durch Selbstprüfung.

    Der Anpassungsprozess berücksichtigt:
    1. Abzüge bei Erweiterungen während der Informationsbeschaffung.
    2. Bestrafungen für das Fehlen von Quellen in bestimmten Antwortmodi.
    3. Problemhäufigkeiten aus der Selbstbewertung, wobei die Auswirkungen problemgesteuert
       gewichtet werden.
    4. Drastische Reduzierung in kritischen Antwortmodi wie Eskalation, Blockierung und
       Nichtbeantwortung.

    Das endgültige Ergebnis wird innerhalb eines definierten Intervallements [0.0, 1.0]
    normalisiert und auf 4 Dezimalstellen gerundet.

    :param original_confidence: Der ursprüngliche Vertrauenswert als `float` zwischen 0.0 und 1.0.
    :param retrieval_expanded: Ein `bool`, das angibt, ob die Informationsbeschaffung erweitert wurde.
    :param self_evaluation_result: Ein `dict`, das die Selbstbewertungsergebnisse mit der Anzahl
        von erkannten Problemen im Schlüssel `K_ISSUES` enthält.
    :param response_mode: Der Modus der Antwortgenerierung, angegeben als eine festgelegte Konstante,
        beispielsweise `MODE_NORMAL`, `MODE_REVIEW`, `MODE_ESCALATION`, `MODE_BLOCKED`, `MODE_NO_ANSWER`.
    :param used_sources: Ein `bool`, das angibt, ob Quellen verwendet wurden.
    :return: Ein kalibrierter Vertrauenswert als `float`, normalisiert im Bereich von 0.0 bis 1.0.
    """
    classification_score = _bounded_score(original_confidence)
    completeness_score = _bounded_score(
        (answer_completeness or {}).get(K_COMPLETENESS_SCORE),
        default=0.5,
    )
    source_support = (
        SOURCE_SUPPORT_WITH_USED_SOURCES
        if used_sources
        else SOURCE_SUPPORT_WITHOUT_USED_SOURCES
    )

    issue_count = len((self_evaluation_result or {}).get(K_ISSUES, []))
    self_eval_score = 1.0 if (self_evaluation_result or {}).get(K_PASSED, False) else 0.75
    self_eval_score = max(0.0, self_eval_score - issue_count * 0.1)

    calibrated = (
        classification_score * 0.4
        + completeness_score * 0.25
        + source_support * 0.2
        + self_eval_score * 0.15
    )

    if retrieval_expanded:
        calibrated -= 0.05

    calibrated -= _risk_penalty(risk_score)

    if response_mode == MODE_REVIEW:
        calibrated = min(calibrated, 0.75)
    elif response_mode == MODE_NO_ANSWER:
        calibrated = min(calibrated, 0.45)
    elif response_mode == MODE_ESCALATION:
        calibrated = min(calibrated, 0.35)
    elif response_mode == MODE_BLOCKED:
        calibrated = min(calibrated, 0.2)
    elif response_mode != MODE_NORMAL:
        calibrated = min(calibrated, 0.6)

    calibrated = max(0.0, min(1.0, calibrated))

    return round(calibrated, 4)
