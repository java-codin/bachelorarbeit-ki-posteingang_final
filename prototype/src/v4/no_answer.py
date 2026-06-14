"""No-Answer-Entscheidung der Pipeline v4.

Das Modul entscheidet anhand von Zuständigkeit und Quellenlage, ob eine
automatische Antwort fachlich zu unsicher wäre.
"""

from typing import Any, List

from src.v4.core.constants import K_TOP_TEAM, V_UNKNOWN


def should_trigger_no_answer(retrieved_chunks: List[Any], classification: dict[str, Any]) -> bool:
    """
    Bestimmt, ob eine "Keine Antwort"-Entscheidung ausgelöst werden soll.

    Diese Funktion bewertet, ob basierend auf den übergebenen Parametern `retrieved_chunks`
    und `classification` keine Antwort generiert werden sollte. Sie berücksichtigt dabei,
    ob die Klassifizierung auf ein unbekanntes Team (`V_UNKNOWN`) hinweist oder
    ob keine relevanten Dokumentausschnitte (`retrieved_chunks`) gefunden wurden.

    :param retrieved_chunks: Eine Liste von gefundenen Dokumentausschnitten, basierend auf der Abfrage.
    :param classification: Ein Wörterbuch, das die Klassifikation enthält, inklusive des Teamschlüssels
        `K_TOP_TEAM` und des zugehörigen Werts.
    :return: Gibt `True` zurück, wenn keine Antwort ausgelöst werden soll, andernfalls `False`.
    """
    if classification[K_TOP_TEAM] == V_UNKNOWN:
        return True

    if not retrieved_chunks:
        return True

    return False
