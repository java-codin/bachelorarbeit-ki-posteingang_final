"""Routinglogik der Pipeline v5.

Das Modul übersetzt die fachliche Department-Klassifikation in Zieladresse,
Anzeigename und Routingstatus. Historische Feldnamen mit ``team`` bleiben aus
Kompatibilitätsgründen erhalten.
"""

from typing import Any

from src.v5.core.constants import (
    K_TOP_TEAM, V_UNKNOWN, K_EMAIL, K_NAME,
    K_TARGET_TEAM, K_TARGET_EMAIL, K_DISPLAY_NAME, K_ROUTING_STATUS,
    V_MANUAL_REVIEW, V_ROUTED
)
from src.v5.core.response_messages import DISPLAY_NAME_UNKNOWN
from src.v5.municipality_structure import get_department


def route(classification: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
     Bestimmt den zuständigen Fachbereich und dessen Routing-Adresse.

    Hinweis: Die Felder ``K_TOP_TEAM`` und ``K_TARGET_TEAM`` behalten aus
    Kompatibilitätsgründen ihre historischen Namen. Fachlich enthalten sie in v5
    jedoch die technische ID des zuständigen Departments/Fachbereichs.

    :param classification: Klassifikationsergebnis. Erwartet wird, dass
        ``K_TOP_TEAM`` die technische Fachbereichs-ID oder ``unknown`` enthält.
    :param config: Kommunale Organisationskonfiguration. v5 liest die
        Fachbereiche über ``department_groups`` / ``departments`` und nicht über
        eine flache ``teams``-Struktur.
    :return: Routing-Metadaten mit ``K_TARGET_TEAM`` als technischer
        Fachbereichs-ID, ``K_TARGET_EMAIL`` als Fachbereichsadresse,
        ``K_DISPLAY_NAME`` als Anzeigename des Fachbereichs und
        ``K_ROUTING_STATUS``.
    """
    department_id = classification.get(K_TOP_TEAM)

    if department_id in [None, "", V_UNKNOWN]:
        return {
            K_TARGET_TEAM: V_UNKNOWN,
            K_TARGET_EMAIL: None,
            K_DISPLAY_NAME: DISPLAY_NAME_UNKNOWN,
            K_ROUTING_STATUS: V_MANUAL_REVIEW
        }

    department = get_department(config, department_id)

    if not department:
        return {
            K_TARGET_TEAM: V_UNKNOWN,
            K_TARGET_EMAIL: None,
            K_DISPLAY_NAME: DISPLAY_NAME_UNKNOWN,
            K_ROUTING_STATUS: V_MANUAL_REVIEW
        }

    return {
        K_TARGET_TEAM: department_id,
        K_TARGET_EMAIL: department.get(K_EMAIL),
        K_DISPLAY_NAME: department.get(K_NAME, department_id),
        K_ROUTING_STATUS: V_ROUTED
    }
