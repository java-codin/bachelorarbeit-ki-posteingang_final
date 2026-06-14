"""Human-Oversight-Ableitung der Pipeline v4.

Die Funktion nutzt die zentrale Risikobewertung, um manuelle Prüfung und
Begründungen konsistent auszugeben.
"""

from typing import Any

from src.v4.core.constants import (
    CLASSIFICATION_REVIEW_THRESHOLD,
    K_CONFIDENCE,
    K_DETECTED,
    K_FLAGS,
    K_REASONS,
    K_REQUIRED,
    K_TOP_TEAM,
    REASON_GUARDRAIL_FLAGS,
    REASON_LOW_CONFIDENCE,
    REASON_NO_ANSWER_TRIGGERED,
    REASON_PROMPT_INJECTION,
    REASON_UNKNOWN_TEAM,
    V_UNKNOWN,
)


def require_human_review(
        classification: dict[str, Any],
        injection_result: dict[str, Any],
        guardrail_result: dict[str, Any],
        no_answer_triggered: bool
) -> dict[str, Any]:
    """
    Analysiert die Ergebnisse verschiedener Analysestufen, um festzustellen, ob eine
    menschliche Überprüfung erforderlich ist.

    Die Funktion bewertet die Eingangsdaten aus mehreren Quellen wie der Klassifikation,
    Ergebnissen zur Erkennung von Prompt Injection, Guardrail-Logiken und möglichen
    Fehlermeldungen. Basierend auf vorgegebenen Bedingungen wird entschieden, ob
    eine menschliche Überprüfung notwendig ist, und es werden die Gründe für eine
    mögliche Überprüfung gesammelt.

    :param classification: Ein `dict`, das die Klassifikationsdaten enthält.
                           Erwartet Schlüssel wie `K_TOP_TEAM`, um das Team zu
                           identifizieren, und `K_CONFIDENCE`, um das Vertrauen
                           der Klassifikation auszudrücken.
    :param injection_result: Ein `dict`, das die Ergebnisse der Erkennung von
                             Prompt Injection darstellt. Enthält z. B. den Schlüssel
                             `K_DETECTED`, um zwischen erkannten und nicht erkannten
                             Injektionen zu unterscheiden.
    :param guardrail_result: Ein `dict`, das die Auswertung der Guardrail-Mechanismen
                             enthält. Erwartet den Schlüssel `K_FLAGS`, um die Anzahl
                             und Art der identifizierten Guardrail-Flags zu interpretieren.
    :param no_answer_triggered: Ein `bool`, der angibt, ob ein Fehler durch das Fehlen
                                einer passenden Antwort (z. B. durch einen Trigger)
                                ausgelöst wurde.
    :return: Ein `dict`, das anzeigt, ob eine menschliche Überprüfung erforderlich ist.
             Es enthält zwei Schlüssel: `K_REQUIRED`, ein `bool`, ob eine Überprüfung
             notwendig ist, und `K_REASONS`, eine `list[str]`, die die spezifischen
             Gründe für die Entscheidung beschreibt.
    """
    reasons = []

    if classification[K_TOP_TEAM] == V_UNKNOWN:
        reasons.append(REASON_UNKNOWN_TEAM)

    if classification[K_CONFIDENCE] < CLASSIFICATION_REVIEW_THRESHOLD:
        reasons.append(REASON_LOW_CONFIDENCE)

    if injection_result[K_DETECTED]:
        reasons.append(REASON_PROMPT_INJECTION)

    if no_answer_triggered:
        reasons.append(REASON_NO_ANSWER_TRIGGERED)

    if guardrail_result[K_FLAGS]:
        reasons.append(REASON_GUARDRAIL_FLAGS)

    return {
        K_REQUIRED: len(reasons) > 0,
        K_REASONS: reasons
    }
