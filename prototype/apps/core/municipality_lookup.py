"""Lookup-Helfer für kommunale Organisationsdaten in den Streamlit-Apps.

Das Modul stellt bewusst nur lesende Zugriffe bereit und hält die fachliche
Zuständigkeitsstruktur in der YAML-Konfiguration.
"""

from __future__ import annotations

from typing import Any


def get_departments(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    departments: dict[str, dict[str, Any]] = {}

    for group_id, group in (config.get("department_groups") or {}).items():
        if not isinstance(group, dict):
            continue

        for department_id, department in (group.get("departments") or {}).items():
            if not isinstance(department, dict):
                continue

            normalized = dict(department)
            normalized.setdefault("department_group_id", group_id)
            normalized.setdefault("department_group_name", group.get("name", group_id))
            departments[str(department_id)] = normalized

    if departments:
        return departments

    return {
        str(team_id): team
        for team_id, team in (config.get("teams") or {}).items()
        if isinstance(team, dict)
    }


def get_department(config: dict[str, Any], department_id: str | None) -> dict[str, Any] | None:
    if not department_id:
        return None

    return get_departments(config).get(str(department_id))


def get_department_display_name(config: dict[str, Any], department_id: str | None) -> str | None:
    department = get_department(config, department_id)
    if not department:
        return department_id

    return department.get("public_label") or department.get("name") or department_id


def get_department_email(config: dict[str, Any], department_id: str | None) -> str | None:
    department = get_department(config, department_id)
    if not department:
        return None

    return department.get("email")
