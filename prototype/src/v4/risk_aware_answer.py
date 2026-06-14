"""Policy-Antworten der Pipeline v4.

Das Modul erzeugt sichere Fallback-Texte für Fälle, in denen Risiko, Review
oder Eskalation eine fachliche Antwortgenerierung begrenzen.
"""

from typing import Optional, Any

from src.v4.core.constants import (
    K_ANSWER,
    K_SOURCES,
    K_USED_CHUNKS,
    MODE_BLOCKED,
    MODE_ESCALATION,
    MODE_NO_ANSWER,
)
from src.v4.core.response_messages import (
    MSG_POLICY_BLOCKED,
    MSG_POLICY_ESCALATION,
    MSG_POLICY_NO_ANSWER,
)


def generate_policy_answer(response_mode: str) -> Optional[dict[str, Any]]:
    """
    Generiert eine Antwort basierend auf der gegebenen Richtlinienentscheidung.

    Diese Funktion erstellt eine Antwort in Form eines Wörterbuchs abhängig
    vom Wert des Parameters `response_mode`. Sie verwendet drei mögliche
    Antwortmodi, die festlegen, wie mit Anfragen umgegangen wird: blockiert,
    eskaliert oder keine Antwort. Die Ergebnisse enthalten vorab definierte
    Antwortmeldungen sowie leere Listen für Quellen und verwendete Textausschnitte.
    Falls der `response_mode` nicht erkannt wird, wird `None` zurückgegeben.

    :param response_mode: Der Modus, der angibt, welche Art von Antwort
        generiert werden soll. Erwartet wird einer der vordefinierten Werte:
        `MODE_BLOCKED`, `MODE_ESCALATION` oder `MODE_NO_ANSWER`.
    :return: Ein Wörterbuch mit den Schlüsseln `K_ANSWER`, `K_SOURCES`
        und `K_USED_CHUNKS`, oder `None`, falls der `response_mode` ungültig ist.
    :rtype: Optional[dict[str, Any]]
    """
    if response_mode == MODE_BLOCKED:
        return {
            K_ANSWER: MSG_POLICY_BLOCKED,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    if response_mode == MODE_ESCALATION:
        return {
            K_ANSWER: MSG_POLICY_ESCALATION,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    if response_mode == MODE_NO_ANSWER:
        return {
            K_ANSWER: MSG_POLICY_NO_ANSWER,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    return None
