"""Routinglogik der Baseline-Pipeline v0.

Das Modul übersetzt die einfache Klassifikation in Zielteam, Zieladresse und
Routingstatus auf Basis der Konfiguration.
"""

def route(classification_result, config):
    """
    Routet eine Klassifikationsergebnis basierend auf der Teamzuordnung und der Konfiguration.

    Diese Funktion extrahiert das Team mit der höchsten Priorität aus
    `classification_result`. Basierend darauf wird ein Routing-Objekt generiert,
    das Details wie die Zielgruppe, Ziel-E-Mail und Anzeigeinformationen enthält.
    Im Falle eines unbekannten Teams wird ein Objekt für die manuelle Prüfung zurückgegeben.

    :param classification_result: Das Ergebnis einer Klassifikation. Es sollte einen
        Schlüssel `top_team` enthalten, der das höchste priorisierte Team repräsentiert.
    :type classification_result: Dict[str, Any]

    :param config: Konfiguration der Teams, einschließlich Team-spezifischer Daten.
        Der `config`-Parameter sollte einen Schlüssel `teams` enthalten, der die
        Teamdetails wie E-Mail und Anzeigenamen enthält.
    :type config: Dict[str, Any]

    :return: Ein Routing-Objekt, das Details über das Zielteam, dessen Ziel-E-Mail,
        den Anzeigenamen und den Routing-Status enthält.
    :rtype: Dict[str, Any]
    """
    top_team = classification_result["top_team"]

    if top_team == "unknown":
        return {
            "target_team": "unknown",
            "target_email": None,
            "display_name": "Manuelle Prüfung",
            "routing_status": "manual_review"
        }

    team_config = config["teams"].get(top_team, {})

    return {
        "target_team": top_team,
        "target_email": team_config.get("email"),
        "display_name": team_config.get("name", top_team),
        "routing_status": "routed"
    }
