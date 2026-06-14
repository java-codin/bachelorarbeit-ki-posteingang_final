"""Antwortentwurf der Pipeline v1.

Das Modul erzeugt eine knappe Routing- und Bearbeitungsnachricht ohne komplexes
Retrieval und bildet damit den ersten Ausbau gegenüber der Baseline ab.
"""

from src.v1.core import constants as c
from src.v1.core.response_messages import MSG_ROUTING_DRAFT, MSG_UNKNOWN_ROUTING_DRAFT


def generate_answer(classification: dict, routing: dict) -> str:
    """
    Erstellt einen Entwurfsantworttext basierend auf Klassifikations- und Routing-Daten. Diese Funktion generiert eine
    Antwort, die den Benutzer über den aktuellen Status bezüglich der Zuordnung informiert. Ist keine genaue
    Zielgruppe identifizierbar, wird ein Standardentwurf verwendet, um Unsicherheit zu kommunizieren.

    :param classification: Ein Wörterbuch, das Schlüsselinformationen zur Klassifikation enthält. Erwartete
        Schlüssel sind beispielsweise `c.K_TOP_TEAM`, die die Hauptzielgruppe identifizieren, sowie
        `c.K_REASON` für die Klassifikationsbegründung.
    :param routing: Ein Wörterbuch, das Routing-Informationen enthält. Erwartete Schlüssel sind unter anderem
        `c.K_DISPLAY_NAME`, das den Anzeige-Namen der Zielgruppe angibt, und `c.K_TARGET_EMAIL` für
        die Zieladresse, falls verfügbar.
    :return: Ein `str`, das den generierten Entwurfsantworttext enthält.
    """
    if classification[c.K_TOP_TEAM] == c.V_UNKNOWN:
        return MSG_UNKNOWN_ROUTING_DRAFT

    return MSG_ROUTING_DRAFT.format(
        display_name=routing[c.K_DISPLAY_NAME],
        reason=classification[c.K_REASON],
        target_email=routing[c.K_TARGET_EMAIL],
    )
