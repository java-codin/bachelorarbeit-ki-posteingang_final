"""Workflow-Status-Mapping der Pipeline v4.

Das Modul übersetzt Response-Policy und Review-Signale in operative Statuswerte
für automatische Entwürfe, manuelle Prüfung oder Eskalation.
"""

from src.v4.core.constants import (
    K_ESCALATION_REQUIRED,
    K_HUMAN_REVIEW_REQUIRED,
    MODE_BLOCKED,
    STATUS_AUTO,
    STATUS_BLOCKED,
    STATUS_ESCALATED,
    STATUS_HUMAN,
)


def determine_workflow_status(
        response_mode: str,
        response_policy: dict
) -> str:
    """
    Bestimmt den Arbeitsablaufstatus basierend auf dem angegebenen Antwortmodus
    und der Richtlinie.

    Die Funktion entscheidet, welcher Status für einen bestimmten Arbeitsablauf
    zurückgegeben werden soll, basierend auf angegebenen Parametern wie
    `response_mode` und `response_policy`. Die Entscheidung erfolgt auf Grundlage
    vordefinierter Konstanten und Bedingungen, die Sicherheitsanforderungen,
    menschliche Überprüfung und Eskalationslogik berücksichtigen.

    :param response_mode: Der Modus der Antwort, z. B. blockiert, wird genutzt, um
        den Arbeitsablaufstatus direkt auf einen blockierten Zustand zu setzen.
    :param response_policy: Ein Wörterbuch mit Richtlinien, das Untermengen von
        Schlüsseln enthalten kann, z. B. `K_ESCALATION_REQUIRED` oder
        `K_HUMAN_REVIEW_REQUIRED`, um den Entscheidungsprozess zu lenken.
    :return: Gibt den entsprechenden Arbeitsablaufstatus zurück. Die möglichen
        Werte sind z. B. `STATUS_BLOCKED`, `STATUS_ESCALATED`,
        `STATUS_HUMAN` oder `STATUS_AUTO`.
    """
    if response_mode == MODE_BLOCKED:
        return STATUS_BLOCKED

    if response_policy[K_ESCALATION_REQUIRED]:
        return STATUS_ESCALATED

    if response_policy[K_HUMAN_REVIEW_REQUIRED]:
        return STATUS_HUMAN

    return STATUS_AUTO
