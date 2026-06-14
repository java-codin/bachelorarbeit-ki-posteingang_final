"""Policy-Antworten für risikobehaftete v5-Fälle.

Das Modul erzeugt sichere Standardtexte, wenn Security-, Review-,
Eskalations- oder No-Answer-Policies eine fachliche Antwort begrenzen.
"""

from typing import Optional, Any

from src.v5.core.response_messages import (
    MSG_SECURITY_BLOCKED_ESCALATED,
    MSG_ESCALATION_REQUIRED,
    MSG_NO_KNOWLEDGE_FOUND
)
from src.v5.core.constants import (
    K_ANSWER, K_SOURCES, K_USED_CHUNKS,
    MODE_BLOCKED, MODE_ESCALATION, MODE_NO_ANSWER
)


def generate_policy_answer(response_mode: str) -> Optional[dict[str, Any]]:
    """
    Generiert eine Antwort basierend auf der angegebenen Richtlinienentscheidungslogik.

    Diese Funktion verwendet den `response_mode`, um eine entsprechende Antwort
    in Form eines Wörterbuchs zu erstellen, das spezifische Schlüsselinformationen
    wie `K_ANSWER`, `K_SOURCES` und `K_USED_CHUNKS` enthält. Die generierten Antworten
    wurden für die Behandlung von Szenarien wie Eskalation, Blockierung und fehlendes Wissen
    vordefiniert. Wenn der `response_mode` keinen gültigen Wert hat, wird `None` zurückgegeben.

    :param response_mode: Der Modus, der spezifisch angibt, wie die Richtlinienantwort
        erstellt werden soll. Unterstützte Werte sind `MODE_BLOCKED`, `MODE_ESCALATION`,
        `MODE_NO_ANSWER`.
    :return: Ein Wörterbuch mit der generierten Antwort und den zugehörigen Metadaten
        oder `None`, falls der übergebene Modus ungültig ist.
    """
    if response_mode == MODE_BLOCKED:
        return {
            K_ANSWER: MSG_SECURITY_BLOCKED_ESCALATED,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    if response_mode == MODE_ESCALATION:
        return {
            K_ANSWER: MSG_ESCALATION_REQUIRED,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    if response_mode == MODE_NO_ANSWER:
        return {
            K_ANSWER: MSG_NO_KNOWLEDGE_FOUND,
            K_SOURCES: [],
            K_USED_CHUNKS: []
        }

    return None
