"""Risikobewertungswrapper der Pipeline v4.

Die Funktion kapselt die umfassende Risikoevaluation und gibt nur die für den
v4-Workflow benötigten Score- und Begründungsfelder zurück.
"""

from typing import Any

from src.v4.core.constants import (
    CLASSIFICATION_REVIEW_THRESHOLD,
    ISSUE_HIGH_RISK_KEYWORD,
    K_CONFIDENCE,
    K_DETECTED,
    K_FLAGS,
    K_REASONS,
    K_SCORE,
    K_TOP_TEAM,
    REASON_GUARDRAIL_FLAGS,
    REASON_LOW_CONFIDENCE,
    REASON_NO_ANSWER_TRIGGERED,
    REASON_PROMPT_INJECTION,
    REASON_UNKNOWN_TEAM,
    RISK_WEIGHT_GUARDRAIL_FLAGS,
    RISK_WEIGHT_HIGH_RISK_KEYWORD,
    RISK_WEIGHT_LOW_CONFIDENCE,
    RISK_WEIGHT_NO_ANSWER,
    RISK_WEIGHT_PROMPT_INJECTION,
    RISK_WEIGHT_UNKNOWN_TEAM,
    V_UNKNOWN,
)
from src.v4.core.response_messages import HIGH_RISK_KEYWORDS


def calculate_risk_score(
        inquiry_text: str,
        classification: dict[str, Any],
        injection_result: dict[str, Any],
        guardrail_result: dict[str, Any],
        no_answer_triggered: bool
) -> dict[str, Any]:
    """
    Berechnet den Risikoscore für eine Anfrage basierend auf verschiedenen Faktoren wie
    Schlüsselwörtern im Text, Klassifikation, Prompt-Injection-Ergebnissen und Guardrail-
    Ergebnissen. Diese Funktion dient zur Bewertung potenzieller Risiken und liefert eine
    strukturierte Bewertung des Risikos sowie die zugrunde liegenden Gründe.

    :param inquiry_text: Der Text der Anfrage, der analysiert wird.
    :type inquiry_text: str
    :param classification: Ein Wörterbuch, das die Klassifikation der Anfrage sowie zugehörige
        Konfidenzwerte und Teamzuordnungen enthält.
    :type classification: dict[str, Any]
    :param injection_result: Ein Wörterbuch, das die Ergebnisse der Untersuchung auf
        Prompt-Injection-Angriffe enthält.
    :type injection_result: dict[str, Any]
    :param guardrail_result: Ein Wörterbuch, das die Ergebnisse der Überprüfung durch
        Guardrail-Mechanismen enthält.
    :type guardrail_result: dict[str, Any]
    :param no_answer_triggered: Ein Wahrheitswert, der angibt, ob bei der Bearbeitung der
        Anfrage keine Antwort erzeugt werden konnte, was auf ein potenzielles Problem hinweisen
        könnte.
    :type no_answer_triggered: bool
    :return: Ein Wörterbuch mit zwei Schlüssel-Wert-Paaren: `score`, der berechnete
        Risikowert, und `reasons`, eine Liste von Gründen, die zur Bewertung des Risikos
        beigetragen haben.
    :rtype: dict[str, Any]
    """
    score = 0
    reasons = []

    text_lower = inquiry_text.lower()

    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text_lower:
            score += RISK_WEIGHT_HIGH_RISK_KEYWORD
            reasons.append(ISSUE_HIGH_RISK_KEYWORD.format(keyword=keyword))

    if classification[K_TOP_TEAM] == V_UNKNOWN:
        score += RISK_WEIGHT_UNKNOWN_TEAM
        reasons.append(REASON_UNKNOWN_TEAM)

    if classification[K_CONFIDENCE] < CLASSIFICATION_REVIEW_THRESHOLD:
        score += RISK_WEIGHT_LOW_CONFIDENCE
        reasons.append(REASON_LOW_CONFIDENCE)

    if injection_result[K_DETECTED]:
        score += RISK_WEIGHT_PROMPT_INJECTION
        reasons.append(REASON_PROMPT_INJECTION)

    if no_answer_triggered:
        score += RISK_WEIGHT_NO_ANSWER
        reasons.append(REASON_NO_ANSWER_TRIGGERED)

    if guardrail_result[K_FLAGS]:
        score += RISK_WEIGHT_GUARDRAIL_FLAGS
        reasons.append(REASON_GUARDRAIL_FLAGS)

    return {
        K_SCORE: score,
        K_REASONS: reasons
    }
