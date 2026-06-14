"""LLM-gestützte Klassifikation der Pipeline v4.

Das Modul nutzt die kommunale Konfiguration als Zuständigkeitsmatrix und
normalisiert Modellausgaben für Risiko- und Workflow-Logik.
"""

from typing import Any

from prototype.shared.model_profiles import LLM_STEP_CLASSIFICATION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v4.core import constants as c
from src.v4.core.prompt_templates import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_PROMPT
from src.v4.core.response_messages import (
    DEFAULT_CLASSIFICATION_REASON,
    MATRIX_LINE_DEPT,
    MATRIX_LINE_DESC,
    MATRIX_LINE_KEYS,
    MATRIX_LINE_MAIL,
    MATRIX_LINE_NAME,
    MATRIX_LINE_SERV,
    MATRIX_LINE_TEAM,
    MATRIX_SEPARATOR,
    MSG_NO_KEYWORDS,
    MSG_NO_SERVICES,
    RULE_IF_MATCH,
    RULE_THEN_TEAM,
)


def build_team_responsibility_matrix(config: dict[str, Any]) -> str:
    """
    Erstellt eine Matrix, die Verantwortlichkeiten der Teams innerhalb der Konfiguration
    nachvollziehbar auflistet. Die Matrix enthält Informationen zu Team-IDs, Namen,
    Abteilungen, Beschreibungen, angebotenen Dienstleistungen und relevanten Keywords.

    Diese Funktion ist hilfreich, um Transparenz und Nachvollziehbarkeit in der
    Zuordnung von Aufgaben und Teams zu gewährleisten, insbesondere im Zusammenhang
    mit Klassifikation und Routing.

    :param config: Eine `dict`-basierte Konfiguration, die die Teams und ihre Eigenschaften
                   unter dem Schlüssel `c.K_TEAMS` enthält. Innerhalb jedes Team-Eintrags
                   werden andere Schlüssel wie `c.K_KEYWORDS`, `c.K_SERVICES`,
                   `c.K_NAME`, `c.K_DEPARTMENT`, `c.K_DESCRIPTION` und `c.K_EMAIL`
                   verwendet, um die jeweilige Konfiguration des Teams bereitzustellen.
    :return: Eine `str`, die die Team-Matrix als durchgehende Textdarstellung enthält,
             wobei jedes Team durch Trennzeichen voneinander abgegrenzt wird.
    """
    lines = []

    for team_id, team in config[c.K_TEAMS].items():
        keywords = team.get(c.K_KEYWORDS, [])
        services = team.get(c.K_SERVICES, [])
        keyword_text = ", ".join(keywords) if keywords else MSG_NO_KEYWORDS
        service_text = ", ".join(services) if services else MSG_NO_SERVICES

        lines.append(
            f"{MATRIX_LINE_TEAM.format(team_id=team_id)}\n"
            f"{MATRIX_LINE_NAME.format(name=team.get(c.K_NAME, team_id))}\n"
            f"{MATRIX_LINE_DEPT.format(department=team.get(c.K_DEPARTMENT, ''))}\n"
            f"{MATRIX_LINE_DESC.format(description=team.get(c.K_DESCRIPTION, ''))}\n"
            f"{MATRIX_LINE_SERV.format(service_text=service_text)}\n"
            f"{MATRIX_LINE_KEYS.format(keyword_text=keyword_text)}\n"
            f"{MATRIX_LINE_MAIL.format(email=team.get(c.K_EMAIL, ''))}"
        )

    return MATRIX_SEPARATOR.join(lines)


def build_keyword_priority_rules(config: dict[str, Any]) -> str:
    """
    Erstellt eine Prioritätsregeldefinition für Schlüsselwörter und Services einer Teamkonfiguration.

    Die Funktion iteriert über die Teamkonfiguration und erzeugt basierend auf den in der Konfiguration enthaltenen
    Schlüsselwörtern und Services Regelausdrücke im Textformat. Diese Regelausdrücke werden für die Verarbeitung
    und Routinglogik in KI-basierten Systemen verwendet.

    :param config: Eine Wörterbuchstruktur, die die Teamkonfiguration enthält. Die Konfiguration muss den Schlüssel
        `c.K_TEAMS` umfassen, der ein Wörterbuch von Team-IDs als Schlüssel und Team-Eigenschaften als Werte beinhaltet.
        Jede Team-Eigenschaft kann `c.K_KEYWORDS` (Liste von Schlüsselwörtern) und `c.K_SERVICES` (Liste von Services) enthalten.
    :return: Eine Zeichenkette, die die erzeugten Regeln im Textformat repräsentiert.
    """
    rules = []

    for team_id, team in config[c.K_TEAMS].items():
        terms = team.get(c.K_KEYWORDS, []) + team.get(c.K_SERVICES, [])

        if not terms:
            continue

        rules.append(
            f"{RULE_IF_MATCH.format(terms=', '.join(terms))}\n"
            f"{RULE_THEN_TEAM.format(team=team_id)}"
        )

    return "\n".join(rules)


