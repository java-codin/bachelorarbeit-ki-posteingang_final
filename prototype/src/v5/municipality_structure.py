"""Zugriffsschicht für die v5-Organisationsstruktur.

Das Modul normalisiert Department-, Bereichs- und Teamdaten aus YAML, ohne
kommunale Zuständigkeiten im Code zu hardcodieren.
"""

from __future__ import annotations

from typing import Any

from src.v5.core.constants import (
    K_DEPARTMENT_GROUPS,
    K_DEPARTMENTS,
    K_DESCRIPTION,
    K_DIVISIONS,
    K_EMAIL,
    K_NAME,
    K_SUBTEAMS,
    K_TEAMS,
    K_KEYWORDS,
    K_SERVICES,
)


def get_department_groups(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups = config.get(K_DEPARTMENT_GROUPS)
    if isinstance(groups, dict):
        return {
            str(group_id): group
            for group_id, group in groups.items()
            if isinstance(group, dict)
        }

    return {}


def get_departments(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    departments: dict[str, dict[str, Any]] = {}

    for group_id, group in get_department_groups(config).items():
        group_departments = group.get(K_DEPARTMENTS) or {}
        if not isinstance(group_departments, dict):
            continue

        for department_id, department in group_departments.items():
            if not isinstance(department, dict):
                continue

            normalized = dict(department)
            normalized.setdefault("department_group_id", group_id)
            normalized.setdefault("department_group_name", group.get(K_NAME, group_id))
            departments[str(department_id)] = normalized

    if departments:
        return departments

    # Legacy fallback: previous V5 configs exposed routing targets under "teams".
    legacy_teams = config.get(K_TEAMS) or {}
    if not isinstance(legacy_teams, dict):
        return {}

    return {
        str(team_id): team
        for team_id, team in legacy_teams.items()
        if isinstance(team, dict)
    }


def get_department(config: dict[str, Any], department_id: str | None) -> dict[str, Any] | None:
    if not department_id:
        return None

    return get_departments(config).get(str(department_id))


def get_divisions(department: dict[str, Any]) -> dict[str, dict[str, Any]]:
    divisions = department.get(K_DIVISIONS)
    if isinstance(divisions, dict):
        return {
            str(division_id): division
            for division_id, division in divisions.items()
            if isinstance(division, dict)
        }

    legacy_subteams = department.get(K_SUBTEAMS)
    if isinstance(legacy_subteams, dict):
        return {
            str(subteam_id): subteam
            for subteam_id, subteam in legacy_subteams.items()
            if isinstance(subteam, dict)
        }

    return {}


def get_teams(division: dict[str, Any]) -> dict[str, dict[str, Any]]:
    teams = division.get(K_TEAMS)
    if isinstance(teams, dict):
        return {
            str(team_id): team
            for team_id, team in teams.items()
            if isinstance(team, dict)
        }

    return {}


def get_department_display_name(config: dict[str, Any], department_id: str | None) -> str | None:
    department = get_department(config, department_id)
    if not department:
        return None

    return department.get("public_label") or department.get(K_NAME) or department_id


def department_knowledge_categories(department: dict[str, Any]) -> list[str]:
    categories: list[str] = []

    for division_id, division in get_divisions(department).items():
        category = str(division.get("knowledge_category") or division_id).strip()
        if category and category not in categories:
            categories.append(category)

    return categories


def find_division(
        department: dict[str, Any],
        division_id: str | None,
) -> dict[str, Any] | None:
    if not division_id:
        return None

    return get_divisions(department).get(str(division_id))


def find_team(
        department: dict[str, Any],
        division_id: str | None,
        team_id: str | None,
) -> dict[str, Any] | None:
    division = find_division(department, division_id)
    if not division or not team_id:
        return None

    return get_teams(division).get(str(team_id))


def collect_department_keywords(department: dict[str, Any]) -> list[str]:
    keywords: list[str] = []

    for keyword in department.get(K_KEYWORDS) or []:
        keyword_text = str(keyword).strip()
        if keyword_text and keyword_text not in keywords:
            keywords.append(keyword_text)

    for division in get_divisions(department).values():
        for keyword in division.get(K_KEYWORDS) or []:
            keyword_text = str(keyword).strip()
            if keyword_text and keyword_text not in keywords:
                keywords.append(keyword_text)

        for team in get_teams(division).values():
            for keyword in team.get(K_KEYWORDS) or []:
                keyword_text = str(keyword).strip()
                if keyword_text and keyword_text not in keywords:
                    keywords.append(keyword_text)

    return keywords


def collect_department_services(department: dict[str, Any]) -> list[str]:
    services: list[str] = []

    for service in department.get(K_SERVICES) or []:
        service_text = str(service).strip()
        if service_text and service_text not in services:
            services.append(service_text)

    for division in get_divisions(department).values():
        for service in division.get(K_SERVICES) or []:
            service_text = str(service).strip()
            if service_text and service_text not in services:
                services.append(service_text)

        for team in get_teams(division).values():
            for service in team.get(K_SERVICES) or []:
                service_text = str(service).strip()
                if service_text and service_text not in services:
                    services.append(service_text)

    return services


def format_organization_path(department: dict[str, Any]) -> str:
    group_name = department.get("department_group_name")
    department_name = department.get(K_NAME)

    if group_name and department_name:
        return f"{group_name} > {department_name}"

    return str(department_name or "")
