"""Routinglogik der Pipeline v4.

Das Modul überführt Klassifikationsergebnisse in Zieladresse, Anzeigename und
Routingstatus auf Basis der kommunalen Konfiguration.
"""

from typing import Any

from src.v4.core.constants import (
    K_DISPLAY_NAME,
    K_EMAIL,
    K_NAME,
    K_ROUTING_STATUS,
    K_TARGET_EMAIL,
    K_TARGET_TEAM,
    K_TEAMS,
    K_TOP_TEAM,
    V_MANUAL_REVIEW,
    V_ROUTED,
    V_UNKNOWN,
)
from src.v4.core.response_messages import DISPLAY_NAME_MANUAL_REVIEW


def route(classification: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
    Bestimmt die Zielgruppe und zugehörige Metadaten basierend auf einer Klassifikation und
    einer gegebenen Konfiguration. Die Funktion ermittelt das passende Zielteam, dessen E-Mail-Adresse,
    angezeigten Namen und den Routing-Status. Falls der `classification`-Wert `V_UNKNOWN` ist, erfolgt
    eine manuelle Überprüfung.

    :param classification: Eine Klassifikation, welche Informationen über Teams und deren Priorität enthält.
        Muss den Schlüssel `K_TOP_TEAM` enthalten, welcher das priorisierte Team angibt.
    :param config: Eine Konfiguration, die Informationen über verfügbare Teams enthält. Dies umfasst
        möglichen Schlüssel wie `K_TEAMS`, welcher eine Zuordnung von Team-Namen zu Team-Daten darstellt.
    :return: Ein Wörterbuch mit Metadaten zum Routing des Klassifikationsvorgangs, einschließlich
        `K_TARGET_TEAM`, `K_TARGET_EMAIL`, `K_DISPLAY_NAME` und `K_ROUTING_STATUS`. Wenn kein passendes Team
        bestimmt werden kann, enthält das Ergebnis Informationen für eine manuelle Überprüfung.
    """
    top_team = classification[K_TOP_TEAM]

    if top_team == V_UNKNOWN:
        return {
            K_TARGET_TEAM: V_UNKNOWN,
            K_TARGET_EMAIL: None,
            K_DISPLAY_NAME: DISPLAY_NAME_MANUAL_REVIEW,
            K_ROUTING_STATUS: V_MANUAL_REVIEW
        }

    team_config = config[K_TEAMS].get(top_team, {})

    return {
        K_TARGET_TEAM: top_team,
        K_TARGET_EMAIL: team_config.get(K_EMAIL),
        K_DISPLAY_NAME: team_config.get(K_NAME, top_team),
        K_ROUTING_STATUS: V_ROUTED
    }
