"""Routinglogik der Pipeline v3.

Das Modul löst klassifizierte Zuständigkeiten gegen die Konfiguration auf und
liefert Zieladresse, Anzeigename und Routingstatus.
"""

from typing import Any

from src.v3.core import constants as c
from src.v3.core.response_messages import DISPLAY_NAME_MANUAL_REVIEW


def route(classification: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
    Leitet eine Klassifikation zu einem entsprechenden Zielteam basierend auf der
    gegebenen Konfiguration weiter. Wenn das Top-Team der Klassifikation unbekannt
    ist, werden Standardwerte für eine manuelle Überprüfung zurückgegeben.

    :param classification: Ein Wörterbuch, das die Klassifikationsergebnisse enthält.
        Muss den Schlüssel `c.K_TOP_TEAM` enthalten.
    :param config: Ein Wörterbuch, das die Konfigurationsdaten enthält. Muss die
        Team-Konfiguration unter dem Schlüssel `c.K_TEAMS` enthalten.
    :return: Ein Wörterbuch mit den Routing-Informationen, das die folgenden Schlüssel enthält:
        - `c.K_TARGET_TEAM`: Das zugewiesene Team basierend auf der Klassifikation oder `c.V_UNKNOWN`.
        - `c.K_TARGET_EMAIL`: Die E-Mail-Adresse des Zielteams oder `None` bei manueller Überprüfung.
        - `c.K_DISPLAY_NAME`: Der Anzeigename des Zielteams oder ein Standardwert für manuelle Überprüfung.
        - `c.K_ROUTING_STATUS`: Gibt den Routing-Status zurück, entweder `c.V_ROUTED` oder `c.V_MANUAL_REVIEW`.
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
