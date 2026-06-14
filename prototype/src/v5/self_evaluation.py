"""Interne Qualitätsdiagnose der Pipeline v5.

Das Modul bewertet Guardrail-Ergebnisse, Quellenverwendung und Response-Modus,
damit Reflexion, Retrieval-Erweiterung und Workflow-Status begründbar bleiben.
"""

from typing import Any, List
from src.v5.core.constants import (
    K_PASSED, K_ISSUES,
    MODE_BLOCKED, MODE_NORMAL, MODE_REVIEW,
    ISSUE_SECURITY_BLOCK, ISSUE_NO_RETRIEVED_SOURCES, ISSUE_NO_USED_SOURCES,
    K_FLAGS, ISSUE_GUARDRAIL_PREFIX
)


def build_quality_diagnostic(
        guardrail_result: dict[str, Any],
        retrieved_sources: List[str],
        used_sources: List[str],
        response_mode: str,
) -> dict[str, Any]:
    """
    Erstellt eine Diagnose der Qualitätsprobleme basierend auf den bereitgestellten Argumenten.
    Die Diagnose prüft Sicherheitsaspekte, Quellennutzung und Guardrail-Ergebnisse und bietet
    eine strukturierte Zusammenfassung der identifizierten Probleme und potenziellen Risiken.

    :param guardrail_result: Ein Wörterbuch, das Guardrail-Ergebnisse umfasst. Enthält den
        Schlüssel `K_FLAGS`, eine Liste von Problemen oder Flags, die von den Guardrails
        zurückgegeben wurden.
    :param retrieved_sources: Eine Liste von Quellen, die für die Antwort abgerufen wurden.
    :param used_sources: Eine Liste von Quellen, die tatsächlich für die Erstellung der Antwort
        verwendet wurden.
    :param response_mode: Der Modus der Antwort, der den spezifischen Antworttyp definiert
        (z. B. `MODE_BLOCKED`, `MODE_NORMAL`, `MODE_REVIEW`).
    :return: Ein Wörterbuch mit zwei Schlüsseln: `K_PASSED`, das angibt, ob keine Probleme
        identifiziert wurden (`True` oder `False`), und `K_ISSUES`, eine Liste der
        diagnostizierten Qualitätsprobleme.
    """
    issues = []

    if response_mode == MODE_BLOCKED:
        issues.append(ISSUE_SECURITY_BLOCK)

    if response_mode in [MODE_NORMAL, MODE_REVIEW]:
        if not retrieved_sources:
            issues.append(ISSUE_NO_RETRIEVED_SOURCES)

        if not used_sources:
            issues.append(ISSUE_NO_USED_SOURCES)

    for flag in guardrail_result.get(K_FLAGS, []):
        issues.append(f"{ISSUE_GUARDRAIL_PREFIX}: {flag}")

    return {
        K_PASSED: len(issues) == 0,
        K_ISSUES: issues,
    }
