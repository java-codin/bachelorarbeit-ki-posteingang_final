"""Guardrail-Prüfung der Pipeline v5.

Die Funktion validiert Antwortentwürfe auf Mindestlänge, Quellenbezug und
ungültige Quellen-IDs, bevor Risiko und Workflow final abgeleitet werden.
"""

from typing import Optional, Any

from src.v5.core.constants import K_VALID, K_FLAGS, ISSUE_MISSING_SOURCES, ISSUE_ANSWER_TOO_SHORT, \
    MIN_GUARDRAIL_ANSWER_LENGTH, ISSUE_INVALID_SOURCE_IDS
from src.v5.core.response_messages import GUARDRAIL_RISKY_PHRASES, ISSUE_RISKY_PHRASE


def validate_answer(answer: str, sources: list[Any], invalid_source_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Validiert eine Antwort basierend auf gegebenen Quellen und guardrails.

    Diese Funktion überprüft, ob die Antwort die minimal erforderliche Länge
    aufweist, keine riskanten Phrasen enthält und mit den bereitgestellten
    Quellen konsistent ist. Sie kann Warnungen und Flags zurückgeben, falls
    irgendwelche Guardrails verletzt werden.

    :param answer: Die zu überprüfende Antwort.
    :param sources: Eine Liste von Quellen, die die Antwort untermauern soll.
                    Leerer Input kann als Problem markiert werden.
    :param invalid_source_ids: Eine optionale Liste von Quell-IDs, die als
                               ungültig markiert wurden.
    :return: Ein Dictionary mit den Schlüsseln `K_VALID`, das einen
             Wahrheitswert angibt, ob die Antwort gültig ist, und `K_FLAGS`,
             das eine Liste von Strings mit aufgetretenen Warnungen und
             Problemen enthält.
    """
    flags = []

    if not sources:
        flags.append(ISSUE_MISSING_SOURCES)

    if invalid_source_ids:
        flags.append(f"{ISSUE_INVALID_SOURCE_IDS}: {', '.join(invalid_source_ids)}")

    if len(answer.strip()) < MIN_GUARDRAIL_ANSWER_LENGTH:
        flags.append(ISSUE_ANSWER_TOO_SHORT)

    answer_lower = answer.lower()

    for phrase in GUARDRAIL_RISKY_PHRASES:
        if phrase in answer_lower:
            flags.append(ISSUE_RISKY_PHRASE.format(phrase=phrase))

    return {
        K_VALID: len(flags) == 0,
        K_FLAGS: flags
    }
