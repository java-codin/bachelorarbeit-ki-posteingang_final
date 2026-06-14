"""LLM-gestützte Klassifikation der Pipeline v1.

Das Modul baut eine Zuständigkeitsmatrix aus der Konfiguration und normalisiert
die Modellantwort auf stabile Routing- und Evaluationsfelder.
"""

import json

from prototype.shared.constants import JSON_INDENT
from prototype.shared.model_profiles import LLM_STEP_CLASSIFICATION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v1.core import constants as c
from src.v1.core.prompt_templates import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_PROMPT
from src.v1.core.response_messages import DEFAULT_CLASSIFICATION_REASON


def build_team_description(team_id: str, team: dict) -> dict:
    """
    Erstellt eine Team-Beschreibungsstruktur basierend auf der gegebenen 
    `team_id` und den bereitgestellten Team-Informationen. Das Ergebnis 
    enthält Attribute wie `K_NAME`, `K_DEPARTMENT`, `K_DESCRIPTION`, 
    `K_SERVICES` und `K_KEYWORDS`, wobei gegebenenfalls Standardwerte 
    eingesetzt werden.

    :param team_id: Die eindeutige Identifikationsnummer des Teams.
    :type team_id: str
    :param team: Ein Wörterbuch mit Informationen zum Team, das optional die 
        Schlüssel `K_NAME`, `K_DEPARTMENT`, `K_DESCRIPTION`, `K_SERVICES` 
        und `K_KEYWORDS` enthalten kann.
    :type team: dict
    :return: Strukturierte Team-Beschreibung als Wörterbuch mit den Schlüsseln
        `K_TEAM_ID`, `K_NAME`, `K_DEPARTMENT`, `K_DESCRIPTION`, `K_SERVICES`
        und `K_KEYWORDS`.
    :rtype: dict
    """
    return {
        c.K_TEAM_ID: team_id,
        c.K_NAME: team.get(c.K_NAME, team_id),
        c.K_DEPARTMENT: team.get(c.K_DEPARTMENT, ""),
        c.K_DESCRIPTION: team.get(c.K_DESCRIPTION, ""),
        c.K_SERVICES: team.get(c.K_SERVICES, []),
        c.K_KEYWORDS: team.get(c.K_KEYWORDS, []),
    }


def classify(text, config):
    valid_teams = list(config[c.K_TEAMS].keys())

    teams_description = [
        build_team_description(team_id, team)
        for team_id, team in config[c.K_TEAMS].items()
    ]

    prompt = CLASSIFIER_USER_PROMPT.format(
        teams_description=json.dumps(teams_description, ensure_ascii=False, indent=JSON_INDENT),
        text=text
    )

    provider, model, temperature = current_llm_step_model(LLM_STEP_CLASSIFICATION)
    result = chat_json([
        {c.K_ROLE: c.ROLE_SYSTEM, c.K_CONTENT: CLASSIFIER_SYSTEM_PROMPT},
        {c.K_ROLE: c.ROLE_USER, c.K_CONTENT: prompt}
    ], provider=provider, model=model, temperature=temperature)

    return normalize_classification(result, valid_teams)


def normalize_classification(result, valid_teams):
    valid_outputs = valid_teams + [c.V_UNKNOWN]

    top_team = result.get(c.K_TOP_TEAM, c.V_UNKNOWN)
    if top_team not in valid_outputs:
        top_team = c.V_UNKNOWN

    try:
        confidence = float(result.get(c.K_CONFIDENCE, 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    if confidence < c.CLASSIFICATION_UNKNOWN_THRESHOLD:
        top_team = c.V_UNKNOWN

    top3 = result.get(c.K_TOP3, [])
    if not isinstance(top3, list):
        top3 = []

    top3 = [
        team for team in top3
        if team in valid_teams
    ]

    if top_team == c.V_UNKNOWN:
        top3 = []
    else:
        if top_team not in top3:
            top3.insert(0, top_team)

        for team in valid_teams:
            if team not in top3:
                top3.append(team)

            if len(top3) == c.TOP3_LIMIT:
                break

    return {
        c.K_TOP_TEAM: top_team,
        c.K_TOP3: top3[:c.TOP3_LIMIT],
        c.K_CONFIDENCE: round(confidence, 4),
        c.K_REASON: result.get(c.K_REASON, DEFAULT_CLASSIFICATION_REASON),
    }
