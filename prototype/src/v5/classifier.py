"""Klassifikationslogik der Pipeline v5.

Das Modul baut eine Fachbereichs- und Detailmatrix aus der YAML-Konfiguration,
ruft das konfigurierte LLM auf und plausibilisiert die Antwort gegen explizit
konfigurierte Zuständigkeitsbegriffe.
"""

import unicodedata
from typing import Any, List

from prototype.shared.model_profiles import LLM_STEP_CLASSIFICATION
from src.core.llm_client import chat_json, current_llm_step_model
from src.v5.core.constants import (
    CLASSIFICATION_UNKNOWN_THRESHOLD,
    K_CONFIDENCE,
    K_CONTENT_MSG,
    K_DESCRIPTION,
    K_EMAIL,
    K_KEYWORDS,
    K_MATCHED_SUBTEAM,
    K_MATCHED_SUBTEAM_CONFIDENCE,
    K_MATCHED_SUBTEAM_NAME,
    K_MATCHED_TEAM,
    K_MATCHED_TEAM_CONFIDENCE,
    K_MATCHED_TEAM_NAME,
    K_NAME,
    K_REASON,
    K_ROLE,
    K_SERVICES,
    K_TOP3,
    K_TOP_TEAM,
    ROLE_SYSTEM,
    ROLE_USER,
    SEP_NL,
    V_UNKNOWN,
)
from src.v5.core.prompt_templates import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_PROMPT
from src.v5.core.response_messages import (
    DEFAULT_NO_REASON,
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
from src.v5.municipality_structure import (
    collect_department_keywords,
    collect_department_services,
    get_departments,
    get_divisions,
    get_teams,
)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value in (None, ""):
        return []

    return [value]


def _normalize_match_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(text.split())


def _term_matches(text: str, term: object) -> bool:
    normalized_term = _normalize_match_text(term)
    if len(normalized_term) < 3:
        return False

    return normalized_term in text


def _score_terms(text: str, values: list[Any]) -> float:
    score = 0.0

    for value in values:
        term = _normalize_match_text(value)
        if len(term) < 3 or term not in text:
            continue

        # Longer explicit service phrases are stronger than broad single keywords.
        score += 2.0 if " " in term else 1.0
        score += min(len(term), 40) / 100.0

    return score


def _division_terms(division_id: str, division: dict[str, Any]) -> list[Any]:
    return [
        division_id,
        division.get(K_NAME),
        division.get(K_DESCRIPTION),
        *(_as_list(division.get(K_SERVICES))),
        *(_as_list(division.get(K_KEYWORDS))),
    ]


def _team_terms(team_id: str, team: dict[str, Any]) -> list[Any]:
    return [
        team_id,
        team.get(K_NAME),
        team.get(K_DESCRIPTION),
        *(_as_list(team.get(K_SERVICES))),
        *(_as_list(team.get(K_KEYWORDS))),
    ]


def infer_detail_from_yaml(
        source_text: str,
        config: dict[str, Any],
        department_id: str,
        current_division: str | None = None,
) -> tuple[str | None, float, str | None, float]:
    """
    Ergänzt Bereich/Team innerhalb eines bereits erkannten Fachbereichs.

    Diese Logik verändert nicht das primäre Routingziel. Sie greift nur, wenn die
    YAML innerhalb des ausgewählten Fachbereichs eindeutige Service- oder
    Keyword-Treffer enthält.
    """
    department = get_departments(config).get(department_id)
    if not department:
        return current_division, 0.0, None, 0.0

    text = _normalize_match_text(source_text)
    divisions = get_divisions(department)
    if not divisions:
        return current_division, 0.0, None, 0.0

    selected_division = current_division if current_division in divisions else None
    best_division: str | None = selected_division
    best_division_score = 0.0
    best_team: str | None = None
    best_team_score = 0.0

    candidate_divisions = (
        {selected_division: divisions[selected_division]}
        if selected_division
        else divisions
    )

    for division_id, division in candidate_divisions.items():
        division_score = _score_terms(text, _division_terms(division_id, division))
        teams = get_teams(division)

        local_best_team: str | None = None
        local_best_team_score = 0.0

        for team_id, team in teams.items():
            team_score = _score_terms(text, _team_terms(team_id, team))
            if team_score > local_best_team_score:
                local_best_team = team_id
                local_best_team_score = team_score

        combined_score = division_score + local_best_team_score
        if combined_score > best_division_score:
            best_division = division_id
            best_division_score = combined_score
            best_team = local_best_team
            best_team_score = local_best_team_score

    if best_division_score <= 0 and len(divisions) == 1:
        best_division = next(iter(divisions))
        best_division_score = 0.6

    division_confidence = 0.0
    if best_division:
        division_confidence = 0.8 if best_division_score >= 2 else 0.6

    team_confidence = 0.0
    if best_team and best_team_score > 0:
        team_confidence = 0.85 if best_team_score >= 2 else 0.7

    return best_division, division_confidence, best_team, team_confidence


def infer_department_from_yaml(
        source_text: str,
        config: dict[str, Any],
) -> tuple[str | None, float, float, float]:
    """
    Ermittelt einen Fachbereich aus expliziten Services und Keywords der Konfiguration.

    Die Heuristik dient als Konsistenzschutz für Fälle, in denen ein lokales Modell
    einen klar konfigurierten Service einem falschen Fachbereich zuordnet.
    """
    text = _normalize_match_text(source_text)
    if not text:
        return None, 0.0, 0.0, 0.0

    ranked: list[tuple[str, float]] = []
    for department_id, department in get_departments(config).items():
        terms = collect_department_services(department) + collect_department_keywords(department)
        score = _score_terms(text, terms)
        if score > 0:
            ranked.append((department_id, score))

    if not ranked:
        return None, 0.0, 0.0, 0.0

    ranked.sort(key=lambda item: item[1], reverse=True)
    best_department, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_score < 2.0 or best_score < second_score + 1.0:
        return None, 0.0, best_score, second_score

    confidence = 0.85 if best_score >= 3.0 else 0.75
    return best_department, confidence, best_score, second_score


def collect_team_keywords(department: dict[str, Any]) -> list[str]:
    return collect_department_keywords(department)


def collect_team_services(department: dict[str, Any]) -> list[str]:
    return collect_department_services(department)


def build_department_detail_matrix_text(department: dict[str, Any]) -> str:
    entries = []

    for division_id, division in get_divisions(department).items():
        division_name = division.get(K_NAME, division_id)
        division_description = division.get(K_DESCRIPTION, "")
        division_services = ", ".join(str(value) for value in _as_list(division.get(K_SERVICES))) or MSG_NO_SERVICES
        division_keywords = ", ".join(str(value) for value in _as_list(division.get(K_KEYWORDS))) or MSG_NO_KEYWORDS
        entries.append(
            f"- Bereich {division_id} ({division_name}): {division_description} "
            f"Leistungen: {division_services}. Suchbegriffe: {division_keywords}."
        )

        for team_id, team in get_teams(division).items():
            team_name = team.get(K_NAME, team_id)
            team_description = team.get(K_DESCRIPTION, "")
            team_services = ", ".join(str(value) for value in _as_list(team.get(K_SERVICES))) or MSG_NO_SERVICES
            team_keywords = ", ".join(str(value) for value in _as_list(team.get(K_KEYWORDS))) or MSG_NO_KEYWORDS
            entries.append(
                f"  - Team {team_id} ({team_name}): {team_description} "
                f"Leistungen: {team_services}. Suchbegriffe: {team_keywords}."
            )

    return "\n".join(entries) if entries else "- Keine Bereiche oder Teams konfiguriert."


def build_division_display_name_map(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    display_names: dict[str, dict[str, str]] = {}

    for department_id, department in get_departments(config).items():
        display_names[department_id] = {
            division_id: division.get(K_NAME, division_id)
            for division_id, division in get_divisions(department).items()
        }

    return display_names


def build_team_display_name_map_by_department(config: dict[str, Any]) -> dict[str, dict[str, dict[str, str]]]:
    display_names: dict[str, dict[str, dict[str, str]]] = {}

    for department_id, department in get_departments(config).items():
        display_names[department_id] = {}
        for division_id, division in get_divisions(department).items():
            display_names[department_id][division_id] = {
                team_id: team.get(K_NAME, team_id)
                for team_id, team in get_teams(division).items()
            }

    return display_names


def build_team_responsibility_matrix(config: dict[str, Any]) -> str:
    """
    Erstellt eine Verantwortlichkeitsmatrix aus der kommunalen Konfiguration.

    Die erste Routing-Ebene ist fachlich der Department/Fachbereich. Die Felder
    ``top_team`` und ``top3`` bleiben aus Kompatibilität bestehen, enthalten aber
    Department-IDs.
    """
    lines = []

    for department_id, department in get_departments(config).items():
        name = department.get(K_NAME, department_id)
        department_group = department.get("department_group_name", "")
        description = department.get(K_DESCRIPTION, "")
        keywords = collect_department_keywords(department)
        services = collect_department_services(department)
        email = department.get(K_EMAIL, "")
        detail_text = build_department_detail_matrix_text(department)

        keyword_text = ", ".join(keywords) if keywords else MSG_NO_KEYWORDS
        service_text = ", ".join(services) if services else MSG_NO_SERVICES

        lines.append(
            f"{MATRIX_LINE_TEAM.format(team_id=department_id)}\n"
            f"{MATRIX_LINE_NAME.format(name=name)}\n"
            f"{MATRIX_LINE_DEPT.format(department=department_group)}\n"
            f"{MATRIX_LINE_DESC.format(description=description)}\n"
            f"{MATRIX_LINE_SERV.format(service_text=service_text)}\n"
            f"{MATRIX_LINE_KEYS.format(keyword_text=keyword_text)}\n"
            f"{MATRIX_LINE_MAIL.format(email=email)}\n"
            f"Bereiche und Teams:\n{detail_text}"
        )

    return MATRIX_SEPARATOR.join(lines)


def build_keyword_priority_rules(config: dict[str, Any]) -> str:
    """
    Baut regelartige Hinweise aus Keywords und Leistungen der Konfiguration.
    """
    rules = []

    for department_id, department in get_departments(config).items():
        department_terms = [
            str(term).strip()
            for term in _as_list(department.get(K_KEYWORDS)) + _as_list(department.get(K_SERVICES))
            if str(term).strip()
        ]
        if department_terms:
            rules.append(
                f"{RULE_IF_MATCH.format(terms=', '.join(department_terms))}\n"
                f"{RULE_THEN_TEAM.format(team=department_id)}"
            )

        for division_id, division in get_divisions(department).items():
            division_terms = [
                str(term).strip()
                for term in _as_list(division.get(K_KEYWORDS)) + _as_list(division.get(K_SERVICES))
                if str(term).strip()
            ]
            if division_terms:
                division_name = division.get(K_NAME, division_id)
                rules.append(
                    f"{RULE_IF_MATCH.format(terms=', '.join(division_terms))}\n"
                    f"{RULE_THEN_TEAM.format(team=department_id)}\n"
                    f"Zuständiger Bereich innerhalb dieses Fachbereichs: {division_id} ({division_name})"
                )

            for team_id, team in get_teams(division).items():
                keywords = _as_list(team.get(K_KEYWORDS))
                services = _as_list(team.get(K_SERVICES))
                terms = [str(term).strip() for term in keywords + services if str(term).strip()]

                if not terms:
                    continue

                division_name = division.get(K_NAME, division_id)
                team_name = team.get(K_NAME, team_id)
                term_text = ", ".join(terms)
                rules.append(
                    f"{RULE_IF_MATCH.format(terms=term_text)}\n"
                    f"{RULE_THEN_TEAM.format(team=department_id)}\n"
                    f"Zuständiger Bereich innerhalb dieses Fachbereichs: {division_id} ({division_name})\n"
                    f"Zuständiges Team innerhalb dieses Bereichs: {team_id} ({team_name})"
                )

    return SEP_NL.join(rules)


def build_valid_team_list(config: dict[str, Any]) -> str:
    """
    Erstellt eine durch Kommas getrennte Liste aller gültigen Department-IDs.
    """
    return ", ".join(get_departments(config).keys())


def build_team_display_name_map(config: dict[str, Any]) -> dict[str, str]:
    """
    Erstellt eine Zuordnung von technischer Department-ID zu Anzeigenamen.
    """
    return {
        department_id: department.get(K_NAME, department_id)
        for department_id, department in get_departments(config).items()
    }


def classify(text: str, config: dict[str, Any]) -> dict[str, Any]:
    """
    Klassifiziert einen eingehenden Text mithilfe des LLM-Classifiers.

    Die fachliche Entscheidung liegt beim Klassifikationsprompt. Die erste
    Routing-Ebene ist Department/Fachbereich. Aus Kompatibilität bleiben die
    bisherigen Felder ``top_team`` und ``matched_subteam`` erhalten.
    """
    valid_teams = list(get_departments(config).keys())

    responsibility_matrix = build_team_responsibility_matrix(config)
    keyword_priority_rules = build_keyword_priority_rules(config)
    valid_teams_list = build_valid_team_list(config)

    system_prompt = CLASSIFIER_SYSTEM_PROMPT.format(
        responsibility_matrix=responsibility_matrix,
        keyword_priority_rules=keyword_priority_rules,
        valid_teams_list=valid_teams_list,
    )

    user_prompt = CLASSIFIER_USER_PROMPT.format(text=text)

    try:
        provider, model, temperature = current_llm_step_model(LLM_STEP_CLASSIFICATION)
        classification = chat_json([
            {
                K_ROLE: ROLE_SYSTEM,
                K_CONTENT_MSG: system_prompt,
            },
            {
                K_ROLE: ROLE_USER,
                K_CONTENT_MSG: user_prompt,
            },
        ], provider=provider, model=model, temperature=temperature)
    except Exception as exc:
        classification = {
            K_TOP_TEAM: V_UNKNOWN,
            K_TOP3: [],
            K_CONFIDENCE: 0.0,
            K_REASON: f"classification_error: {type(exc).__name__}",
            K_MATCHED_SUBTEAM: V_UNKNOWN,
            K_MATCHED_SUBTEAM_NAME: V_UNKNOWN,
            K_MATCHED_SUBTEAM_CONFIDENCE: 0.0,
            K_MATCHED_TEAM: V_UNKNOWN,
            K_MATCHED_TEAM_NAME: V_UNKNOWN,
            K_MATCHED_TEAM_CONFIDENCE: 0.0,
        }

    department_display_names = build_team_display_name_map(config)
    division_display_names = build_division_display_name_map(config)
    team_display_names = build_team_display_name_map_by_department(config)
    return normalize_classification(
        classification,
        valid_teams,
        department_display_names,
        division_display_names,
        team_display_names,
        source_text=text,
        config=config,
    )


def normalize_classification(
        result: dict[str, Any],
        valid_teams: List[str],
        team_display_names: dict[str, str] | None = None,
        subteam_display_names: dict[str, dict[str, str]] | None = None,
        team_display_names_by_department: dict[str, dict[str, dict[str, str]]] | None = None,
        source_text: str = "",
        config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Normalisiert und plausibilisiert die Klassifikationsdaten.

    Die Funktion begrenzt Confidence-Werte, entfernt ungültige IDs und stellt ein
    konsistentes Top-3-Format her. Wenn der Bürgertext eindeutig zu in der
    YAML-Konfiguration hinterlegten Service- oder Zuständigkeitsbegriffen passt,
    kann die initiale LLM-Zuordnung durch diese konfigurierte Heuristik
    korrigiert werden.
    """
    valid_outputs = valid_teams + [V_UNKNOWN]
    top_team = result.get(K_TOP_TEAM, V_UNKNOWN)

    if top_team not in valid_outputs:
        top_team = V_UNKNOWN

    try:
        confidence = float(result.get(K_CONFIDENCE, 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    if confidence < CLASSIFICATION_UNKNOWN_THRESHOLD:
        top_team = V_UNKNOWN

    corrected_by_config_heuristic = False
    if config is not None and source_text:
        # Die Korrektur stützt sich ausschließlich auf die YAML-Konfiguration,
        # damit keine kommunale Zuständigkeitslogik im Python-Code entsteht.
        inferred_department, inferred_confidence, _, _ = infer_department_from_yaml(
            source_text=source_text,
            config=config,
        )
        if inferred_department and inferred_department != top_team:
            top_team = inferred_department
            confidence = inferred_confidence
            corrected_by_config_heuristic = True

    top3 = result.get(K_TOP3, [])

    if not isinstance(top3, list):
        top3 = []

    top3 = [
        team for team in top3
        if team in valid_teams
    ]

    if top_team == V_UNKNOWN:
        top3 = []
    else:
        if top_team not in top3:
            top3.insert(0, top_team)

        top3 = [
            team for team in top3
            if team in valid_teams
        ]

        for team in valid_teams:
            if team not in top3:
                top3.append(team)

            if len(top3) == 3:
                break

        top3 = top3[:3]

    reason = result.get(K_REASON, DEFAULT_NO_REASON)
    if corrected_by_config_heuristic:
        display_name = (team_display_names or {}).get(top_team, top_team)
        reason = (
            f"Das Anliegen enthält eindeutig konfigurierte Service- oder Zuständigkeitsbegriffe "
            f"für den Fachbereich {display_name}. Die Zuordnung wurde deshalb gegenüber "
            "der initialen Modellantwort anhand der kommunalen Konfiguration korrigiert."
        )

    reason = normalize_classification_reason(reason, top_team, team_display_names or {})
    division_by_department = subteam_display_names or {}
    matched_division = result.get(K_MATCHED_SUBTEAM)

    if matched_division in (None, "", V_UNKNOWN, "null"):
        matched_division = None
    else:
        matched_division = str(matched_division)

    if top_team == V_UNKNOWN or matched_division not in division_by_department.get(top_team, {}):
        matched_division = None

    inferred_division_confidence = 0.0
    inferred_team_confidence = 0.0
    inferred_team: str | None = None

    if top_team != V_UNKNOWN and config is not None and source_text:
        inferred_division, inferred_division_confidence, inferred_team, inferred_team_confidence = infer_detail_from_yaml(
            source_text=source_text,
            config=config,
            department_id=top_team,
            current_division=matched_division,
        )

        if inferred_division in division_by_department.get(top_team, {}):
            matched_division = inferred_division

    matched_division_name = (
        division_by_department.get(top_team, {}).get(matched_division)
        if matched_division
        else V_UNKNOWN
    )

    try:
        matched_division_confidence = float(result.get(K_MATCHED_SUBTEAM_CONFIDENCE))
    except (TypeError, ValueError):
        matched_division_confidence = 0.0

    matched_division_confidence = round(max(0.0, min(1.0, matched_division_confidence)), 4)

    if not matched_division:
        matched_division_confidence = 0.0
    elif inferred_division_confidence:
        matched_division_confidence = max(matched_division_confidence, inferred_division_confidence)

    teams_by_department = team_display_names_by_department or {}
    matched_team = result.get(K_MATCHED_TEAM)

    if matched_team in (None, "", V_UNKNOWN, "null"):
        matched_team = None
    else:
        matched_team = str(matched_team)

    if (
            top_team == V_UNKNOWN
            or not matched_division
            or matched_team not in teams_by_department.get(top_team, {}).get(matched_division, {})
    ):
        matched_team = None

    if (
            not matched_team
            and inferred_team
            and inferred_team in teams_by_department.get(top_team, {}).get(matched_division, {})
    ):
        matched_team = inferred_team

    matched_team_name = (
        teams_by_department.get(top_team, {}).get(matched_division, {}).get(matched_team)
        if matched_team
        else V_UNKNOWN
    )

    try:
        matched_team_confidence = float(result.get(K_MATCHED_TEAM_CONFIDENCE))
    except (TypeError, ValueError):
        matched_team_confidence = 0.0

    matched_team_confidence = round(max(0.0, min(1.0, matched_team_confidence)), 4)

    if not matched_team:
        matched_team_confidence = 0.0
    elif inferred_team_confidence:
        matched_team_confidence = max(matched_team_confidence, inferred_team_confidence)

    return {
        K_TOP_TEAM: top_team,
        K_TOP3: top3,
        K_CONFIDENCE: round(confidence, 4),
        K_REASON: reason,
        K_MATCHED_SUBTEAM: matched_division,
        K_MATCHED_SUBTEAM_NAME: matched_division_name,
        K_MATCHED_SUBTEAM_CONFIDENCE: matched_division_confidence,
        K_MATCHED_TEAM: matched_team,
        K_MATCHED_TEAM_NAME: matched_team_name,
        K_MATCHED_TEAM_CONFIDENCE: matched_team_confidence,
    }


def normalize_classification_reason(
        reason: object,
        top_team: str,
        team_display_names: dict[str, str],
) -> str:
    """
    Entfernt technische Artefakte aus der Klassifikationsbegründung.
    """
    if not isinstance(reason, str) or not reason.strip():
        return DEFAULT_NO_REASON

    clean_reason = " ".join(reason.split())
    lower_reason = clean_reason.lower()

    for team_id, display_name in team_display_names.items():
        clean_reason = clean_reason.replace(f"'{team_id}'", display_name)
        clean_reason = clean_reason.replace(f'"{team_id}"', display_name)
        clean_reason = clean_reason.replace(team_id, display_name)

    technical_terms = (
        "keyword",
        "keywords",
        "yaml",
        "zuständigkeitsmatrix",
        "zuständigkeitsregel",
        "team-id",
        "technische team-id",
    )

    if any(term in lower_reason for term in technical_terms):
        if top_team == V_UNKNOWN:
            return (
                "Das Anliegen ist inhaltlich noch nicht eindeutig genug, um es "
                "sicher einem Fachbereich zuzuordnen."
            )

        display_name = team_display_names.get(top_team, top_team)
        return (
            f"Das Anliegen betrifft einen Aufgabenbereich, der fachlich dem Fachbereich "
            f"{display_name} zugeordnet ist. Die Zuordnung sollte bei Bedarf "
            f"fachlich geprüft werden."
        )

    return clean_reason