def build_valid_team_list(config: dict[str, Any]) -> str:
    """
    Erstellt eine durch Komma getrennte Liste von gültigen Teamnamen basierend auf den im Konfigurationsdiktat
    vorhandenen Einträgen. Die Teams werden aus der Konfiguration unter dem Schlüssel `c.K_TEAMS` extrahiert.

    Die Funktion erwartet, dass der übergebene Parameter `config` ein Dictionary ist, das den Schlüssel `c.K_TEAMS`
    enthält, welcher wiederum ein weiteres Dictionary mit den Teamnamen als Schlüssel beinhaltet.

    :param config: Ein Dictionary, das die notwendige Konfigurationsinformation für Teams enthält. Der Schlüssel
        `c.K_TEAMS` wird erwartet, der ein verschachteltes Dictionary mit Teamnamen enthält.
    :return: Eine Zeichenkette, die eine durch Komma getrennte Liste von Teamnamen enthält.
    """
    return ", ".join(config[c.K_TEAMS].keys())


def classify(text, config):
    """
    Klassifiziert den gegebenen Text basierend auf der Konfiguration.

    Eine Klassifizierung wird durchgeführt, indem eine System-Prompt und eine User-Prompt
    unter Nutzung der in der Konfiguration definierten Regeln und Validierungskriterien erstellt
    werden. Die resultierende Klassifizierung wird danach normalisiert und auf die valide
    Teamliste der Konfiguration beschränkt.

    :param text: Der zu klassifizierende Text.
    :type text: str
    :param config: Ein Konfigurationsobjekt, welches Regeln, Teams und andere Parameter
        für die Klassifizierung enthält.
    :type config: dict
    :return: Der Name des Teams, dem der Text zugeordnet wurde, als Zeichenkette.
    :rtype: str
    """
    valid_teams = list(config[c.K_TEAMS].keys())

    system_prompt = CLASSIFIER_SYSTEM_PROMPT.format(
        responsibility_matrix=build_team_responsibility_matrix(config),
        keyword_priority_rules=build_keyword_priority_rules(config),
        valid_teams_list=build_valid_team_list(config),
    )

    user_prompt = CLASSIFIER_USER_PROMPT.format(text=text)

    provider, model, temperature = current_llm_step_model(LLM_STEP_CLASSIFICATION)
    result = chat_json([
        {
            c.K_ROLE: c.ROLE_SYSTEM,
            c.K_CONTENT: system_prompt,
        },
        {
            c.K_ROLE: c.ROLE_USER,
            c.K_CONTENT: user_prompt,
        },
    ], provider=provider, model=model, temperature=temperature)

    return normalize_classification(result, valid_teams)


def normalize_classification(result, valid_teams):
    """
    Normalisiert die Klassifikation eines Ergebnisses basierend auf gültigen Teams,
    Confidence-Werten und Kategorien. Die Funktion prüft und ordnet die Klassifikation so,
    dass nur gültige und sinnvolle Ausgaben berücksichtigt werden.

    Die Ausgaben enthalten einen Hauptklassifikator (`K_TOP_TEAM`),
    eine sortierte Liste der relevanten Klassifikatoren (`K_TOP3`),
    einen normierten Confidence-Wert (`K_CONFIDENCE`) und eine Kategorie zur Nachvollziehbarkeit (`K_REASON`).

    :param result: Ein Wörterbuch, das die Eingangsdaten der Klassifikation enthält.
                   Erwartete Schlüssel sind `K_TOP_TEAM`, `K_CONFIDENCE`, `K_TOP3` und optional `K_REASON`.
    :param valid_teams: Eine Liste gültiger Klassifikatoren, die berücksichtigt werden dürfen.
    :return: Ein Wörterbuch mit den Schlüsseln `K_TOP_TEAM`, `K_TOP3`, `K_CONFIDENCE` und `K_REASON`,
             das die normalisierte Klassifikation nach den Vorgaben enthält.
    """
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

            if len(top3) == c.RETRIEVAL_K:
                break

    reason = result.get(c.K_REASON, DEFAULT_CLASSIFICATION_REASON)

    return {
        c.K_TOP_TEAM: top_team,
        c.K_TOP3: top3[:c.RETRIEVAL_K],
        c.K_CONFIDENCE: round(confidence, 4),
        c.K_REASON: reason,
    }
