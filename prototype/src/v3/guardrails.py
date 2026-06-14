"""Guardrail-Prüfung der Pipeline v3.

Die Funktion prüft Antwortentwürfe auf Mindestlänge, Quellenbezug und riskante
Formulierungen, bevor sie in Review- und Evaluationssignale einfließen.
"""

from typing import Any
from src.v3.core import constants as c
from src.v3.core.response_messages import RISKY_ANSWER_PHRASES


def validate_answer(answer: str, sources: Any) -> dict[str, Any]:
    """
    Validiert eine generierte Antwort gemäß festgelegter Prüfregeln und identifiziert potenzielle Probleme. Die Funktion
    überprüft, ob die bereitgestellten Quellen vorhanden sind, ob die Antwort eine Mindestlänge erfüllt und ob riskante
    Formulierungen enthalten sind. Sie liefert ein Ergebnis in Form eines Wörterbuchs zurück, das angibt, ob die Antwort
    gültig ist, sowie eine Liste der identifizierten Probleme.

    :param answer: Die generierte Antwort, die geprüft werden soll.
    :param sources: Die Quellen, die zur Erstellung der Antwort verwendet wurden, z. B. Dokumente oder andere Referenzen.
    :return: Ein Wörterbuch mit Schlüsseln und Werten:
             - `c.K_VALID` (`bool`): Gibt an, ob die Antwort die Prüfregeln besteht.
             - `c.K_FLAGS` (`list[str]`): Enthält eine Liste von Kennzeichnungen oder Problemen, die bei der Validierung
               festgestellt wurden.
    """
    flags = []

    if not sources:
        flags.append(c.ISSUE_MISSING_SOURCES)

    if len(answer.strip()) < c.MIN_GUARDRAIL_ANSWER_LENGTH:
        flags.append(c.ISSUE_ANSWER_TOO_SHORT)

    answer_lower = answer.lower()

    for phrase in RISKY_ANSWER_PHRASES:
        if phrase in answer_lower:
            flags.append(c.ISSUE_RISKY_PHRASE.format(phrase=phrase))

    return {
        c.K_VALID: len(flags) == 0,
        c.K_FLAGS: flags,
    }
