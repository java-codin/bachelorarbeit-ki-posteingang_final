"""Prompt-Injection-Erkennung der Pipeline v4.

Das Modul markiert verdächtige Nutzereingaben über Mustererkennung und liefert
ein strukturiertes Signal für Sicherheits- und Risikoentscheidungen.
"""

from typing import Any

from src.v4.core.constants import K_DETECTED, K_MATCHED_PATTERNS
from src.v4.core.response_messages import SUSPICIOUS_PATTERNS


def detect_prompt_injection(text: str) -> dict[str, Any]:
    """
    Überprüft den bereitgestellten Text auf das Vorhandensein verdächtiger Muster, um potenzielle
    Prompt-Injection-Versuche zu identifizieren.

    Die Funktion durchsucht den Text nach vordefinierten Mustern, die als verdächtig gelten, um
    einen Schutzmechanismus für die Verarbeitung von generativen KI-Eingaben zu implementieren.
    Sie liefert Informationen darüber, ob ein Verdacht besteht, sowie die Liste der gefundenen
    Übereinstimmungen, falls vorhanden.

    :param text: Der zu analysierende Text.
    :type text: str
    :return: Ein Wörterbuch, das angibt, ob verdächtige Muster gefunden wurden, und eine Liste
             aller übereinstimmenden Muster.
    :rtype: dict[str, Any]
    """
    text_lower = text.lower()

    matched_patterns = [
        pattern for pattern in SUSPICIOUS_PATTERNS
        if pattern in text_lower
    ]

    return {
        K_DETECTED: len(matched_patterns) > 0,
        K_MATCHED_PATTERNS: matched_patterns
    }
