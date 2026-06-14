"""Response-Policy der Pipeline v4.

Das Modul übersetzt Antwortmodi in Regeln für Generierung, Human Review und
Eskalation, ohne diese Entscheidungen im API-Orchestrator zu verstreuen.
"""

from typing import Any

from src.v4.core.constants import (
    K_ALLOW_GENERATION,
    K_DETECTED,
    K_ESCALATION_REQUIRED,
    K_HUMAN_REVIEW_REQUIRED,
    MODE_BLOCKED,
    MODE_ESCALATION,
    MODE_NO_ANSWER,
    MODE_NORMAL,
    MODE_REVIEW,
    RISK_ESCALATION_THRESHOLD,
    RISK_REVIEW_THRESHOLD,
)


def determine_response_mode(
        risk_score: float,
        injection_result: dict[str, Any],
        no_answer_triggered: bool
) -> str:
    """
    Ermittelt den geeigneten Antwortmodus basierend auf Risikobewertung, Erkennungsstatus und ob keine
    Antwort ausgelöst wurde.

    Die Funktion entscheidet, welcher Antwortmodus gewählt wird, basierend auf den angegebenen Parametern.
    Falls eine Erkennung über den Parameter `injection_result` vorliegt, wird ein blockierter Modus verwendet.
    Falls die Risikobewertung bestimmte Schwellenwerte überschreitet, wird entweder ein Eskalationsmodus oder
    ein Überprüfungsmodus aktiviert. Falls keine Antwort ausgelöst wurde, wird ein spezifischer Modus für
    dieses Szenario verwendet. Ansonsten wird ein normaler Modus gewählt.

    :param risk_score: Risikobewertung als numerischer Wert von 0 bis 1.
    :param injection_result: Ergebnis der Erkennung als Wörterbuch, das den Schlüssel ``K_DETECTED``
        enthält, welcher anzeigt, ob ein Erkennungsereignis vorliegt.
    :param no_answer_triggered: Indikator, ob keine Antwort ausgelöst wurde. ``True`` bedeutet, dass
        keine Antwort verfügbar ist.
    :return: Antwortmodus als Zeichenkette. Kann einer der folgenden Werte sein: ``MODE_BLOCKED``,
        ``MODE_ESCALATION``, ``MODE_NO_ANSWER``, ``MODE_REVIEW`` oder ``MODE_NORMAL``.
    """
    if injection_result[K_DETECTED]:
        return MODE_BLOCKED

    if risk_score >= RISK_ESCALATION_THRESHOLD:
        return MODE_ESCALATION

    if no_answer_triggered:
        return MODE_NO_ANSWER

    if risk_score >= RISK_REVIEW_THRESHOLD:
        return MODE_REVIEW

    return MODE_NORMAL


def get_response_policy(response_mode: str) -> dict[str, bool]:
    """
    Ermittelt die Antwortpolitik für ein gegebenes Antwortmodus (`response_mode`). Die Antwortpolitik
    wird als Wörterbuch mit Schlüsseln wie `K_ALLOW_GENERATION`, `K_HUMAN_REVIEW_REQUIRED`
    und `K_ESCALATION_REQUIRED` zurückgegeben. Dieser Ansatz unterstützt die Klassifizierung und
    den Ablauf von Generierungs- und Überprüfungsprozessen, basierend auf dem definierten Modus.

    :param response_mode: Der Modus, der die gewünschte Antwortpolitik spezifiziert. Erwartete Werte
        sind z. B. `MODE_NORMAL`, `MODE_REVIEW`, `MODE_NO_ANSWER`, `MODE_ESCALATION` oder
        `MODE_BLOCKED`.
    :return: Ein Wörterbuch mit den Antwortpolitiken als boolesche Werte, abhängig vom angegebenen
        Modus:
        - `K_ALLOW_GENERATION`: Gibt an, ob die Generierung von Antworten erlaubt ist.
        - `K_HUMAN_REVIEW_REQUIRED`: Gibt an, ob eine menschliche Überprüfung erforderlich ist.
        - `K_ESCALATION_REQUIRED`: Gibt an, ob eine Eskalation erforderlich ist.
    """
    policies = {
        MODE_NORMAL: {
            K_ALLOW_GENERATION: True,
            K_HUMAN_REVIEW_REQUIRED: False,
            K_ESCALATION_REQUIRED: False
        },
        MODE_REVIEW: {
            K_ALLOW_GENERATION: True,
            K_HUMAN_REVIEW_REQUIRED: True,
            K_ESCALATION_REQUIRED: False
        },
        MODE_NO_ANSWER: {
            K_ALLOW_GENERATION: False,
            K_HUMAN_REVIEW_REQUIRED: True,
            K_ESCALATION_REQUIRED: False
        },
        MODE_ESCALATION: {
            K_ALLOW_GENERATION: False,
            K_HUMAN_REVIEW_REQUIRED: True,
            K_ESCALATION_REQUIRED: True
        },
        MODE_BLOCKED: {
            K_ALLOW_GENERATION: False,
            K_HUMAN_REVIEW_REQUIRED: True,
            K_ESCALATION_REQUIRED: True
        }
    }

    return policies.get(response_mode, policies[MODE_ESCALATION])
