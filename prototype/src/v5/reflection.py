"""Reflexionshinweise der Pipeline v5.

Das Modul erzeugt nachvollziehbare Kurzbegründungen für Unsicherheit,
Retrieval-Erweiterung und Self-Evaluation-Probleme.
"""

from typing import List, Any

from src.v5.core.response_messages import (
    REFL_UNKNOWN_TEAM,
    REFL_LOW_CONFIDENCE,
    REFL_ADAPTIVE_RETRIEVAL,
    REFL_SELF_EVAL_ISSUE,
    REFL_CONFIDENCE_REDUCED
)
from src.v5.core.constants import K_TOP_TEAM, K_CONFIDENCE, K_ISSUES, V_UNKNOWN, CLASSIFICATION_REVIEW_THRESHOLD


def generate_reflection(
        classification: dict[str, Any],
        retrieval_reasons: List[str],
        self_evaluation_result: dict[str, Any],
        calibrated_confidence: float
) -> List[str]:
    """
    Generiert eine Liste von Reflexionen basierend auf Klassifikationen,
    Retrieval-Gründen, Selbstevaluierungsergebnissen und kalibrierter Konfidenz.
    Diese Reflexionen stellen eine Bewertung relevanter Aspekte dar, die für
    Nachvollziehbarkeit und Transparenz sorgen.

    :param classification: Ein Wörterbuch mit Schlüsseln, die die Klassifikationsergebnisse
        repräsentieren, einschließlich `K_TOP_TEAM` und `K_CONFIDENCE`.
    :param retrieval_reasons: Eine Liste von Zeichenketten, die die Begründungen für
        Retrieval-Ergebnisse beschreiben.
    :param self_evaluation_result: Ein Wörterbuch mit dem Ergebnis der Selbstevaluierung,
        einschließlich eines Schlüssels `K_ISSUES`, der eine Liste von Problemen enthält.
    :param calibrated_confidence: Eine Fließkommazahl, die die kalibrierte Konfidenz darstellt.
    :return: Eine Liste von Zeichenketten mit generierten Reflexionen.
    """
    reflections = []

    if classification[K_TOP_TEAM] == V_UNKNOWN:
        reflections.append(REFL_UNKNOWN_TEAM)

    if classification[K_CONFIDENCE] < CLASSIFICATION_REVIEW_THRESHOLD:
        reflections.append(REFL_LOW_CONFIDENCE)

    for reason in retrieval_reasons:
        reflections.append(
            REFL_ADAPTIVE_RETRIEVAL.format(reason=reason)
        )

    for issue in self_evaluation_result[K_ISSUES]:
        reflections.append(
            REFL_SELF_EVAL_ISSUE.format(issue=issue)
        )

    if calibrated_confidence < classification[K_CONFIDENCE]:
        reflections.append(REFL_CONFIDENCE_REDUCED)

    return reflections
