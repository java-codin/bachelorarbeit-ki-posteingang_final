"""No-Answer-Entscheidung der Pipeline v5.

Die Funktion verhindert fachliche Antwortgenerierung, wenn keine belastbaren
Quellen oder keine zuständige Organisationseinheit vorliegen.
"""

from src.v5.core.constants import K_TOP_TEAM, V_UNKNOWN


def should_trigger_no_answer(retrieved_chunks, classification: dict) -> bool:
    """
    Bestimmt, ob keine Antwort ausgelöst werden soll, basierend auf den
    bereitgestellten `retrieved_chunks` und der `classification`.

    Diese Funktion dient zur Bewertung, ob die generative KI in einem Fall,
    in dem keine ausreichenden Informationen vorliegen oder die Klassifikation
    nicht einem bekannten Team zugeordnet werden kann, keine automatisierte Antwort
    auslösen sollte.

    :param retrieved_chunks: Eine Liste von extrahierten Informationseinheiten,
                             die durch einen vorherigen Retrieval-Schritt bereitgestellt wurden.
    :param classification: Ein Wörterbuch mit Klassifizierungsinformationen, das
                           z. B. die Zuordnung zu Teams oder Labels enthält.
                           Der Schlüssel `K_TOP_TEAM` wird zur Analyse verwendet.
    :return: Ein Wahrheitswert, der angibt, ob keine Antwort ausgelöst werden soll.
             Gibt `True` zurück, wenn entweder `retrieved_chunks` leer sind oder
             `classification[K_TOP_TEAM]` dem Wert `V_UNKNOWN` entspricht.
    """
    if classification[K_TOP_TEAM] == V_UNKNOWN:
        return True

    if not retrieved_chunks:
        return True

    return False
