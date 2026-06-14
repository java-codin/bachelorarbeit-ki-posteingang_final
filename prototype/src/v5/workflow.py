"""Workflow-Status-Mapping der Pipeline v5.

Das Modul übersetzt Response-Modus, Policy-Entscheidung und Human-Review-Signal
in operative Statuswerte für Dashboard und Evaluation.
"""

from typing import Any
from src.v5.core.constants import (
    MODE_BLOCKED, STATUS_BLOCKED, STATUS_ESCALATED, STATUS_HUMAN, STATUS_AUTO,
    K_ESCALATION_REQUIRED, K_HUMAN_REVIEW_REQUIRED
)


def determine_workflow_status(
        response_mode: str,
        response_policy: dict[str, Any]
) -> str:
    """
    Ermittelt den Workflow-Status basierend auf dem angegebenen `response_mode`
    und der Policy in `response_policy`. Der Workflow-Status definiert, wie die
    Anfrage weiterverarbeitet wird und ob menschliches Handeln erforderlich ist.

    Der Status kann eine gesperrte Anfrage, eine Eskalation, eine menschliche
    Überprüfung oder eine automatisierte Verarbeitung kennzeichnen.

    :param response_mode: Der aktuelle Reaktionsmodus der Anfrage, z. B. ob die
        Anfrage blockiert ist.
    :param response_policy: Ein Wörterbuch mit Konfigurationsschlüsseln, das
        Richtlinien definiert, um zu bestimmen, ob eine Eskalation oder
        menschliche Überprüfung erforderlich ist. Erwartete Schlüssel sind
        beispielsweise `K_ESCALATION_REQUIRED` oder `K_HUMAN_REVIEW_REQUIRED`.
    :return: Der Workflow-Status basierend auf der Evaluation von
        `response_mode` und `response_policy`. Mögliche Werte sind `STATUS_BLOCKED`,
        `STATUS_ESCALATED`, `STATUS_HUMAN` oder `STATUS_AUTO`.
    """
    if response_mode == MODE_BLOCKED:
        return STATUS_BLOCKED

    if response_policy[K_ESCALATION_REQUIRED]:
        return STATUS_ESCALATED

    if response_policy[K_HUMAN_REVIEW_REQUIRED]:
        return STATUS_HUMAN

    return STATUS_AUTO
