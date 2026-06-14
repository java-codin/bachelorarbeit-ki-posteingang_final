"""Operations-Dashboard für den kommunalen Posteingangsprototyp.

Die Oberfläche zeigt eingegangene Fälle, Kontrollqueues, Worker-Status und
manuelle Routingaktionen für den Human-in-the-Loop-Betrieb.
"""

import sys
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import streamlit as st
import yaml

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


CURRENT_FILE = Path(__file__).resolve()
LOCAL_PROTOTYPE_DIR = next(parent for parent in CURRENT_FILE.parents if parent.name == "prototype")
LOCAL_PROJECT_ROOT = LOCAL_PROTOTYPE_DIR.parent

for path in [LOCAL_PROJECT_ROOT, LOCAL_PROTOTYPE_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prototype.shared.bootstrap import ensure_project_import_paths

ensure_project_import_paths(__file__)

from prototype.shared.constants import ENCODING_UTF8
from prototype.shared.paths import DEFAULT_MUNICIPALITY_CONFIG_PATH
from apps.core.ui_styles import apply_app_styles
from apps.core.table_filters import render_dataframe_filters
from apps.core.mail.mailpit_client import (
    MAILPIT_API_URL,
    MAILPIT_INBOX_ADDRESS,
    delete_all_mailpit_messages,
    get_inbox_messages,
)
from apps.core.municipality_lookup import get_departments
from apps.core.store import (
    factory_reset_operations_store,
    load_cases,
    load_processed_emails,
    load_worker_status,
    update_case,
)
from apps.core.workflow_actions import (
    delete_case_logically,
    escalate_case,
    route_case_to_team,
)
from src.v5.core.constants import RISK_REVIEW_THRESHOLD


CONFIG_PATH = DEFAULT_MUNICIPALITY_CONFIG_PATH
ENCODING = ENCODING_UTF8

STATUS_NEEDS_MANUAL_ROUTING = "needs_manual_routing"
STATUS_BLOCKED = "blocked"
STATUS_ESCALATED = "escalated"
STATUS_REROUTE_REQUESTED = "reroute_requested"
STATUS_TEAM_REVIEW_PENDING = "team_review_pending"
STATUS_SENT_TO_CITIZEN = "sent_to_citizen"
STATUS_DELETED = "deleted"
STATUS_CLOSED_UNASSIGNED = "closed_unassigned"

CONTROL_QUEUE_STATUSES = {
    STATUS_NEEDS_MANUAL_ROUTING,
    STATUS_BLOCKED,
    STATUS_ESCALATED,
    STATUS_REROUTE_REQUESTED,
}

TEAM_QUEUE_STATUSES = {
    STATUS_TEAM_REVIEW_PENDING,
    STATUS_SENT_TO_CITIZEN,
    STATUS_ESCALATED,
}

CLOSED_STATUSES = {
    STATUS_CLOSED_UNASSIGNED,
    STATUS_DELETED,
}

INBOX_FILTER_ALL = "Alle E-Mails"
INBOX_FILTER_PENDING = "Noch nicht verarbeitet"
INBOX_FILTER_PROCESSED = "Verarbeitet"
INBOX_FILTER_OPTIONS = [
    INBOX_FILTER_ALL,
    INBOX_FILTER_PENDING,
    INBOX_FILTER_PROCESSED,
]


st.set_page_config(
    page_title="Operativer KI-Posteingang",
    page_icon="📬",
    layout="wide",
)
apply_app_styles("operations_dashboard.css")


def render_ops_note(text: str) -> None:
    st.markdown(
        (
            "<div class='review-hero'>"
            f"<div class='review-hero-subtitle'>{escape(text)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_source_card(title: str, sources: Any) -> None:
    if not sources:
        body = "<div class='review-empty'>Keine Quellen vorhanden.</div>"
    elif isinstance(sources, list):
        items = "".join(f"<li>{escape(str(source))}</li>" for source in sources)
        body = f"<ul>{items}</ul>"
    else:
        body = escape(str(sources))

    st.markdown(
        (
            "<div class='mail-section-card'>"
            f"<div class='mail-section-title'>{escape(title)}</div>"
            f"{body}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def metric_display(value: Any, digits: int = 2) -> str:
    if value in [None, ""]:
        return "Keine Angabe"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def render_ops_tiles(tiles: list[dict[str, Any]]) -> None:
    tile_html = []

    for tile in tiles:
        tone = tile.get("tone") or "neutral"
        value = tile.get("value")
        display_value = "Keine Angabe" if value is None or value == "" else value
        tile_html.append(
            (
                f"<div class='review-tile review-tile-{escape(str(tone))}'>"
                f"<div class='review-tile-label'>{escape(str(tile.get('label') or ''))}</div>"
                f"<div class='review-tile-value'>{escape(str(display_value))}</div>"
                f"<div class='review-tile-caption'>{escape(str(tile.get('caption') or ''))}</div>"
                "</div>"
            )
        )

    st.markdown(
        f"<div class='review-tile-grid'>{''.join(tile_html)}</div>",
        unsafe_allow_html=True,
    )


def render_team_mailbox_header(team_name: str, email: str | None) -> None:
    email_value = email or "Keine Adresse hinterlegt"
    st.markdown(
        (
            "<div class='team-mailbox-header'>"
            "<div class='team-mailbox-main'>"
            f"<div class='team-mailbox-title'>{escape(team_name)}</div>"
            "<div class='team-mailbox-subtitle'>Fachbereichs-Postfach für interne Weiterleitungen</div>"
            "</div>"
            "<div class='team-mailbox-address'>"
            "<span class='team-mailbox-address-label'>Postfach</span>"
            f"<span class='ops-detail-chip'>{escape(email_value)}</span>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


DETAIL_LABELS = {
    "answer_completeness_label": "Abdeckung Label",
    "answer_completeness_reason": "Begründung",
    "answer_completeness_score": "Antwortabdeckung",
    "assigned_by": "Zugeordnet durch",
    "assigned_email": "Zieladresse",
    "assigned_team": "Zugeordnetes Team",
    "calibrated_confidence": "Kalibriertes Gesamtvertrauen",
    "covered_aspects": "Abgedeckte Aspekte",
    "from": "Absenderadresse",
    "guardrail_flags": "Guardrail-Hinweise",
    "human_review_reasons": "Gründe für Human Review",
    "human_review_required": "Human Review erforderlich",
    "missing_aspects": "Fehlende Aspekte",
    "predicted_team": "KI-Team",
    "processed_at": "Verarbeitet am",
    "recipients": "Empfänger",
    "requires_human_completion": "Fachliche Ergänzung erforderlich",
    "response_mode": "Antwortmodus",
    "review_note": "Kontrollnotiz",
    "risk_reasons": "Risikogründe",
    "risk_score": "Risk Score",
    "routing_status": "Routing-Status",
    "self_evaluation_issues": "Self-Evaluation Hinweise",
    "self_evaluation_passed": "Self-Evaluation bestanden",
    "sender": "Absender",
    "sender_address": "Absenderadresse",
    "subject": "Betreff",
    "target_email": "Ziel-E-Mail",
    "target_team": "Zielteam",
    "uncertain_aspects": "Unsichere Aspekte",
    "workflow_status": "Workflow-Status",
}


def format_detail_label(label: str) -> str:
    label_text = str(label)
    return DETAIL_LABELS.get(label_text, label_text.replace("_", " ").replace("-", " ").title())


def looks_like_email_address(value: str) -> bool:
    value_text = value.strip()
    return bool(value_text and "@" in value_text and "." in value_text.split("@")[-1])


def render_detail_value(value: Any) -> str:
    if value in [None, ""]:
        return "<span class='ops-muted-value'>-</span>"

    if isinstance(value, bool):
        return "Ja" if value else "Nein"

    if isinstance(value, list):
        if not value:
            return "<span class='ops-muted-value'>Keine Einträge</span>"

        if all(not isinstance(item, (dict, list)) for item in value):
            chips = "".join(
                f"<span class='ops-detail-chip'>{escape(str(item))}</span>"
                for item in value
            )
            return f"<div class='ops-detail-chip-row'>{chips}</div>"

        items = "".join(f"<li>{render_detail_value(item)}</li>" for item in value)
        return f"<ul class='ops-detail-list'>{items}</ul>"

    if isinstance(value, dict):
        if not value:
            return "<span class='ops-muted-value'>Keine Einträge</span>"

        items = "".join(
            (
                "<li>"
                f"<span class='ops-detail-inline-key'>{escape(format_detail_label(key))}:</span> "
                f"{render_detail_value(item)}"
                "</li>"
            )
            for key, item in value.items()
        )
        return f"<ul class='ops-detail-list'>{items}</ul>"

    if isinstance(value, str) and looks_like_email_address(value):
        return f"<span class='ops-detail-chip'>{escape(value)}</span>"

    return escape(str(value))


def normalize_display_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text


def render_preformatted_text(value: Any, class_name: str = "mail-body-card") -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return f"<pre class='{escape(class_name)}'>{escape(text)}</pre>"


def compact_design_data(data: dict[str, Any]) -> dict[str, Any]:
    compact = dict(data)

    compact.pop("body", None)

    if "status" in compact and "sent" in compact:
        compact.pop("sent", None)

    if compact.get("from") and compact.get("sender_address") == compact.get("from"):
        compact.pop("sender_address", None)

    return compact


def has_detail_content(value: Any) -> bool:
    if value is None or value == "":
        return False

    if isinstance(value, list):
        return any(has_detail_content(item) for item in value)

    if isinstance(value, dict):
        return any(has_detail_content(item) for item in value.values())

    return True


def detail_row_tone(key: str, value: Any) -> str:
    key_text = str(key).lower()
    field_name = key_text.rsplit(":", 1)[-1].strip()
    value_text = str(value).lower()

    if value in [None, "", [], {}]:
        return "neutral"

    if field_name == "subject":
        return "neutral"

    negative_when_true = {
        "human_review_required",
        "requires_human_completion",
        "escalation_required",
        "guardrail_triggered",
        "injection_detected",
        "no_answer_triggered",
    }

    positive_when_true = {
        "self_evaluation_passed",
        "sent",
        "success",
        "passed",
    }

    if isinstance(value, bool):
        if field_name in negative_when_true:
            return "danger" if value else "ok"

        if field_name in positive_when_true or field_name.endswith("_passed"):
            return "ok" if value else "danger"

        return "ok" if value else "neutral"

    if "error" in field_name:
        return "danger"

    if field_name in {"predicted_team", "target_team", "assigned_team", "ki-team", "zielteam"}:
        if value_text in {"unknown", "nicht zugeordnet", "unbekannt"}:
            return "danger"

    if (
            ("bürgerantwort" in key_text or key_text == "citizen_reply_status")
            and key_text.endswith("status")
            and value_text == "not_sent"
    ):
        return "warn"

    if field_name in {"risk_score"}:
        try:
            score = float(value)
            if score >= RISK_REVIEW_THRESHOLD:
                return "danger"
            if score > 0:
                return "warn"
            return "ok"
        except (TypeError, ValueError):
            return "neutral"

    if field_name in {"confidence", "calibrated_confidence"}:
        try:
            confidence = float(value)
            if confidence >= 0.75:
                return "ok"
            if confidence >= 0.45:
                return "warn"
            return "danger"
        except (TypeError, ValueError):
            return "neutral"

    if field_name in {"answer_completeness_score"}:
        try:
            completeness = float(value)
            if completeness >= 0.8:
                return "ok"
            if completeness >= 0.5:
                return "warn"
            return "danger"
        except (TypeError, ValueError):
            return "neutral"

    negative_terms = [
        "blocked",
        "danger",
        "deleted",
        "error",
        "failed",
        "fehler",
        "nicht bestanden",
        "nicht gesendet",
        "not_allowed",
        "not_attempted",
        "not attempted",
        "not_sent",
        "no_answer",
        "no answer",
        "sent_failed",
        "unzustellbar",
        "eskaliert",
    ]
    if any(word in value_text for word in negative_terms):
        return "danger"

    if any(word in value_text for word in ["review", "prüfen", "manual", "fallback", "warn"]):
        return "warn"

    if any(word in value_text for word in ["sent", "ok", "processed", "bestanden", "gesendet"]):
        return "ok"

    return "neutral"


def is_long_detail_field(key: str, value: Any) -> bool:
    key_text = str(key).lower()

    if key_text in {"body", "html", "text", "content", "message", "raw"}:
        return True

    if isinstance(value, str) and len(value) > 420:
        return True

    return False


def render_detail_card(title: str, data: dict[str, Any]) -> None:
    data = compact_design_data(data)
    visible_items = [
        (key, value)
        for key, value in data.items()
        if has_detail_content(value)
    ]
    compact_items = [
        (key, value)
        for key, value in visible_items
        if not is_long_detail_field(str(key), value)
    ]
    long_items = [
        (key, value)
        for key, value in visible_items
        if is_long_detail_field(str(key), value)
    ]

    st.markdown(f"### {title}")

    if not visible_items:
        st.markdown(
            "<div class='review-empty'>Keine Inhalte vorhanden.</div>",
            unsafe_allow_html=True,
        )
        return

    rows = "".join(
        (
            f"<div class='visual-row visual-row-{detail_row_tone(f'{title}:{key}', value)} visual-row-compact'>"
            "<div class='visual-row-main'>"
            f"<div class='visual-row-title'>{escape(format_detail_label(key))}</div>"
            f"<div class='visual-row-subtitle'>{render_detail_value(value)}</div>"
            "</div>"
            "</div>"
        )
        for key, value in compact_items
    )

    if rows:
        st.markdown(
            f"<div class='ops-detail-section'><div class='visual-row-list'>{rows}</div></div>",
            unsafe_allow_html=True,
        )

    for key, value in long_items:
        label = format_detail_label(str(key))
        with st.expander(f"{label} anzeigen", expanded=False):
            st.markdown(
                render_preformatted_text(value, "mail-body-card mail-body-intro"),
                unsafe_allow_html=True,
            )


def render_case_section(
        title: str,
        data: dict[str, Any],
        show_json: bool,
) -> None:
    if show_json:
        st.markdown(f"### {title}")
        st.json(data)
        return

    render_detail_card(title, data)


def render_detail_group(title: str, data: dict[str, Any]) -> None:
    data = compact_design_data(data)
    visible_items = [
        (key, value)
        for key, value in data.items()
        if has_detail_content(value)
    ]

    if not visible_items:
        return

    rows = "".join(
        (
            f"<div class='visual-row visual-row-{detail_row_tone(str(key), value)} visual-row-compact'>"
            "<div class='visual-row-main'>"
            f"<div class='visual-row-title'>{escape(format_detail_label(key))}</div>"
            f"<div class='visual-row-subtitle'>{render_detail_value(value)}</div>"
            "</div>"
            "</div>"
        )
        for key, value in visible_items
    )

    st.markdown(
        (
            f"<div class='ops-governance-group'>"
            f"<div class='mail-section-title'>{escape(title)}</div>"
            f"<div class='visual-row-list'>{rows}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_governance_section(result: dict[str, Any], show_json: bool) -> None:
    predicted_team = result.get("predicted_team")
    target_team = result.get("target_team")
    confidence = result.get("confidence")
    calibrated_confidence = result.get("calibrated_confidence")
    show_predicted_team = predicted_team and predicted_team != target_team
    show_routing_confidence = confidence not in [None, ""]
    governance_data = {
        "predicted_team": predicted_team,
        "target_team": target_team,
        "target_email": result.get("target_email"),
        "routing_status": result.get("routing_status"),
        "confidence": confidence,
        "calibrated_confidence": calibrated_confidence,
        "human_review_required": result.get("human_review_required"),
        "human_review_reasons": result.get("human_review_reasons"),
        "response_mode": result.get("response_mode"),
        "workflow_status": result.get("workflow_status"),
        "risk_score": result.get("risk_score"),
        "risk_reasons": result.get("risk_reasons"),
        "guardrail_flags": result.get("guardrail_flags"),
        "self_evaluation_passed": result.get("self_evaluation_passed"),
        "self_evaluation_issues": result.get("self_evaluation_issues"),
        "answer_completeness_score": result.get("answer_completeness_score"),
        "answer_completeness_label": result.get("answer_completeness_label"),
        "answer_completeness_reason": result.get("answer_completeness_reason"),
        "covered_aspects": result.get("covered_aspects"),
        "missing_aspects": result.get("missing_aspects"),
        "uncertain_aspects": result.get("uncertain_aspects"),
        "requires_human_completion": result.get("requires_human_completion"),
    }

    if show_json:
        render_case_section("KI-Routing und Governance", governance_data, show_json)
        return

    st.markdown("### KI-Routing und Governance")

    render_ops_tiles([
        {
            "label": "Zielteam",
            "value": result.get("target_team") or result.get("predicted_team"),
            "caption": "Fachliche Zielzuordnung aus Klassifikation und Routing.",
            "tone": detail_row_tone("routing_status", result.get("routing_status")),
        },
        {
            "label": "Gesamtvertrauen",
            "value": metric_display(result.get("calibrated_confidence") or result.get("confidence")),
            "caption": (
                "Kalibriertes Vertrauenssignal über Routing, Risiko, "
                "Antwortabdeckung und Review-Auslöser."
            ),
            "tone": detail_row_tone("confidence", result.get("calibrated_confidence") or result.get("confidence")),
        },
        {
            "label": "Review",
            "value": "Erforderlich" if result.get("human_review_required") else "Nicht erforderlich",
            "caption": "Zeigt, ob eine menschliche Prüfung ausgelöst wurde.",
            "tone": detail_row_tone("human_review_required", result.get("human_review_required")),
        },
        {
            "label": "Risiko",
            "value": result.get("risk_score"),
            "caption": "Aggregierter Governance- und Sicherheitsindikator.",
            "tone": detail_row_tone("risk_score", result.get("risk_score")),
        },
    ])

    col_left, col_right = st.columns(2)

    with col_left:
        render_detail_group(
            "Routing-Entscheidung",
            {
                "predicted_team": predicted_team if show_predicted_team else None,
                "target_team": target_team,
                "target_email": result.get("target_email"),
                "routing_status": result.get("routing_status"),
                "confidence": confidence if show_routing_confidence else None,
            },
        )
        render_detail_group(
            "Workflow und Review",
            {
                "calibrated_confidence": calibrated_confidence,
                "human_review_required": result.get("human_review_required"),
                "human_review_reasons": result.get("human_review_reasons"),
                "requires_human_completion": result.get("requires_human_completion"),
            },
        )

    with col_right:
        render_detail_group(
            "Risiko und Schutzmechanismen",
            {
                "risk_score": result.get("risk_score"),
                "risk_reasons": result.get("risk_reasons"),
                "guardrail_flags": result.get("guardrail_flags"),
                "self_evaluation_passed": result.get("self_evaluation_passed"),
                "self_evaluation_issues": result.get("self_evaluation_issues"),
            },
        )
        render_detail_group(
            "Antwortabdeckung",
            {
                "answer_completeness_score": result.get("answer_completeness_score"),
                "answer_completeness_reason": result.get("answer_completeness_reason"),
                "covered_aspects": result.get("covered_aspects"),
                "missing_aspects": result.get("missing_aspects"),
                "uncertain_aspects": result.get("uncertain_aspects"),
            },
        )


def render_citizen_request_section(
        case: dict[str, Any],
        metadata: dict[str, Any],
        show_json: bool,
) -> None:
    request_data = {
        "subject": metadata.get("subject"),
        "sender": metadata.get("sender"),
        "from": metadata.get("from") or metadata.get("sender_address"),
        "sender_address": metadata.get("sender_address"),
        "recipients": metadata.get("recipients"),
        "processed_at": metadata.get("processed_at"),
        "text": case.get("text"),
    }

    if show_json:
        st.markdown("### Bürgeranliegen")
        st.json(request_data)
        return

    compact_data = {
        key: value
        for key, value in request_data.items()
        if key != "text"
    }

    render_detail_card("Bürgeranliegen", compact_data)

    if has_detail_content(case.get("text")):
        with st.expander("Anliegentext anzeigen", expanded=False):
            st.markdown(
                (
                    "<div class='mail-body-card mail-body-intro'>"
                    f"{escape(normalize_display_text(case.get('text')))}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )


def render_case_overview(case: dict[str, Any], result: dict[str, Any]) -> None:
    processing_time = result.get("processing_time_seconds")
    try:
        processing_time_value = f"{float(processing_time):.2f} s"
    except (TypeError, ValueError):
        processing_time_value = "Keine Angabe"

    confidence = result.get("confidence")
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        confidence_float = None

    status = case.get("status")
    status_tone = detail_row_tone("status", status)
    confidence_tone = (
        "ok"
        if confidence_float is not None and confidence_float >= 0.75
        else "warn"
        if confidence_float is not None and confidence_float >= 0.45
        else "neutral"
    )

    st.markdown("### Fallübersicht")
    render_ops_tiles([
        {
            "label": "KI-Team",
            "value": result.get("predicted_team"),
            "caption": "Erste fachliche Zuordnung aus der Klassifikation.",
            "tone": "neutral",
        },
        {
            "label": "Confidence",
            "value": metric_display(confidence),
            "caption": "Modellvertrauen für die vorgeschlagene Zuordnung.",
            "tone": confidence_tone,
        },
        {
            "label": "Fallstatus",
            "value": status,
            "caption": "Aktueller Bearbeitungsstand im operativen Workflow.",
            "tone": status_tone,
        },
        {
            "label": "Bearbeitungszeit",
            "value": processing_time_value,
            "caption": "Gemessene Pipeline-Laufzeit für den erzeugten Fall.",
            "tone": "neutral",
        },
    ])


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding=ENCODING)) or {}


def get_teams(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        department_id: {
            "name": department.get("public_label") or department.get("name", department_id),
            "email": department.get("email"),
        }
        for department_id, department in get_departments(config).items()
    }


def get_result(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("result") or {}


def get_email_metadata(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("email_metadata") or {}


def get_status_mail(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("status_mail") or {}


def get_internal_forward(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("internal_forward") or {}


def get_team_review(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("team_review") or {}


def get_citizen_reply(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("citizen_reply") or {}


def get_team_display_name(
        team_id: str | None,
        teams: dict[str, dict[str, Any]],
) -> str:
    if team_id in [None, "", "unknown"]:
        return "Nicht zugeordnet"

    if team_id in teams:
        return teams[team_id].get("name", team_id)

    return str(team_id)


def cases_with_status(
        cases: list[dict[str, Any]],
        statuses: set[str],
) -> list[dict[str, Any]]:
    return [
        case for case in cases
        if case.get("status") in statuses
    ]


def flatten_case(case: dict[str, Any]) -> dict[str, Any]:
    result = get_result(case)
    metadata = get_email_metadata(case)

    return {
        "case_id": case.get("case_id"),
        "status": case.get("status"),
        "subject": metadata.get("subject"),
        "sender": metadata.get("sender"),
        "assigned_team": case.get("assigned_team"),
        "assigned_email": case.get("assigned_email"),
        "assigned_by": case.get("assigned_by"),
        "version": case.get("version"),
        "predicted_team": result.get("predicted_team"),
        "target_team": result.get("target_team"),
        "confidence": result.get("confidence"),
        "response_mode": result.get("response_mode"),
        "risk_score": result.get("risk_score"),
        "human_review_required": result.get("human_review_required"),
        "answer_completeness_score": result.get("answer_completeness_score"),
        "answer_completeness_label": result.get("answer_completeness_label"),
        "requires_human_completion": result.get("requires_human_completion"),
        "status_mail_status": get_status_mail(case).get("status"),
        "internal_forward_status": get_internal_forward(case).get("status"),
        "team_review_status": get_team_review(case).get("status"),
        "citizen_reply_status": get_citizen_reply(case).get("status"),
        "processing_time_seconds": result.get("processing_time_seconds"),
        "created_at": case.get("created_at"),
    }


def render_cases_table(
        cases: list[dict[str, Any]],
        empty_message: str = "Keine Fälle vorhanden.",
) -> None:
    if not cases:
        st.info(empty_message)
        return

    render_sortable_dataframe(
        pd.DataFrame([flatten_case(case) for case in cases]),
        key=None,
    )


def render_sortable_dataframe(
        df: pd.DataFrame,
        key: str | None = None,
) -> Any:
    return st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        key=key,
    )


def filter_cases_for_table(
        cases: list[dict[str, Any]],
        *,
        key_prefix: str,
        title: str,
) -> list[dict[str, Any]]:
    if not cases:
        return []

    cases_df = pd.DataFrame([flatten_case(case) for case in cases])
    filtered_df = render_dataframe_filters(
        cases_df,
        key_prefix=key_prefix,
        title=title,
        excluded_columns={"case_id"},
        column_label_formatter=format_detail_label,
        visible_item_label="Fällen"
    )
    filtered_case_ids = set(filtered_df["case_id"].tolist())

    return [
        case for case in cases
        if case.get("case_id") in filtered_case_ids
    ]


def render_selectable_cases_table(
        cases: list[dict[str, Any]],
        key: str,
        empty_message: str = "Keine Fälle vorhanden.",
        selection_message: str = "Fall in der Tabelle auswählen, um Details zu öffnen.",
) -> dict[str, Any] | None:
    if not cases:
        st.info(empty_message)
        return None

    cases_df = pd.DataFrame([flatten_case(case) for case in cases])
    table_event = st.dataframe(
        cases_df,
        width="stretch",
        hide_index=True,
        key=key,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = table_event.selection.rows

    if not selected_rows:
        st.info(selection_message)
        return None

    selected_index = selected_rows[0]
    if selected_index >= len(cases_df):
        st.info(selection_message)
        return None

    selected_case_id = cases_df.iloc[selected_index]["case_id"]

    return next(
        (
            case for case in cases
            if case.get("case_id") == selected_case_id
        ),
        None,
    )


def render_worker_status() -> None:
    try:
        worker_status = load_worker_status()
    except Exception as exc:
        st.error(f"Worker-Status konnte nicht gelesen werden: {exc}")
        return

    state = worker_status.get("state")

    render_ops_tiles([
        {
            "label": "Worker Status",
            "value": state,
            "caption": "Aktueller Zustand des E-Mail-Workers.",
            "tone": detail_row_tone("worker_state", state),
        },
        {
            "label": "Letzter Fall",
            "value": worker_status.get("last_case_id"),
            "caption": "Zuletzt erzeugte oder aktualisierte Fallreferenz.",
            "tone": "neutral",
        },
        {
            "label": "Bearbeitungsstatus",
            "value": worker_status.get("last_status"),
            "caption": "Letzter gemeldeter Verarbeitungsschritt.",
            "tone": detail_row_tone("last_status", worker_status.get("last_status")),
        },
        {
            "label": "Aktuelle Mail",
            "value": worker_status.get("current_subject"),
            "caption": "Betreff der aktuell verarbeiteten Nachricht.",
            "tone": "neutral",
        },
    ])

    message = worker_status.get("message")

    if state == "processing":
        st.info(message or "E-Mail wird verarbeitet.")
    elif state == "processed":
        st.success(message or "E-Mail wurde verarbeitet.")
    elif state == "error":
        st.error(message or "Fehler im Worker.")

        if worker_status.get("last_error"):
            st.code(worker_status.get("last_error"))
    else:
        st.caption(message or "Worker wartet auf neue E-Mails.")

    if worker_status.get("updated_at"):
        st.caption(f"Zuletzt aktualisiert: {worker_status.get('updated_at')}")


def render_case_detail(
        case: dict[str, Any],
        key_prefix: str = "case_detail",
) -> None:
    result = get_result(case)
    metadata = get_email_metadata(case)
    internal_forward = get_internal_forward(case)
    team_review = get_team_review(case)
    citizen_reply = get_citizen_reply(case)
    status_mail = get_status_mail(case)
    show_json = st.toggle(
        "Technische JSON-Ansicht anzeigen",
        value=False,
        key=f"{key_prefix}_json_view_{case.get('case_id', 'unknown')}",
        help="Wechselt die Fallabschnitte zwischen gestalteter Dashboard-Ansicht und Rohdaten als JSON.",
    )

    render_case_overview(case, result)
    render_citizen_request_section(case, metadata, show_json)

    render_case_section("Statusmail an Bürger", status_mail, show_json)

    render_case_section("Interne Weiterleitung an Fachbereich", internal_forward, show_json)
    render_case_section("Fachbereichs-Freigabe", team_review, show_json)
    render_case_section("Bürgerantwort", citizen_reply, show_json)

    render_case_section(
        "Operative Zuordnung",
        {
            "assigned_team": case.get("assigned_team"),
            "assigned_email": case.get("assigned_email"),
            "assigned_by": case.get("assigned_by"),
            "review_note": case.get("review_note"),
        },
        show_json,
    )

    render_governance_section(result, show_json)

    st.markdown("### KI-Antwortentwurf")
    answer = str(result.get("draft_answer") or result.get("answer") or "").strip()

    if answer:
        st.markdown(
            (
                "<div class='mail-section-card'>"
                "<pre class='mail-section-body answer-draft-body'>"
                f"{escape(answer)}"
                "</pre>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.warning("Kein Antwortentwurf vorhanden.")

    st.markdown("### Quellen")
    col1, col2 = st.columns(2)

    with col1:
        render_source_card("Retrieved Sources", result.get("retrieved_sources", []))

    with col2:
        render_source_card("Used Sources", result.get("used_sources", []))


def render_header(cases: list[dict[str, Any]]) -> None:
    st.title("📬 Operativer KI-Posteingang")
    st.markdown(
        (
            "<div class='review-hero'>"
            "<div class='review-hero-title'>Kommunaler KI-Posteingang im Kontrollbetrieb</div>"
            "<div class='review-hero-subtitle'>"
            "Eingang überwachen, unklare oder kritische Fälle prüfen, "
            "manuell an Fachbereiche verteilen, löschen oder eskalieren."
            "</div>"
            "<div class='review-badge-row'>"
            "<span class='review-badge'>Human-in-the-Loop</span>"
            "<span class='review-badge'>Routing-Kontrolle</span>"
            "<span class='review-badge'>Quellengebundene Entwürfe</span>"
            "<span class='review-badge'>Auditierbarer Workflow</span>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.divider()

    render_ops_tiles([
        {
            "label": "Gesamtfälle",
            "value": len(cases),
            "caption": "Alle operativ gespeicherten Fälle.",
            "tone": "neutral",
        },
        {
            "label": "Kontroll-Queue",
            "value": len(cases_with_status(cases, CONTROL_QUEUE_STATUSES)),
            "caption": "Fälle mit zentralem Prüf- oder Klärungsbedarf.",
            "tone": "warn" if cases_with_status(cases, CONTROL_QUEUE_STATUSES) else "ok",
        },
        {
            "label": "Fachbereichs-Freigaben",
            "value": len(cases_with_status(cases, {STATUS_TEAM_REVIEW_PENDING})),
            "caption": "Offene fachliche Freigaben in den Teams.",
            "tone": "warn" if cases_with_status(cases, {STATUS_TEAM_REVIEW_PENDING}) else "ok",
        },
        {
            "label": "Antworten gesendet",
            "value": len(cases_with_status(cases, {STATUS_SENT_TO_CITIZEN})),
            "caption": "Abgeschlossene Bürgerantworten.",
            "tone": "ok",
        },
        {
            "label": "Gelöscht",
            "value": len(cases_with_status(cases, {STATUS_DELETED})),
            "caption": "Logisch entfernte operative Fälle.",
            "tone": "neutral",
        },
    ])

    st.divider()


def build_case_by_mailpit_id(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    case_by_mailpit_id = {}

    for case in cases:
        mailpit_id = get_email_metadata(case).get("mailpit_id")

        if mailpit_id:
            case_by_mailpit_id[mailpit_id] = case

    return case_by_mailpit_id


def build_inbox_rows(
        inbox_messages: list[dict[str, Any]],
        processed_emails: list[str],
        cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_by_mailpit_id = build_case_by_mailpit_id(cases)
    processed_email_keys = set(processed_emails)
    rows = []

    for message in inbox_messages:
        mailpit_id = message["message_id"]
        processed_key = f"mailpit:{mailpit_id}"
        related_case = case_by_mailpit_id.get(mailpit_id)
        is_processed = processed_key in processed_email_keys

        rows.append({
            "Mailpit-ID": mailpit_id,
            "Betreff": message["subject"],
            "Absender": message["sender"],
            "Empfänger": ", ".join(message["recipients"]),
            "Bearbeitungsstatus": (
                "verarbeitet"
                if is_processed
                else "wartet auf Worker"
            ),
            "Fall-ID": related_case.get("case_id") if related_case else None,
            "Fallstatus": related_case.get("status") if related_case else None,
            "Eingang": message["created"],
            "_processed": is_processed,
        })

    return rows


def filter_inbox_rows(
        rows: list[dict[str, Any]],
        inbox_filter: str,
) -> list[dict[str, Any]]:
    if inbox_filter == INBOX_FILTER_PENDING:
        return [row for row in rows if not row["_processed"]]

    if inbox_filter == INBOX_FILTER_PROCESSED:
        return [row for row in rows if row["_processed"]]

    return rows


def display_inbox_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in row.items()
            if not key.startswith("_")
        }
        for row in rows
    ]


def find_case_by_id(
        cases: list[dict[str, Any]],
        case_id: Any,
) -> dict[str, Any] | None:
    return next(
        (
            case for case in cases
            if str(case.get("case_id")) == str(case_id)
        ),
        None,
    )


def set_browser_title(title: str) -> None:
    st.html(
        "<script>"
        f"window.parent.document.title = {repr(title)};"
        "</script>",
        unsafe_allow_javascript=True,
    )


def render_direct_case_view(cases: list[dict[str, Any]], case_id: str) -> None:
    selected_case = find_case_by_id(cases, case_id)

    st.title("Fallansicht")

    if st.button("Zurück zum Dashboard"):
        st.query_params.clear()
        st.rerun()

    if selected_case is None:
        set_browser_title(f"Detailansicht Fall: {case_id}")
        st.error(f"Fall {case_id} wurde nicht gefunden.")
        return

    set_browser_title(f"Detailansicht Fall: {selected_case.get('case_id')}")

    st.caption(
        "Direktansicht der vollständigen Fallakte. "
        "Diese Ansicht ist für Verweise aus dem E-Mail-Eingang gedacht."
    )
    st.divider()
    render_case_detail(selected_case, key_prefix="direct_case_detail")


def render_inbox_tab(cases: list[dict[str, Any]]) -> None:
    st.subheader("E-Mail-Eingang")

    render_ops_tiles([
        {
            "label": "Überwachte Adresse",
            "value": MAILPIT_INBOX_ADDRESS,
            "caption": "Inbox, die durch den Worker beobachtet wird.",
            "tone": "neutral",
        },
        {
            "label": "Mailpit API",
            "value": MAILPIT_API_URL.replace("/api/v1", ""),
            "caption": "Lokaler Mailpit-Endpunkt für die Demo.",
            "tone": "neutral",
        },
    ])

    if st.button("Jetzt aktualisieren"):
        st.rerun()

    auto_refresh = st.toggle(
        "Automatisch aktualisieren",
        value=True,
        help="Aktualisiert regelmäßig Inbox, Worker-Status und Bearbeitungsstatus.",
    )

    if auto_refresh:
        if st_autorefresh is not None:
            st_autorefresh(interval=5000, key="mailpit_inbox_refresh")
        else:
            st.warning("Für Auto-Refresh bitte installieren: `pip install streamlit-autorefresh`")

    st.divider()
    st.markdown("### Bearbeitungsstatus")
    render_worker_status()

    st.divider()
    st.markdown("### Inbox der überwachten Mailadresse")

    try:
        inbox_messages = get_inbox_messages(limit=500)
        processed_emails = load_processed_emails()
    except Exception as exc:
        st.error("Mailpit-Inbox konnte nicht geladen werden.")
        st.code(f"{type(exc).__name__}: {exc}")
        inbox_messages = []
        processed_emails = []

    if "known_mailpit_message_ids" not in st.session_state:
        st.session_state["known_mailpit_message_ids"] = set()

    current_message_ids = {
        message["message_id"]
        for message in inbox_messages
    }

    new_message_ids = current_message_ids - st.session_state["known_mailpit_message_ids"]

    if new_message_ids and st.session_state["known_mailpit_message_ids"]:
        st.toast(
            f"{len(new_message_ids)} neue E-Mail(s) im überwachten Postfach gefunden.",
            icon="📬",
        )
        st.success(
            f"{len(new_message_ids)} neue E-Mail(s) gefunden. "
            "Der Worker verarbeitet diese automatisch."
        )

    st.session_state["known_mailpit_message_ids"] = current_message_ids

    if not inbox_messages:
        st.info("Keine E-Mails für die überwachte Adresse vorhanden.")
        return

    inbox_rows = build_inbox_rows(inbox_messages, processed_emails, cases)
    pending_count = len([row for row in inbox_rows if not row["_processed"]])
    processed_count = len([row for row in inbox_rows if row["_processed"]])

    render_ops_tiles([
        {
            "label": "Inbox gesamt",
            "value": len(inbox_rows),
            "caption": "Geladene Nachrichten der überwachten Adresse.",
            "tone": "neutral",
        },
        {
            "label": "Noch nicht verarbeitet",
            "value": pending_count,
            "caption": "Mails, die der Worker noch nicht als verarbeitet markiert hat.",
            "tone": "warn" if pending_count else "ok",
        },
        {
            "label": "Verarbeitet",
            "value": processed_count,
            "caption": "Mails mit Verarbeitungseintrag im Operations-Store.",
            "tone": "ok" if processed_count else "neutral",
        },
    ])

    inbox_filter = st.radio(
        "Inbox filtern",
        INBOX_FILTER_OPTIONS,
        horizontal=True,
        key="operations_inbox_processing_filter",
    )
    filtered_rows = filter_inbox_rows(inbox_rows, inbox_filter)

    if not filtered_rows:
        st.info("Für diesen Filter sind aktuell keine E-Mails vorhanden.")
        return

    inbox_df = pd.DataFrame(display_inbox_rows(filtered_rows))
    inbox_event = st.dataframe(
        inbox_df,
        width="stretch",
        hide_index=True,
        key="operations_inbox_table",
        on_select="rerun",
        selection_mode="single-row",
    )

    st.divider()

    selected_rows = inbox_event.selection.rows

    if not selected_rows:
        st.info("E-Mail in der Tabelle auswählen, um die Vorschau zu öffnen.")
        return

    selected_index = selected_rows[0]
    if selected_index >= len(inbox_df):
        st.info("E-Mail in der Tabelle auswählen, um die Vorschau zu öffnen.")
        return

    selected_row = inbox_df.iloc[selected_index]
    selected_mail_id = selected_row["Mailpit-ID"]
    case_by_mailpit_id = build_case_by_mailpit_id(cases)

    selected_message = next(
        message for message in inbox_messages
        if message["message_id"] == selected_mail_id
    )

    st.markdown("### Maildetails")
    preview_fields = [
        ("Betreff", selected_message["subject"]),
        ("Absender", selected_message["sender"]),
        ("Absenderadresse", selected_message.get("from") or selected_message.get("sender_address")),
        ("Empfänger", ", ".join(selected_message["recipients"])),
        ("Eingang", selected_message["created"]),
    ]
    preview_html = "".join(
        (
            "<div class='mail-field'>"
            f"<div class='mail-field-label'>{escape(label)}</div>"
            f"<div class='mail-field-value'>{escape(str(value))}</div>"
            "</div>"
        )
        for label, value in preview_fields
    )
    st.markdown(
        (
            "<div class='mail-card'>"
            "<div class='mail-card-title'>Ausgewählte E-Mail</div>"
            f"<div class='mail-field-grid'>{preview_html}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    related_case = case_by_mailpit_id.get(selected_mail_id)

    if related_case:
        result = get_result(related_case)
        internal_forward = get_internal_forward(related_case)
        st.markdown("### Verknüpfter Fall")
        render_ops_tiles([
            {
                "label": "Fall-ID",
                "value": related_case.get("case_id"),
                "caption": "Eindeutige Referenz für die Detailansicht.",
                "tone": "neutral",
            },
            {
                "label": "Fallstatus",
                "value": related_case.get("status"),
                "caption": "Aktueller Workflow-Status des erzeugten Falls.",
                "tone": detail_row_tone("status", related_case.get("status")),
            },
            {
                "label": "KI-Team",
                "value": result.get("predicted_team"),
                "caption": "Erste fachliche Zuordnung aus der Klassifikation.",
                "tone": "neutral",
            },
            {
                "label": "Weiterleitung",
                "value": internal_forward.get("status"),
                "caption": "Status der internen Arbeitspaket-Mail.",
                "tone": detail_row_tone("internal_forward_status", internal_forward.get("status")),
            },
        ])
        render_ops_note(
            "Die vollständige Fallansicht ist in den Reitern „Alle Fälle“, "
            "„Kontroll-Queue“ oder „Fachbereichs-Queue“ verfügbar. "
            "Der E-Mail-Eingang zeigt nur Informationen mit direktem Bezug zur ausgewählten Mail."
        )
        case_id = related_case.get("case_id")
        if case_id:
            st.link_button(
                "Vollständige Fallansicht öffnen",
                f"?case_id={quote(str(case_id))}",
                type="primary",
            )
    else:
        st.warning(
            "Für diese E-Mail wurde noch kein Fall erzeugt. "
            "Der Worker hat sie entweder noch nicht verarbeitet oder ist nicht gestartet."
        )


def render_control_queue_tab(
        teams: dict[str, dict[str, Any]],
) -> None:
    st.subheader("Kontroll-Queue")
    render_ops_note(
        "Diese Queue enthält Fälle, die nicht automatisch an einen Fachbereich "
        "weitergeleitet wurden, z. B. wegen unklarer Zuordnung, Human Review, "
        "Prompt-Injection, Eskalation oder Routing-/Quellenkonflikt."
    )

    current_cases = load_cases()
    control_cases = cases_with_status(current_cases, CONTROL_QUEUE_STATUSES)

    if not control_cases:
        st.success("Aktuell gibt es keine offenen Fälle im Kontrolldashboard.")
        return

    filtered_control_cases = filter_cases_for_table(
        control_cases,
        key_prefix="operations_control_queue_filters_v1",
        title="Kontroll-Queue filtern",
    )

    selected_case = render_selectable_cases_table(
        filtered_control_cases,
        key="operations_control_queue_table",
        empty_message="Für die aktuelle Filterauswahl liegen keine Fälle in der Kontroll-Queue vor.",
        selection_message="Fall in der Kontroll-Queue auswählen, um Prüfung und Entscheidung zu öffnen.",
    )

    if selected_case is None:
        return

    st.divider()
    render_case_detail(selected_case, key_prefix="control_queue_case_detail")

    st.divider()
    st.markdown("### Zentrale Entscheidung")

    team_options = list(teams.keys())

    if not team_options:
        st.error("Es sind keine Fachbereiche in der Konfiguration hinterlegt.")
        return

    suggested_team = (
        selected_case.get("result", {}).get("target_team")
        or selected_case.get("result", {}).get("predicted_team")
    )
    suggested_team_label = get_team_display_name(suggested_team, teams)

    render_ops_tiles([
        {
            "label": "Vorgeschlagenes Ziel",
            "value": suggested_team_label,
            "caption": (
                "KI-Vorschlag aus Klassifikation und Routing. In der Kontroll-Queue "
                "darf dieser Vorschlag bewusst bestätigt oder überschrieben werden."
            ),
            "tone": "neutral" if suggested_team in team_options else "warn",
        },
        {
            "label": "Zielteam auswählen",
            "value": "Manuelle Prüfung",
            "caption": (
                "Bestimmt, in welcher Fachbereichs-Queue der Fall anschließend zur "
                "fachlichen Prüfung und Freigabe erscheint."
            ),
            "tone": "ok",
        },
        {
            "label": "Kontrollnotiz",
            "value": "Audit-Hinweis",
            "caption": (
                "Dokumentiert kurz, warum die manuelle Zuordnung vorgenommen wurde. "
                "Das unterstützt Nachvollziehbarkeit und Human Oversight."
            ),
            "tone": "neutral",
        },
    ])

    default_index = (
        team_options.index(suggested_team)
        if suggested_team in team_options
        else 0
    )

    with st.form(f"manual_routing_form_{selected_case['case_id']}"):
        manual_team = st.selectbox(
            "Zielteam auswählen",
            team_options,
            index=int(default_index),
            format_func=lambda team_id: get_team_display_name(team_id, teams),
            help=(
                "Dieser Fachbereich erhält den Fall als offene Freigabe. "
                "Der KI-Vorschlag kann hier manuell korrigiert werden."
            ),
        )

        review_note = st.text_area(
            "Kontrollnotiz",
            value="Manuelle Prüfung im Kontrolldashboard durchgeführt.",
            height=120,
            help=(
                "Kurze Begründung für die Kontrollentscheidung. "
                "Die Notiz wird am Fall gespeichert."
            ),
        )

        route_clicked = st.form_submit_button(
            "An Fachbereich weiterleiten",
            type="primary",
            help=(
                "Speichert Zielteam und Kontrollnotiz und verschiebt den Fall "
                "in die passende Fachbereichs-Queue."
            ),
        )

    if route_clicked:
        try:
            updated_case = route_case_to_team(
                case_id=selected_case["case_id"],
                team_id=manual_team,
                assigned_by="control_dashboard",
                note=review_note,
            )

            st.success(
                f"Fall wurde an {get_team_display_name(updated_case.get('assigned_team'), teams)} "
                "weitergeleitet und erscheint jetzt in der Fachbereichs-Freigabe-App."
            )
            st.rerun()

        except Exception as exc:
            st.error("Fall konnte nicht weitergeleitet werden.")
            st.code(f"{type(exc).__name__}: {exc}")

    st.divider()

    st.markdown("### Weitere Aktionen")
    render_ops_tiles([
        {
            "label": "Fall löschen",
            "value": "Ausblenden",
            "caption": (
                "Markiert den Fall logisch als gelöscht. Der Fall bleibt für die "
                "Nachvollziehbarkeit gespeichert, erscheint aber nicht mehr in den "
                "offenen Arbeitsqueues."
            ),
            "tone": "danger",
        },
        {
            "label": "Fall eskalieren",
            "value": "Sonderprüfung",
            "caption": (
                "Setzt den Fall auf Eskalation, wenn er organisatorisch, fachlich "
                "oder rechtlich nicht im normalen Kontrollprozess geklärt werden soll."
            ),
            "tone": "warn",
        },
        {
            "label": "Nicht zuordenbar schließen",
            "value": "Abschluss",
            "caption": (
                "Schließt den Fall ohne Fachbereichs-Zuordnung. Geeignet für Eingänge, "
                "die auch nach manueller Prüfung keinem kommunalen Zuständigkeitsbereich "
                "zugeordnet werden können."
            ),
            "tone": "neutral",
        },
    ])

    col_delete, col_escalate, col_close = st.columns(3)

    with col_delete:
        if st.button(
                "Fall löschen",
                key=f"delete_{selected_case['case_id']}",
                help="Markiert den Fall logisch als gelöscht und entfernt ihn aus den offenen Arbeitsqueues.",
        ):
            delete_case_logically(
                case_id=selected_case["case_id"],
                deleted_by="control_dashboard",
                notes="Fall wurde im Kontrolldashboard gelöscht.",
            )
            st.warning("Fall wurde gelöscht.")
            st.rerun()

    with col_escalate:
        if st.button(
                "Fall eskalieren",
                key=f"escalate_{selected_case['case_id']}",
                help="Setzt den Fall auf Eskalation für eine gesonderte organisatorische oder fachliche Klärung.",
        ):
            escalate_case(
                case_id=selected_case["case_id"],
                escalated_by="control_dashboard",
                notes="Fall wurde im Kontrolldashboard eskaliert.",
            )
            st.warning("Fall wurde eskaliert.")
            st.rerun()

    with col_close:
        if st.button(
                "Als nicht zuordenbar schließen",
                key=f"close_unassigned_{selected_case['case_id']}",
                help=(
                    "Schließt den Fall ohne Fachbereichs-Zuordnung, wenn keine sinnvolle "
                    "kommunale Zuständigkeit bestimmt werden kann."
                ),
        ):
            update_case(
                selected_case["case_id"],
                {
                    "status": STATUS_CLOSED_UNASSIGNED,
                    "assigned_team": "unknown",
                    "assigned_email": None,
                    "assigned_by": "control_dashboard",
                    "review_note": "Fall wurde als nicht zuordenbar geschlossen.",
                },
            )
            st.warning("Fall wurde als nicht zuordenbar geschlossen.")
            st.rerun()


def render_team_queue_tab(
        teams: dict[str, dict[str, Any]],
) -> None:
    st.subheader("Fachbereichs-Queues")
    render_ops_note(
        "Diese Ansicht zeigt ausschließlich die Postfächer der Fachbereiche. "
        "Die fachliche Prüfung, Bearbeitung und Freigabe der Antwort erfolgt "
        "in der separaten Fachbereichs-Freigabe-App."
    )

    st.link_button(
        "Fachbereichs-Freigabe-App öffnen",
        "http://localhost:8503",
    )

    current_cases = load_cases()
    mailbox_tabs = st.tabs([
        teams[team_id]["name"]
        for team_id in teams
    ])

    for index, team_id in enumerate(teams.keys()):
        with mailbox_tabs[index]:
            team_cases = [
                case for case in current_cases
                if case.get("assigned_team") == team_id
                and case.get("status") in TEAM_QUEUE_STATUSES
            ]

            render_team_mailbox_header(
                teams[team_id]["name"],
                teams[team_id].get("email"),
            )

            open_count = len(cases_with_status(team_cases, {STATUS_TEAM_REVIEW_PENDING}))
            sent_count = len(cases_with_status(team_cases, {STATUS_SENT_TO_CITIZEN}))

            render_ops_tiles([
                {
                    "label": "Offene Freigaben",
                    "value": open_count,
                    "caption": "Fälle, die im Fachbereich geprüft werden müssen.",
                    "tone": "warn" if open_count else "ok",
                },
                {
                    "label": "Gesendete Antworten",
                    "value": sent_count,
                    "caption": "Vom Fachbereich freigegebene und gesendete Antworten.",
                    "tone": "ok",
                },
                {
                    "label": "Alle Fachbereichsfälle",
                    "value": len(team_cases),
                    "caption": "Aktuelle Fälle in dieser Fachbereichs-Queue.",
                    "tone": "neutral",
                },
            ])

            if not team_cases:
                st.info("Keine Fälle in diesem Postfach.")
                continue

            filtered_team_cases = filter_cases_for_table(
                team_cases,
                key_prefix=f"operations_team_queue_filters_v1_{team_id}",
                title=f"{teams[team_id]['name']} filtern",
            )

            selected_case = render_selectable_cases_table(
                filtered_team_cases,
                key=f"operations_team_queue_table_{team_id}",
                empty_message="Für die aktuelle Filterauswahl liegen keine Fälle in diesem Postfach vor.",
                selection_message="Fall in der Fachbereichs-Queue auswählen, um Details zu öffnen.",
            )

            if selected_case is None:
                continue

            render_case_detail(selected_case, key_prefix=f"team_queue_case_detail_{team_id}")


def render_all_cases_tab() -> None:
    st.subheader("Alle Vorgänge")

    all_cases = load_cases()

    if not all_cases:
        st.info("Noch keine Fälle vorhanden.")
        return

    filtered_cases = filter_cases_for_table(
        all_cases,
        key_prefix="operations_all_cases_filters_v2",
        title="Alle Fälle filtern",
    )

    selected_case = render_selectable_cases_table(
        filtered_cases,
        key="operations_all_cases_table",
        empty_message="Für die aktuelle Filterauswahl liegen keine Fälle vor.",
        selection_message="Fall in der Tabelle auswählen, um die Detailansicht zu öffnen.",
    )

    if selected_case is None:
        return

    st.divider()
    render_case_detail(selected_case, key_prefix="all_cases_detail")


def render_admin_tab() -> None:
    st.subheader("Administration")
    st.warning(
        "Der Factory Reset löscht alle operativen Fälle, Kennzahlen, "
        "verarbeitete E-Mail-IDs, Worker-Statusdaten, lokale Cache-Dateien "
        "und alle E-Mails aus Mailpit."
    )

    confirm_reset = st.checkbox(
        "Ich bestätige, dass alle Daten der operativen E-Mail-Applikation gelöscht werden sollen."
    )

    if st.button(
            "Factory Reset ausführen",
            type="primary",
            disabled=not confirm_reset,
    ):
        reset_results = []

        try:
            mailpit_result = delete_all_mailpit_messages()
            reset_results.append(mailpit_result["message"])
        except Exception as exc:
            reset_results.append(
                f"Mailpit konnte nicht vollständig geleert werden: {type(exc).__name__}: {exc}"
            )

        try:
            store_result = factory_reset_operations_store()
            reset_results.append(store_result["message"])
        except Exception as exc:
            reset_results.append(
                f"Lokaler Store konnte nicht vollständig zurückgesetzt werden: {type(exc).__name__}: {exc}"
            )

        try:
            st.cache_data.clear()
            st.cache_resource.clear()
            reset_results.append("Streamlit-Cache wurde geleert.")
        except Exception as exc:
            reset_results.append(
                f"Streamlit-Cache konnte nicht vollständig geleert werden: {type(exc).__name__}: {exc}"
            )

        for result_message in reset_results:
            st.write(f"- {result_message}")

        st.success("Factory Reset wurde ausgeführt.")
        st.session_state.clear()
        st.rerun()


def main() -> None:
    config = load_config()
    teams = get_teams(config)
    cases = load_cases()

    direct_case_id = st.query_params.get("case_id")

    if direct_case_id:
        render_direct_case_view(cases, str(direct_case_id))
        return

    render_header(cases)

    tab_inbox, tab_control, tab_team_queues, tab_all_cases, tab_admin = st.tabs([
        "E-Mail-Eingang",
        "Kontroll-Queue",
        "Fachbereichs-Queue",
        "Alle Fälle",
        "Administration",
    ])

    with tab_inbox:
        render_inbox_tab(cases)

    with tab_control:
        render_control_queue_tab(teams)

    with tab_team_queues:
        render_team_queue_tab(teams)

    with tab_all_cases:
        render_all_cases_tab()

    with tab_admin:
        render_admin_tab()


if __name__ == "__main__":
    main()
