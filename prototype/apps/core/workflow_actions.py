"""Workflow-Aktionen für manuelle Steuerung im Operations-Prototyp.

Die Funktionen aktualisieren Fallstatus, Routing, Team-Review und simulierte
Versandaktionen, ohne Pipeline-Entscheidungen im UI-Code zu verstecken.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

CURRENT_FILE = Path(__file__).resolve()
LOCAL_PROTOTYPE_DIR = next(parent for parent in CURRENT_FILE.parents if parent.name == "prototype")
LOCAL_PROJECT_ROOT = LOCAL_PROTOTYPE_DIR.parent

for path in [LOCAL_PROJECT_ROOT, LOCAL_PROTOTYPE_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prototype.shared.bootstrap import ensure_project_import_paths

ensure_project_import_paths(__file__)

from apps.core.store import load_cases, update_case
from apps.core.mail.email_sender import send_internal_team_forward, send_final_reply_to_citizen
from apps.core.municipality_lookup import get_department, get_department_display_name, get_department_email
from apps.core.mail.email_addresses import normalize_email_address
from prototype.shared.constants import ENCODING_UTF8
from prototype.shared.paths import DEFAULT_MUNICIPALITY_CONFIG_PATH


CONFIG_PATH = DEFAULT_MUNICIPALITY_CONFIG_PATH
ENCODING = ENCODING_UTF8

STATUS_TEAM_REVIEW_PENDING = "team_review_pending"
STATUS_NEEDS_MANUAL_ROUTING = "needs_manual_routing"
STATUS_SENT_TO_CITIZEN = "sent_to_citizen"
STATUS_ESCALATED = "escalated"
STATUS_DELETED = "deleted"

TEAM_REVIEW_PENDING = "pending"
TEAM_REVIEW_EDITED = "edited"
TEAM_REVIEW_APPROVED = "approved"
TEAM_REVIEW_SEND_ERROR = "send_error"
TEAM_REVIEW_REROUTE_REQUESTED = "reroute_requested"
TEAM_REVIEW_ESCALATED = "escalated"

DECISION_EDITED = "edited"
DECISION_SENT = "sent"
DECISION_SEND_ERROR = "send_error"
DECISION_REROUTE_REQUESTED = "reroute_requested"
DECISION_ESCALATED = "escalated"


def now_iso() -> str:
    return datetime.now().isoformat()


def load_municipality_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding=ENCODING)) or {}


def get_team_config(team_id: str | None) -> dict[str, Any] | None:
    if not team_id:
        return None

    config = load_municipality_config()
    return get_department(config, team_id)


def get_team_email(team_id: str | None) -> str | None:
    return get_department_email(load_municipality_config(), team_id)


def get_team_name(team_id: str | None) -> str | None:
    if not team_id:
        return None

    return get_department_display_name(load_municipality_config(), team_id)


def get_case_by_id(case_id: int) -> dict[str, Any] | None:
    for case in load_cases():
        if case.get("case_id") == case_id:
            return case

    return None


def require_case(case_id: int) -> dict[str, Any]:
    case = get_case_by_id(case_id)

    if not case:
        raise ValueError(f"Fall {case_id} wurde nicht gefunden.")

    return case


def build_initial_team_review() -> dict[str, Any]:
    return {
        "status": TEAM_REVIEW_PENDING,
        "reviewed_by": None,
        "reviewed_at": None,
        "decision": None,
        "edited_answer": None,
        "notes": "",
    }


def update_team_review(
        case: dict[str, Any],
        *,
        status: str,
        reviewed_by: str,
        decision: str,
        notes: str = "",
        edited_answer: str | None = None,
) -> dict[str, Any]:
    team_review = dict(case.get("team_review") or build_initial_team_review())

    team_review.update({
        "status": status,
        "reviewed_by": reviewed_by,
        "reviewed_at": now_iso(),
        "decision": decision,
        "notes": notes,
    })

    if edited_answer is not None:
        team_review["edited_answer"] = edited_answer

    return team_review


def build_internal_forward_state(team_email: str | None) -> dict[str, Any]:
    return {
        "sent": False,
        "to": team_email,
        "from": None,
        "subject": None,
        "body": None,
        "sent_at": None,
        "status": "not_attempted",
        "error": None,
    }


def build_internal_forward_update(forward_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "internal_forward": {
            "sent": forward_result.get("sent"),
            "to": normalize_email_address(forward_result.get("to")),
            "from": normalize_email_address(forward_result.get("from")),
            "subject": forward_result.get("subject"),
            "body": forward_result.get("body"),
            "sent_at": forward_result.get("sent_at"),
            "status": forward_result.get("status"),
            "error": forward_result.get("error"),
        }
    }


def build_citizen_reply_update(
        case: dict[str, Any],
        reply_result: dict[str, Any],
        final_answer: str,
) -> dict[str, Any]:
    citizen_reply = dict(case.get("citizen_reply") or {})

    citizen_reply.update({
        "sent": reply_result.get("sent"),
        "status": reply_result.get("status"),
        "from": normalize_email_address(reply_result.get("from")),
        "to": normalize_email_address(reply_result.get("to")),
        "subject": reply_result.get("subject"),
        "final_answer": final_answer,
        "sent_at": reply_result.get("sent_at"),
        "error": reply_result.get("error"),
    })

    return citizen_reply


def route_case_to_team(
        case_id: int,
        team_id: str,
        assigned_by: str = "control_dashboard",
        note: str = "",
) -> dict[str, Any] | None:
    team_email = get_team_email(team_id)

    if not team_email:
        raise ValueError(f"Keine E-Mail-Adresse für Team '{team_id}' gefunden.")

    updates = {
        "status": STATUS_TEAM_REVIEW_PENDING,
        "assigned_team": team_id,
        "assigned_email": team_email,
        "assigned_by": assigned_by,
        "review_note": note,
        "team_review": build_initial_team_review(),
        "internal_forward": build_internal_forward_state(team_email),
    }

    updated_case = update_case(case_id, updates)

    if not updated_case:
        raise ValueError(f"Fall {case_id} wurde nicht gefunden.")

    forward_result = send_internal_team_forward(updated_case)

    return update_case(
        case_id,
        build_internal_forward_update(forward_result),
    )


def save_edited_answer(
        case_id: int,
        edited_answer: str,
        reviewed_by: str = "fachteam",
        notes: str = "",
) -> dict[str, Any] | None:
    case = require_case(case_id)

    team_review = update_team_review(
        case,
        status=TEAM_REVIEW_EDITED,
        reviewed_by=reviewed_by,
        decision=DECISION_EDITED,
        notes=notes,
        edited_answer=edited_answer,
    )

    return update_case(case_id, {"team_review": team_review})


def approve_and_send_to_citizen(
        case_id: int,
        final_answer: str,
        reviewed_by: str = "fachteam",
        notes: str = "",
) -> dict[str, Any] | None:
    """
    Wird durch die Fachteam-Freigabe-App ausgelöst.
    Erst hier wird die finale Antwort an den Bürger versendet.
    """
    case = require_case(case_id)

    reply_result = send_final_reply_to_citizen(
        case=case,
        final_answer=final_answer,
    )

    reply_was_sent = bool(reply_result.get("sent"))

    team_review = update_team_review(
        case,
        status=TEAM_REVIEW_APPROVED if reply_was_sent else TEAM_REVIEW_SEND_ERROR,
        reviewed_by=reviewed_by,
        decision=DECISION_SENT if reply_was_sent else DECISION_SEND_ERROR,
        notes=notes,
        edited_answer=final_answer,
    )

    citizen_reply = build_citizen_reply_update(
        case=case,
        reply_result=reply_result,
        final_answer=final_answer,
    )

    new_status = (
        STATUS_SENT_TO_CITIZEN
        if reply_was_sent
        else STATUS_TEAM_REVIEW_PENDING
    )

    return update_case(
        case_id,
        {
            "status": new_status,
            "team_review": team_review,
            "citizen_reply": citizen_reply,
        },
    )


def return_case_to_control_dashboard(
        case_id: int,
        reviewed_by: str = "fachteam",
        notes: str = "",
) -> dict[str, Any] | None:
    case = require_case(case_id)

    team_review = update_team_review(
        case,
        status=TEAM_REVIEW_REROUTE_REQUESTED,
        reviewed_by=reviewed_by,
        decision=DECISION_REROUTE_REQUESTED,
        notes=notes,
    )

    return update_case(
        case_id,
        {
            "status": STATUS_NEEDS_MANUAL_ROUTING,
            "assigned_team": None,
            "assigned_email": None,
            "assigned_by": None,
            "team_review": team_review,
        },
    )


def escalate_case(
        case_id: int,
        escalated_by: str = "user",
        notes: str = "",
) -> dict[str, Any] | None:
    case = require_case(case_id)

    team_review = update_team_review(
        case,
        status=TEAM_REVIEW_ESCALATED,
        reviewed_by=escalated_by,
        decision=DECISION_ESCALATED,
        notes=notes,
    )

    return update_case(
        case_id,
        {
            "status": STATUS_ESCALATED,
            "team_review": team_review,
        },
    )


def delete_case_logically(
        case_id: int,
        deleted_by: str = "control_dashboard",
        notes: str = "",
) -> dict[str, Any] | None:
    """
    Löscht den Fall nicht physisch, sondern markiert ihn als gelöscht.
    Das ist für Nachvollziehbarkeit/Audit besser.
    """
    case = require_case(case_id)

    team_review = dict(case.get("team_review") or build_initial_team_review())
    team_review.update({
        "status": STATUS_DELETED,
        "reviewed_by": deleted_by,
        "reviewed_at": now_iso(),
        "decision": STATUS_DELETED,
        "notes": notes,
    })

    return update_case(
        case_id,
        {
            "status": STATUS_DELETED,
            "deleted_by": deleted_by,
            "deleted_at": now_iso(),
            "delete_note": notes,
            "team_review": team_review,
        },
    )
