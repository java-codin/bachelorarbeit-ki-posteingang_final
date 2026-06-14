"""No-Answer-Entscheidung der Pipeline v3.

Die Funktion verhindert freie Antwortgenerierung, wenn Zuständigkeit oder
Quellenlage nicht belastbar genug für einen Entwurf sind.
"""

from src.v3.core import constants as c


def should_trigger_no_answer(retrieved_chunks, classification: dict) -> bool:
    """
    Bestimmt, ob keine Antwort ausgelöst werden sollte.

    Diese Funktion bewertet, ob eine Antwort im System ausgelöst werden sollte,
    basierend auf der gegebenen `classification` und den `retrieved_chunks`.
    Eine Antwort wird nicht ausgelöst, wenn `classification[c.K_TOP_TEAM]` den
    Wert `c.V_UNKNOWN` hat oder wenn keine `retrieved_chunks` vorhanden sind.

    :param retrieved_chunks: Eine Liste der abgerufenen Informationseinheiten
        (z. B. relevante Dokumentausschnitte oder Ergebnisse). Wenn diese Liste
        leer ist, wird keine Antwort ausgelöst.
    :param classification: Ein Wörterbuch, das die Klassifikationsergebnisse
        repräsentiert. Es wird geprüft, ob der Wert für `classification[c.K_TOP_TEAM]`
        `c.V_UNKNOWN` entspricht.
    :return: Ein Wahrheitswert, der angibt, ob keine Antwort ausgelöst werden
        sollte (`True`, wenn keine Antwort ausgelöst werden sollte; ansonsten
        `False`).
    """
    if classification[c.K_TOP_TEAM] == c.V_UNKNOWN:
        return True

    if not retrieved_chunks:
        return True

    return False
