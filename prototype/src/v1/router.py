"""Routinglogik der Pipeline v1.

Das Modul löst klassifizierte Team-IDs gegen die kommunale Konfiguration auf
und erzeugt ein konsistentes Routing-Ergebnis.
"""

from typing import Any

from src.v1.core import constants as c
from src.v1.core.response_messages import DISPLAY_NAME_MANUAL_REVIEW


def route(classification: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
    Routet eine Klassifikation basierend auf der Teamkonfiguration.

    Diese Funktion verarbeitet eine gegebene Klassifikation und ordnet sie nach den
    Konfigurationsvorgaben einem Zielteam, einer Ziel-E-Mail und einem Anzeigenamen zu.
    Falls das Team als unbekannt klassifiziert wird, erfolgt eine manuelle Überprüfung.
    Das Ergebnis enthält die Route-Informationen sowie den Routing-Status.

    :param classification:
        Ein `dict`, das die Klassifikation enthält. Der Schlüssel `c.K_TOP_TEAM` wird verwendet,
        um das relevante Top-Team zu bestimmen.
    :param config:
        Ein `dict`, das die Konfiguration der Teams enthält, einschließlich ihrer Zuordnungen
        für E-Mail-Adressen und Anzeigenamen.
    :return:
        Ein `dict`, das Informationen zur Routingentscheidung bereitstellt. Dieses enthält:
        - `c.K_TARGET_TEAM`: Das Zielteam oder `c.V_UNKNOWN`, falls unbekannt.
        - `c.K_TARGET_EMAIL`: Die E-Mail-Adresse des Zielteams oder `None`, falls keine zugeordnet ist.
        - `c.K_DISPLAY_NAME`: Den Anzeigenamen des Zielteams oder `DISPLAY_NAME_MANUAL_REVIEW`,
          falls eine manuelle Überprüfung erfolgt.
        - `c.K_ROUTING_STATUS`: Den Status des Routings, entweder `c.V_ROUTED` oder `c.V_MANUAL_REVIEW`.
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
