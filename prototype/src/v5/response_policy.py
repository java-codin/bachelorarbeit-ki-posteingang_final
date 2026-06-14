"""Response-Policy der Pipeline v5.

Die Funktion ordnet Response-Modi konkreten Regeln für Antwortgenerierung,
Human Review und Eskalation zu.
"""

from typing import Dict, Any

from src.v5.core.constants import (
    MODE_BLOCKED, MODE_ESCALATION, MODE_NO_ANSWER, MODE_REVIEW, MODE_NORMAL,
    K_ALLOW_GENERATION, K_HUMAN_REVIEW_REQUIRED, K_ESCALATION_REQUIRED,
)


def get_response_policy(response_mode: str) -> Dict[str, bool]:
    """
    Gibt eine Antwortpolitik basierend auf dem angegebenen `response_mode` zurück. Die Antwortpolitik
    definiert, ob Generierung erlaubt ist, ob menschliche Prüfung erforderlich ist und ob eine
    Eskalation notwendig ist. Jede Betriebsart (`response_mode`) ist mit spezifischen Regeln verknüpft,
    die die Verarbeitung in unterschiedlichen Szenarien steuern können.

    Die Methode unterstützt mehrere vordefinierte Modi wie z. B. `MODE_NORMAL`, bei dem Generierung
    erlaubt und keine menschliche Prüfung erforderlich ist, sowie `MODE_ESCALATION`, bei dem sowohl
    eine menschliche Prüfung als auch eine Eskalation notwendig sind. Ein Fallback auf
    `MODE_ESCALATION` erfolgt, wenn der übergebene Modus unbekannt ist.

    Die Rückgabe erfolgt als `dict`, das als Schlüssel boolesche Werte für
    `K_ALLOW_GENERATION`, `K_HUMAN_REVIEW_REQUIRED` und `K_ESCALATION_REQUIRED` enthält.

    :param response_mode: Der Modus, der die gewünschte Antwortpolitik beschreibt.
    :type response_mode: str
    :return: Ein Wörterbuch, das die Regeln für `K_ALLOW_GENERATION`,
        `K_HUMAN_REVIEW_REQUIRED` und `K_ESCALATION_REQUIRED` enthält.
    :rtype: dict
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
