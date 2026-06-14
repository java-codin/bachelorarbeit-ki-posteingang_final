"""Guardrail-Prüfung der Pipeline v4.

Die Funktion validiert Antwortentwürfe anhand von Länge, Quellenbezug und
riskanten Formulierungen, bevor Risiko und Workflow abgeleitet werden.
"""

from typing import Any

from src.v4.core.constants import (
    ISSUE_ANSWER_TOO_SHORT,
    ISSUE_MISSING_SOURCES,
    ISSUE_RISKY_PHRASE_PREFIX,
    K_FLAGS,
    K_VALID,
    MIN_GUARDRAIL_ANSWER_LENGTH,
)
from src.v4.core.response_messages import RISKY_ANSWER_PHRASES


def validate_answer(answer: str, sources: Any) -> dict[str, Any]:
    """
    Validiert eine generierte Antwort anhand von Quellen und vordefinierten
    Prüfregeln, um die Einhaltung von Guardrails sicherzustellen. Die Funktion
    prüft unter anderem auf das Vorhandensein von Quellen, die Mindestlänge der
    Antwort sowie auf potenziell riskante Phrasen in der Antwort. Ergebnisse
    der Validierung werden nach Flags kategorisiert.

    :param answer: Die zu validierende Antwort als Zeichenkette. Muss nicht leer
        sein und sollte relevante Informationen enthalten.
    :param sources: Die zugehörigen Quellen, die die Antwort untermauern. Kann
        jede datenartige Struktur sein; wird auf Vorhandensein geprüft.
    :return: Ein Wörterbuch mit der Validitätsbewertung der Antwort. Es enthält
        die Schlüssel `K_VALID`, ein boolescher Wert für die Gültigkeit, und
        `K_FLAGS`, eine Liste mit erkannten Problemindikatoren.
    """
    flags: list[str] = []

    if not sources:
        flags.append(ISSUE_MISSING_SOURCES)

    if len(answer.strip()) < MIN_GUARDRAIL_ANSWER_LENGTH:
        flags.append(ISSUE_ANSWER_TOO_SHORT)

    answer_lower = answer.lower()

    for phrase in RISKY_ANSWER_PHRASES:
        if phrase in answer_lower:
            flags.append(f"{ISSUE_RISKY_PHRASE_PREFIX}: {phrase}")

    return {
        K_VALID: len(flags) == 0,
        K_FLAGS: flags
    }
