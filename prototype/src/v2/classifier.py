"""LLM-gestützte Klassifikation der Pipeline v2.

Das Modul nutzt die kommunale Konfiguration als Zuständigkeitsmatrix und
stabilisiert die Modellausgabe für Routing, Retrieval und Evaluation.
"""

from typing import Any

from prototype.shared.model_profiles import LLM_STEP_CLASSIFICATION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v2.core import constants as c
from src.v2.core.prompt_templates import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_PROMPT
from src.v2.core.response_messages import (
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
    Erstellt eine Teamverantwortungsmatrix basierend auf der gegebenen Konfiguration.

    Die Methode verarbeitet die Informationen zu Teams in der `config`-Struktur und erzeugt eine
    strukturierte, textuelle Repräsentation der Verantwortlichkeitszuordnung. Dabei werden
    Team-IDs, Namen, Abteilungen, Beschreibungen, zuständige Services und Schlüsselwörter berücksichtigt.
    Falls bestimmte Informationen fehlen, werden alternative Nachrichten ausgegeben.

    :param config: Die Konfigurationsdaten, die Informationen zu Teams und deren Attributen enthalten.
    :type config: dict[str, Any]
    :return: Eine formatierte Textdarstellung der Teamverantwortungsmatrix.
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
    Erstellt eine Liste von Regeldefinitionen zur Priorisierung von Teams basierend auf Schlüsselbegriffen
    und unterstützten Diensten. Diese Regeln werden aus der übergebenen `config`-Struktur abgeleitet und
    als formatierte Zeichenkette zurückgegeben.

    Die Funktion generiert bedingte Regeln für Routing- und Klassifizierungslogik in einem generativen
    KI-System, das in einer kommunalen Posteingangsverarbeitung eingesetzt wird. Jede generierte Regel
    besteht aus einer Bedingung, welche die Übereinstimmung mit Schlüsselbegriffen oder unterstützten
    Diensten prüft, und einer Folgeaktion, welche ein bestimmtes Team zuordnet.

    Es werden nur Teams berücksichtigt, die mindestens einen Schlüsselbegriff oder Dienst definiert haben.
    Teams ohne solche Definitionen werden übersprungen.

    :param config: Eine Konfigurationsstruktur, die die relevanten Teamdefinitionen enthält. Erwartet wird
        ein Wörterbuch, das unter dem Schlüssel `c.K_TEAMS` weitere Wörterbücher umfasst. Jedes Team kann
        Schlüsselbegriffe (`c.K_KEYWORDS`) und unterstützte Dienste (`c.K_SERVICES`) definieren.
    :return: Eine formatierte Zeichenkette, die alle generierten Regeldefinitionen für priorisierte Teams
        enthält. Jede Regel besteht aus einer Bedingung und einer Zuweisung.
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
    Erstellt eine durch Komma getrennte Liste gültiger Teamnamen basierend auf den in der
    Konfiguration definierten Schlüsselwerten.

    Die Funktion durchläuft die Schlüssel des `K_TEAMS` innerhalb der übergebenen
    Konfigurationsdaten und fügt sie zu einer einzigen Zeichenkette zusammen,
    wobei die Teamnamen durch Kommas getrennt werden.

    :param config: Die Konfigurationsdaten, die Details zu Teams enthalten. Der Wert
        unter `K_TEAMS` sollte ein Wörterbuch mit Teamnamen als Schlüsseln sein.
    :return: Eine formatierte Zeichenkette, die die Teamnamen als kommagetrennte Liste enthält.
    :rtype: str
    """
    return ", ".join(config[c.K_TEAMS].keys())


def classify(text, config):
    """
    Klassifiziert den gegebenen Text basierend auf den im `config`-Parameter angegebenen
    Regeln und Verantwortlichkeiten. Diese Funktion generiert systematische und benutzerdefinierte
    Prompts für ein KI-Modell, analysiert die Antworten und normiert schließlich die Klassifikation
    in Bezug auf die Liste gültiger Teams.

    :param text:
        Der zu klassifizierende Text.
    :param config:
        Ein Konfigurationsobjekt, das die Schlüsseldefinitionen (`K_TEAMS`,
        `K_ROLE`, `ROLE_SYSTEM`, `ROLE_USER`) sowie team- und schlüsselwortspezifische
        Regeln und Matrixe enthält, die für die Prompt-Generierung und Klassifikation erforderlich sind.
    :return:
        Das normalisierte Klassifikationsergebnis als Mitglied der Liste gültiger Teams.
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
        {c.K_ROLE: c.ROLE_SYSTEM, c.K_CONTENT: system_prompt},
        {c.K_ROLE: c.ROLE_USER, c.K_CONTENT: user_prompt},
    ], provider=provider, model=model, temperature=temperature)

    return normalize_classification(result, valid_teams)


def normalize_classification(result, valid_teams):
    """
    Normalisiert die Klassifikationsergebnisse und passt die Werte an vorgegebene Regeln
    an. Diese Funktion prüft und validiert die erhaltenen Daten, passt den Wert der
    Top-Kategorie und der Wahrscheinlichkeitsangabe an und gibt die normierten Werte
    zurück. Zudem werden die einzelnen Teams in einer priorisierten Liste sortiert und
    begrenzt.

    Die Funktion berücksichtigt folgende Aspekte:
    - Überprüfung, ob die Top-Kategorie (`K_TOP_TEAM`) gültig ist.
    - Konvertierung und Begrenzung der Konfidenzwerte zwischen 0.0 und 1.0.
    - Überprüfung, Sortierung und Begrenzung der Top-3-Teams (`K_TOP3`) nach Relevanz.
    - Rückfalllogik bei Unsicherheiten durch die Festlegung eines standardisierten
      Ergebnisses (`V_UNKNOWN`).
    - Sicherstellung, dass ein Grund für die Klassifikation (`K_REASON`) in die Ausgabe
      aufgenommen wird.

    :param result: Ein `dict`, das die ursprünglichen Klassifikationsergebnisse enthält.
        Erwartete Schlüssel sind unter anderem `K_TOP_TEAM`, `K_CONFIDENCE`, `K_TOP3`
        und `K_REASON`.
    :type result: dict
    :param valid_teams: Eine Liste von gültigen Teams, gegen die die Ergebnisse geprüft
        und gefiltert werden.
    :type valid_teams: list[str]
    :return: Ein normiertes `dict`, das die angepasste Klassifikation mit den Schlüsseln
        `K_TOP_TEAM`, `K_TOP3`, `K_CONFIDENCE` und `K_REASON` enthält. Die Ergebnisse
        werden begrenzt und geprüft zurückgegeben.
    :rtype: dict
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

    return {
        c.K_TOP_TEAM: top_team,
        c.K_TOP3: top3[:c.RETRIEVAL_K],
        c.K_CONFIDENCE: round(confidence, 4),
        c.K_REASON: result.get(c.K_REASON, DEFAULT_CLASSIFICATION_REASON),
    }
