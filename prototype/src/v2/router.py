"""Routinglogik der Pipeline v2.

Das Modul übersetzt klassifizierte Zuständigkeiten in Zieladresse, Anzeigename
und Routingstatus auf Basis der kommunalen Konfiguration.
"""

from src.v2.core import constants as c
from src.v2.core.response_messages import DISPLAY_NAME_MANUAL_REVIEW


def route(classification, config):
    """
    Routet eine Nachricht basierend auf einer gegebenen Klassifikation und Konfiguration.

    Diese Funktion nimmt eine Klassifikation und eine Konfiguration entgegen und versucht,
    eine Zuordnung zu einem Ziel-Team und einer Ziel-E-Mail-Adresse vorzunehmen.
    Falls das `top_team` in der Klassifikation unbekannt ist, wird eine manuelle Überprüfung
    empfohlen. Andernfalls werden Informationen aus der entsprechenden Teamkonfiguration extrahiert.
    Das Ergebnis enthält Daten zur Zielroute, den zugehörigen Anzeigenamen sowie den Routingstatus.

    :param classification: Ein Wörterbuch mit Klassifikationsdaten. Erwartet wird, dass
        der Schlüssel `c.K_TOP_TEAM` existiert, der das oberste zugeordnete Team angibt.
    :param config: Ein Wörterbuch mit Konfigurationsdaten. Erwartet wird, dass
        der Schlüssel `c.K_TEAMS` existiert, der Teamkonfigurationen in Form von
        Unterwörterbüchern bereitstellt.
    :return: Ein Wörterbuch mit den Schlüsseln:
        - `c.K_TARGET_TEAM` : Das Ziel-Team, entweder aus `classification` oder als
          `c.V_UNKNOWN` gesetzt.
        - `c.K_TARGET_EMAIL` : Die Ziel-E-Mail-Adresse, extrahiert aus der Teamkonfiguration
          oder `None`, falls keine Informationen vorhanden sind.
        - `c.K_DISPLAY_NAME` : Anzeigename für das Team, entweder aus der Teamkonfiguration
          oder als `top_team` gesetzt.
        - `c.K_ROUTING_STATUS` : Der Routingstatus, entweder `c.V_ROUTED` oder `c.V_MANUAL_REVIEW`.
    """
    top_team = classification[c.K_TOP_TEAM]

    if top_team == c.V_UNKNOWN:
        return {
            c.K_TARGET_TEAM: c.V_UNKNOWN,
            c.K_TARGET_EMAIL: None,
            c.K_DISPLAY_NAME: DISPLAY_NAME_MANUAL_REVIEW,
            c.K_ROUTING_STATUS: c.V_MANUAL_REVIEW,
        }

    team_config = config[c.K_TEAMS].get(top_team, {})

    return {
        c.K_TARGET_TEAM: top_team,
        c.K_TARGET_EMAIL: team_config.get(c.K_EMAIL),
        c.K_DISPLAY_NAME: team_config.get(c.K_NAME, top_team),
        c.K_ROUTING_STATUS: c.V_ROUTED,
    }
