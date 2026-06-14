"""LLM-gestützte Klassifikation der Pipeline v3.

Die Klassifikation nutzt die kommunale Konfiguration als Zuständigkeitsmatrix
und normalisiert die Modellausgabe für robuste Weiterverarbeitung.
"""

from typing import Any

from prototype.shared.model_profiles import LLM_STEP_CLASSIFICATION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v3.core import constants as c
from src.v3.core.prompt_templates import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_PROMPT
from src.v3.core.response_messages import (
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

CONFIDENCE_THRESHOLD = c.CLASSIFICATION_UNKNOWN_THRESHOLD


def build_team_responsibility_matrix(config: dict[str, Any]) -> str:
    """
    Erstellt eine Verantwortlichkeitsmatrix für Teams basierend auf einer gegebenen Konfigurationsstruktur.

    Diese Funktion generiert eine textuelle Repräsentation der Zuständigkeiten und
    Zugehörigkeiten einzelner Teams innerhalb der bereitgestellten Konfiguration. Die Matrix
    beinhaltet Informationen wie Team-ID, Teamname, Abteilung, Beschreibung, zugeordnete
    Dienstleistungen, Schlüsselwörter und E-Mail-Adressen. Falls Schlüsselwörter oder
    Dienstleistungen fehlen, werden vordefinierte Platzhaltertexte verwendet.

    :param config: Eine Konfigurationsstruktur, die Details zu den Teams enthält. Es wird erwartet,
        dass der Schlüssel `c.K_TEAMS` auf ein Wörterbuch verweist, welches Teams als Schlüssel-Wert-
        Paare definiert, wobei die Werte weitere Informationen des jeweiligen Teams enthalten.
    :return: Die generierte Verantwortlichkeitsmatrix als Zeichenkette.
    :rtype: str
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
    Generiert Prioritätsregeln basierend auf Schlüsselwörtern und Dienstleistungen aus der
    Teamkonfiguration.

    Diese Funktion verarbeitet die bereitgestellte Konfiguration und übersetzt darin definierte
    Schlüsselwörter und Dienstleistungen pro Team in eine Liste von Regeln. Diese Regeln können
    zur weiteren Verarbeitung oder Klassifikation genutzt werden. Teams ohne definierte Schlüsselwörter
    oder Dienstleistungen werden dabei übersprungen.

    :param config: Die Konfigurationsdaten, die Informationen über Teams und zugehörige
        Schlüsselwörter sowie Dienstleistungen enthalten.
    :type config: dict[str, Any]
    :return: Eine Zeichenkette, die alle generierten Prioritätsregeln enthält. Jede Regel ist
        formatbezogen aufgebaut und von anderen Regeln durch Zeilenumbrüche getrennt.
    :rtype: str
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
    Erzeugt eine durch Komma getrennte Liste gültiger Teams basierend auf der Konfiguration.

    Diese Funktion aggregiert die Namen aller Teams, die in der durch
    `config` bereitgestellten Konfiguration unter `c.K_TEAMS` definiert sind.
    Die zurückgegebene Liste basiert auf den Schlüsseln des Dictionaries,
    das unter `c.K_TEAMS` gespeichert ist.

    :param config: Die Konfiguration als Dictionary, das unter dem Schlüssel
        `c.K_TEAMS` ein weiteres Dictionary enthält. Die Schlüssel dieses
        untergeordneten Dictionaries repräsentieren die gültigen Teams.
    :return: Eine durch Komma getrennte `str`, die alle Teams aus der Konfiguration enthält.
    """
    return ", ".join(config[c.K_TEAMS].keys())


def classify(text, config):
    """
    Klassifiziert den gegebenen Text basierend auf den in der Konfiguration definierten Teams und Regeln.

    Die Funktion erstellt automatisch System- und Nutzer-Prompts basierend auf den durch die Konfiguration
    bereitgestellten Informationen wie Verantwortlichkeitsmatrix, Keyword-Prioritätsregeln und der Liste
    gültiger Teams. Anschließend wird die Klassifikation anhand eines Rückgabewerts eines generativen
    KI-Modells durchgeführt. Die Klassifikation wird normalisiert und auf Gültigkeit geprüft, bevor sie
    ausgegeben wird.

    :param text: Der zu klassifizierende Text.
    :type text: str
    :param config: Die Konfiguration, die Informationen zu Teams, Regeln und Parametern der Klassifikation enthält.
    :type config: dict
    :return: Das Ergebnis der Klassifikation (z. B. ein durch das Modell bestimmtes Team).
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

    return normalize_classification(
        result,
        valid_teams,
    )


def normalize_classification(result, valid_teams):
    """
    Normalisiert das Klassifikationsergebnis, um sicherzustellen, dass es den
    gegebenen Anforderungen entspricht. Diese Funktion überprüft und passt die
    Top-Team-Klassifizierung, das Konfidenzniveau und die Top-3-Liste gemäß
    definierten Regeln und Schwellenwerten an.

    :param result: Ein `dict`, das die Ausgangsdaten der Klassifikation
        enthält. Erwartet werden Schlüssel wie `c.K_TOP_TEAM`, `c.K_CONFIDENCE`,
        `c.K_TOP3` und `c.K_REASON`.
    :param valid_teams: Eine `list` der gültigen Teamnamen, die für die
        Klassifizierung verwendet werden können.
    :return: Gibt ein `dict` zurück, das das normalisierte Ergebnis enthält
        mit folgenden Schlüsseln:

        - `c.K_TOP_TEAM`: Der identifizierte Top-Team-Name, oder `c.V_UNKNOWN`,
          wenn kein gültiges Team gefunden wurde.
        - `c.K_TOP3`: Eine Liste der Top-3-Teams, priorisiert nach Relevanz.
        - `c.K_CONFIDENCE`: Der normalisierte Konfidenzwert, gerundet auf vier
          Nachkommastellen.
        - `c.K_REASON`: Der Grund für die Klassifikation, als Zeichenkette.
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

    if confidence < CONFIDENCE_THRESHOLD:
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
