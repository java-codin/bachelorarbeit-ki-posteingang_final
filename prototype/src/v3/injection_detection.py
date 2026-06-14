"""Regelbasierte Prompt-Injection-Erkennung der Pipeline v3.

Das Modul sucht nach verdächtigen Mustern im Bürgertext und liefert ein
strukturiertes Sicherheitssignal für die weitere Pipeline-Steuerung.
"""

from src.v3.core import constants as c
from src.v3.core.response_messages import SUSPICIOUS_PATTERNS


def detect_prompt_injection(text: str) -> dict[str, object]:
    """
    Prüft einen Text auf potenzielle Prompt-Injection-Muster.

    Diese Funktion untersucht die übergebene Zeichenkette auf das Vorhandensein
    verdächtiger Muster, die in der Konstante `SUSPICIOUS_PATTERNS` definiert sind.
    Es wird eine Fall-Unterscheidung durchgeführt, das heißt, der Text wird vor
    der Überprüfung in Kleinbuchstaben umgewandelt. Das Ergebnis wird als Wörterbuch
    zurückgegeben, das Informationen darüber enthält, ob verdächtige Muster erkannt
    wurden und welche Muster dem Text entsprechen.

    :param text: Der zu analysierende Text als `str`.
    :return: Ein `dict` mit zwei Schlüsseln:
        - `c.K_DETECTED` (`bool`): Gibt an, ob mindestens ein verdächtiges Muster erkannt wurde.
        - `c.K_MATCHED_PATTERNS` (`list[str]`): Eine Liste aller im Text gefundenen verdächtigen Muster.
    """
    text_lower = text.lower()

    matched_patterns = [
        pattern for pattern in SUSPICIOUS_PATTERNS
        if pattern in text_lower
    ]

    return {
        c.K_DETECTED: len(matched_patterns) > 0,
        c.K_MATCHED_PATTERNS: matched_patterns,
    }
