"""Fachbereichs-Review-Oberfläche für Antwortentwürfe und Weiterleitungen.

Die App bildet den Human-Oversight-Schritt ab: Entwürfe können geprüft,
bearbeitet, freigegeben, zurückgegeben oder eskaliert werden.
"""

import sys
import re
from email.utils import parseaddr
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


CURRENT_FILE = Path(__file__).resolve()
LOCAL_PROTOTYPE_DIR = next(parent for parent in CURRENT_FILE.parents if parent.name == "prototype")
LOCAL_PROJECT_ROOT = LOCAL_PROTOTYPE_DIR.parent

for path in [LOCAL_PROJECT_ROOT, LOCAL_PROTOTYPE_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prototype.shared.bootstrap import ensure_project_import_paths

ensure_project_import_paths(__file__)

from apps.core.municipality_lookup import get_departments
from apps.core.ui_styles import apply_app_styles
from apps.core.store import load_cases
from apps.core.table_filters import render_dataframe_filters
from apps.core.workflow_actions import (
    approve_and_send_to_citizen,
    escalate_case,
    get_team_name,
    load_municipality_config,
    return_case_to_control_dashboard,
    save_edited_answer,
)
from apps.core.mail.email_sender import (
    build_internal_forward_body,
    build_internal_forward_subject,
)
from prototype.shared.paths import DEFAULT_KNOWLEDGE_BASE_PATH
from src.v5.chunking.structure_chunking import create_chunks
from src.v5.knowledge_loader import load_knowledge_base


STATUS_TEAM_REVIEW_PENDING = "team_review_pending"
STATUS_SENT_TO_CITIZEN = "sent_to_citizen"

DEFAULT_REVIEWER_ROLE = "Mitarbeiter"


st.set_page_config(
    page_title="Fachbereichs-Freigabe",
    page_icon="✅",
    layout="wide",
)


apply_app_styles("team_review.css")


def get_result(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("result") or {}


def get_email_metadata(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("email_metadata") or {}


def get_team_review(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("team_review") or {}


def get_citizen_reply(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("citizen_reply") or {}


def get_internal_forward(case: dict[str, Any] | None) -> dict[str, Any]:
    if not case:
        return {}

    return case.get("internal_forward") or {}


def get_draft_answer(case: dict[str, Any]) -> str:
    team_review = get_team_review(case)
    edited_answer = team_review.get("edited_answer")

    if edited_answer:
        return edited_answer

    result = get_result(case)
    return result.get("draft_answer") or result.get("answer") or ""


def get_sender(case: dict[str, Any]) -> str:
    return get_email_metadata(case).get("sender") or "Unbekannt"


def sender_display_name(sender: str | None, sender_address: str | None = None) -> str:
    if not sender:
        return "Unbekannt"

    parsed_name, parsed_address = parseaddr(sender)

    if parsed_name:
        return parsed_name

    if sender_address and sender.strip().lower() == sender_address.strip().lower():
        return "Unbekannt"

    if parsed_address and parsed_address == sender:
        return "Unbekannt"

    return sender


def get_subject(case: dict[str, Any]) -> str:
    return get_email_metadata(case).get("subject") or "Ohne Betreff"


def display_team_name(team_id: str | None) -> str:
    if not team_id:
        return "Nicht zugeordnet"

    if team_id == "unknown":
        return "Nicht eindeutig"

    return get_team_name(team_id) or team_id


def get_review_teams(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        department_id: {
            "name": department.get("public_label") or department.get("name", department_id),
            "email": department.get("email"),
        }
        for department_id, department in get_departments(config).items()
    }


def display_result_team(result: dict[str, Any]) -> str:
    return display_team_name(result.get("predicted_team"))


def display_result_division(result: dict[str, Any]) -> str:
    return (
        result.get("matched_subteam_name")
        or result.get("matched_subteam")
        or "Nicht ausgewiesen"
    )


def display_result_unit_team(result: dict[str, Any]) -> str:
    return (
        result.get("matched_team_name")
        or result.get("matched_team")
        or "Nicht ausgewiesen"
    )


def display_table_metric(value: Any, digits: int = 2) -> Any:
    if value in (None, ""):
        return "Keine Angabe"

    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def display_table_bool(value: Any) -> str:
    if value is True:
        return "Ja"

    if value is False:
        return "Nein"

    return "Keine Angabe"


def display_category_name(category_id: Any) -> str:
    if not category_id:
        return "-"

    category = str(category_id)
    display_name = display_team_name(category)

    if display_name in {"Nicht zugeordnet", "Nicht eindeutig"}:
        return category

    return display_name


def reviewer_name_for_team(team_id: str) -> str:
    team_name = display_team_name(team_id)
    return f"{team_name} {DEFAULT_REVIEWER_ROLE}"


def get_open_cases_for_team(
        cases: list[dict[str, Any]],
        team_id: str,
) -> list[dict[str, Any]]:
    return [
        case for case in cases
        if case.get("assigned_team") == team_id
        and case.get("status") == STATUS_TEAM_REVIEW_PENDING
    ]


def get_sent_cases_for_team(
        cases: list[dict[str, Any]],
        team_id: str,
) -> list[dict[str, Any]]:
    return [
        case for case in cases
        if case.get("assigned_team") == team_id
        and case.get("status") == STATUS_SENT_TO_CITIZEN
    ]


def get_all_cases_for_team(
        cases: list[dict[str, Any]],
        team_id: str,
) -> list[dict[str, Any]]:
    return [
        case for case in cases
        if case.get("assigned_team") == team_id
    ]


def metric_value(value: Any, digits: int = 3) -> Any:
    if value is None:
        return "-"

    if isinstance(value, float):
        return round(value, digits)

    return value


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return sorted(value)

    return [value]


def preview_text(value: Any, limit: int = 420) -> str:
    text = str(value or "").strip()

    if len(text) <= limit:
        return text

    return f"{text[:limit].rstrip()}..."


def bool_text(value: Any) -> str:
    if value is True:
        return "Ja"

    if value is False:
        return "Nein"

    return "Keine Angabe"


def count_label(count: int, singular: str, plural: str | None = None) -> str:
    if plural is None:
        plural = f"{singular}n"

    noun = singular if count == 1 else plural
    return f"{count} {noun}"


REASON_LABELS = {
    "low_confidence": "niedrige Klassifikationssicherheit",
    "low_classification_confidence": "niedrige Klassifikationssicherheit",
    "unknown_team": "kein eindeutiges Fachteam",
    "prompt_injection_detected": "Manipulationsversuch im Bürgertext",
    "no_answer_triggered": "keine belastbare Antwortgrundlage",
    "guardrail_flags": "Guardrail-Hinweis",
    "incomplete_answer": "unvollständiger Antwortentwurf",
    "answer_too_short": "Antwortentwurf ist sehr kurz",
    "missing_sources": "Quellenbindung unvollständig",
    "no_retrieved_sources": "keine Informationsgrundlagen gefunden",
    "no_used_sources": "keine Informationsgrundlagen im Entwurf genutzt",
    "invalid_source_ids": "unzulässige Quellenreferenz",
    "security_block_active": "Sicherheitsblock aktiv",
    "self_evaluation_failed": "interne Qualitätsprüfung nicht bestanden",
    "too_few_retrieved_chunks": "wenige Retrieval-Treffer",
}


def readable_items(value: Any) -> list[str]:
    items = []

    for item in as_list(value):
        if item is None:
            continue

        key = str(item)
        items.append(REASON_LABELS.get(key, key.replace("_", " ")))

    return items


def join_readable(value: Any, fallback: str = "Keine Auffälligkeiten.") -> str:
    items = readable_items(value)

    if not items:
        return fallback

    return "; ".join(items)


def oversight_hint(result: dict[str, Any]) -> str:
    reasons = readable_items(result.get("human_review_reasons"))

    if not result.get("human_review_required"):
        return "Der Fall kann regulär geprüft werden; keine zusätzliche Kontrollstufe wurde ausgelöst."

    if reasons:
        return (
            "Bitte Zuständigkeit, Antwortentwurf und Quellen besonders prüfen. "
            f"Auslöser: {'; '.join(reasons)}."
        )

    return "Bitte den Fall fachlich freigeben, bevor eine Antwort an den Bürger versendet wird."


def escalation_hint(result: dict[str, Any]) -> str:
    risk_reasons = readable_items(result.get("risk_reasons"))

    if result.get("escalation_required"):
        if risk_reasons:
            return (
                "Bitte nicht ohne weitere Klärung freigeben. "
                f"Relevante Risikohinweise: {'; '.join(risk_reasons)}."
            )

        return "Bitte zentrale Klärung oder Rückgabe an das Kontrolldashboard prüfen."

    return "Keine Eskalation vorgesehen; eine normale Fachprüfung reicht voraussichtlich aus."


def generation_hint(result: dict[str, Any]) -> str:
    if result.get("policy_allows_generation"):
        return "Ein Antwortentwurf durfte erzeugt werden; Inhalt und Tonalität bleiben vor Versand fachlich zu prüfen."

    return "Die Policy erlaubt keinen normalen Antwortentwurf; bitte Fallback, Rückfrage oder manuelle Bearbeitung prüfen."


def injection_details(result: dict[str, Any]) -> str:
    if result.get("injection_detected"):
        reasoning = result.get("injection_reasoning")
        patterns = join_readable(result.get("injection_patterns"), fallback="")

        if reasoning and patterns:
            return f"{reasoning} Erkannte Muster: {patterns}."

        return reasoning or f"Erkannte Muster: {patterns}." or "Der Bürgertext enthält eine potenzielle Manipulationsanweisung."

    return "Keine Anzeichen, dass der Bürgertext Systemregeln überschreiben oder interne Anweisungen beeinflussen soll."


def no_answer_details(result: dict[str, Any]) -> str:
    if result.get("no_answer_triggered"):
        return "Das System hat keine ausreichend belastbare Informationsgrundlage für eine reguläre Antwort erkannt."

    return "Das Retrieval lieferte grundsätzlich verwertbare Informationsgrundlagen für den Antwortentwurf."


def guardrail_details(result: dict[str, Any]) -> str:
    flags = join_readable(result.get("guardrail_flags"), fallback="")

    if result.get("guardrail_triggered"):
        return f"Bitte den Antwortentwurf gezielt prüfen. Hinweise: {flags or 'Guardrail wurde ausgelöst'}."

    return "Keine formalen Guardrail-Auffälligkeiten im erzeugten Antwortentwurf."


def self_evaluation_details(result: dict[str, Any]) -> str:
    issues = join_readable(result.get("self_evaluation_issues"), fallback="")

    if result.get("self_evaluation_passed"):
        return "Die interne Qualitätsprüfung sieht keine wesentlichen Auffälligkeiten."

    return f"Bitte Antwort und Quellen besonders prüfen. Hinweise: {issues or 'interne Qualitätsprüfung nicht bestanden'}."


def render_source_list(title: str, values: list[Any]) -> None:
    st.markdown(f"**{title}**")

    if not values:
        st.info("Keine Einträge vorhanden.")
        return

    for value in values:
        st.write(f"- {value}")


def render_review_header(
        title: str,
        subtitle: str,
        badges: list[str] | None = None,
) -> None:
    badge_html = "".join(
        f"<span class='review-badge'>{escape(str(badge))}</span>"
        for badge in (badges or [])
    )

    st.markdown(
        (
            "<div class='review-hero'>"
            f"<div class='review-hero-title'>{escape(title)}</div>"
            f"<div class='review-hero-subtitle'>{escape(subtitle)}</div>"
            f"<div class='review-badge-row'>{badge_html}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_review_tiles(tiles: list[dict[str, Any]]) -> None:
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


def render_visual_source_overview(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("Keine Quelleninformationen vorhanden.")
        return

    html_rows = []

    for row in rows:
        is_used = row.get("Status") == "genutzt"
        tone = "ok" if is_used else "neutral"
        html_rows.append(
            (
                f"<div class='visual-row visual-row-{tone}'>"
                "<div class='visual-row-main'>"
                f"<div class='visual-row-title'>{escape(str(row.get('Quelle') or 'Unbekannte Quelle'))}</div>"
                f"<div class='visual-row-subtitle'>{escape(str(row.get('Hinweis') or ''))}</div>"
                "</div>"
                "<div class='visual-row-meta'>"
                f"<span>{escape(str(row.get('Status') or '-'))}</span>"
                f"<span>{escape(str(row.get('Kategorie') or '-'))}</span>"
                f"<span>{escape(count_label(int(row.get('Chunks') or 0), 'Chunk', 'Chunks'))}</span>"
                "</div>"
                "</div>"
            )
        )

    st.markdown(
        f"<div class='visual-row-list'>{''.join(html_rows)}</div>",
        unsafe_allow_html=True,
    )


def build_source_overview_rows(
        retrieved_sources: list[Any],
        used_sources: list[Any],
        retrieved_chunks: list[Any],
) -> list[dict[str, Any]]:
    source_names = sorted({
        str(source)
        for source in [*retrieved_sources, *used_sources]
        if source
    })
    used_source_names = {str(source) for source in used_sources if source}
    rows = []

    for source_name in source_names:
        source_chunks = [
            chunk for chunk in retrieved_chunks
            if isinstance(chunk, dict) and str(chunk.get("source")) == source_name
        ]
        categories = sorted({
            display_category_name(chunk.get("category"))
            for chunk in source_chunks
            if chunk.get("category")
        })
        is_used = source_name in used_source_names

        rows.append({
            "Quelle": source_name,
            "Status": "genutzt" if is_used else "nur gefunden",
            "Kategorie": ", ".join(categories) or "-",
            "Chunks": len(source_chunks),
            "Hinweis": (
                "Diese Quelle ist Grundlage des Antwortentwurfs."
                if is_used
                else "Diese Quelle wurde gefunden, aber nicht im Entwurf verwendet."
            ),
        })

    return rows


def grouped_chunks_by_source(chunks: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue

        source = str(chunk.get("source") or "Unbekannte Quelle")
        grouped.setdefault(source, []).append(chunk)

    return dict(sorted(grouped.items()))


def render_visual_checklist(rows: list[dict[str, Any]], title_key: str) -> None:
    if not rows:
        return

    html_rows = []

    for row in rows:
        status = str(row.get("Status") or "Keine Angabe")
        status_lower = status.lower()

        if any(word in status_lower for word in ["nicht erkannt", "nicht ausgelöst", "bestanden", "nicht erforderlich", "nein"]):
            tone = "ok"
        elif any(word in status_lower for word in ["erkannt", "ausgelöst", "prüfen", "erforderlich", "ja"]):
            tone = "warn"
        else:
            tone = "neutral"

        title = row.get(title_key) or row.get("Prüfpunkt") or row.get("Prüfung") or "Prüfung"
        html_rows.append(
            (
                f"<div class='visual-row visual-row-{tone}'>"
                "<div class='visual-row-main'>"
                f"<div class='visual-row-title'>{escape(str(title))}</div>"
                f"<div class='visual-row-subtitle'>{escape(str(row.get('Konkreter Prüfhinweis') or ''))}</div>"
                "</div>"
                "<div class='visual-row-meta'>"
                f"<span>{escape(status)}</span>"
                f"<span>{escape(str(row.get('Einordnung') or '-'))}</span>"
                "</div>"
                "</div>"
            )
        )

    st.markdown(
        f"<div class='visual-row-list'>{''.join(html_rows)}</div>",
        unsafe_allow_html=True,
    )


def render_visual_chunk_overview(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    html_rows = []

    for row in rows:
        html_rows.append(
            (
                "<div class='visual-row visual-row-neutral visual-row-compact'>"
                "<div class='visual-row-main'>"
                f"<div class='visual-row-title'>{escape(str(row.get('Abschnitt') or row.get('Chunk-ID') or 'Chunk'))}</div>"
                f"<div class='visual-row-subtitle'>{escape(str(row.get('Auszug') or ''))}</div>"
                "</div>"
                "<div class='visual-row-meta'>"
                f"<span>{escape(str(row.get('Quelle') or '-'))}</span>"
                f"<span>{escape(str(row.get('Kategorie') or '-'))}</span>"
                "</div>"
                "</div>"
            )
        )

    st.markdown(
        f"<div class='visual-row-list'>{''.join(html_rows)}</div>",
        unsafe_allow_html=True,
    )


def html_lines(text: Any) -> str:
    return escape(str(text or "")).replace("\n", "<br>")


def render_mail_header_card(title: str, fields: list[tuple[str, Any]]) -> None:
    field_html = []

    for label, value in fields:
        display_value = value if value not in (None, "") else "Keine Angabe"
        field_html.append(
            (
                "<div class='mail-field'>"
                f"<div class='mail-field-label'>{escape(str(label))}</div>"
                f"<div class='mail-field-value'>{escape(str(display_value))}</div>"
                "</div>"
            )
        )

    st.markdown(
        (
            "<div class='mail-card'>"
            f"<div class='mail-card-title'>{escape(title)}</div>"
            f"<div class='mail-field-grid'>{''.join(field_html)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def split_numbered_mail_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    lines = body.splitlines()
    intro_lines = []
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if re.match(r"^\d+\.\s+\S", line.strip()):
            if current_title is not None:
                sections.append((current_title, current_lines))
            else:
                intro_lines = current_lines

            current_title = line.strip()
            current_lines = []
            continue

        if current_title is None:
            current_lines.append(line)
        else:
            if set(line.strip()) <= {"-"}:
                continue
            current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, current_lines))
    else:
        intro_lines = current_lines

    cleaned_sections = [
        (title, "\n".join(section_lines).strip())
        for title, section_lines in sections
    ]

    return "\n".join(intro_lines).strip(), cleaned_sections


def render_mail_body(body: str, structured: bool = False) -> None:
    if not body.strip():
        st.info("Kein Mailinhalt vorhanden.")
        return

    if not structured:
        st.markdown(
            (
                "<div class='mail-body-card'>"
                f"{html_lines(body)}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    intro, sections = split_numbered_mail_sections(body)

    if intro:
        st.markdown(
            (
                "<div class='mail-body-card mail-body-intro'>"
                f"{html_lines(intro)}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    if not sections:
        st.markdown(
            (
                "<div class='mail-body-card'>"
                f"{html_lines(body)}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    for title, content in sections:
        st.markdown(
            (
                "<div class='mail-section-card'>"
                f"<div class='mail-section-title'>{escape(title)}</div>"
                f"<div class='mail-section-body'>{html_lines(content)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def status_tone(value: bool | None) -> str:
    if value is True:
        return "warn"

    if value is False:
        return "ok"

    return "neutral"


def knowledge_base_fingerprint(path: Path) -> float:
    if not path.exists():
        return 0.0

    mtimes = [
        file_path.stat().st_mtime
        for file_path in path.rglob("*.md")
        if file_path.name.lower() != "readme.md"
    ]

    return max(mtimes) if mtimes else path.stat().st_mtime


@st.cache_data(show_spinner=False)
def load_v5_chunks_by_id(
        knowledge_base_path: str,
        fingerprint: float,
) -> dict[str, dict[str, Any]]:
    documents = load_knowledge_base(Path(knowledge_base_path))
    chunks = create_chunks(documents)

    return {
        chunk.get("chunk_id"): chunk
        for chunk in chunks
        if isinstance(chunk, dict) and chunk.get("chunk_id")
    }


def resolve_retrieved_chunks_from_ids(chunk_ids: list[Any]) -> list[dict[str, Any]]:
    if not chunk_ids:
        return []

    chunks_by_id = load_v5_chunks_by_id(
        str(DEFAULT_KNOWLEDGE_BASE_PATH),
        knowledge_base_fingerprint(DEFAULT_KNOWLEDGE_BASE_PATH),
    )

    return [
        chunks_by_id[chunk_id]
        for chunk_id in chunk_ids
        if isinstance(chunk_id, str) and chunk_id in chunks_by_id
    ]


def render_case_summary(case: dict[str, Any]) -> None:
    result = get_result(case)
    metadata = get_email_metadata(case)
    case_id = case.get("case_id") or "-"
    subject = metadata.get("subject") or "Ohne Betreff"

    render_review_header(
        f"Fall {case_id}: {subject}",
        "Fachliche Prüfung des KI-gestützten Arbeitspakets vor einer möglichen Antwortfreigabe.",
        badges=[
            f"Fallstatus: {case.get('status') or 'Keine Angabe'}",
            f"Fachbereich: {display_result_team(result)}",
            f"Workflow: {result.get('workflow_status') or 'Keine Angabe'}",
        ],
    )


def render_governance(case: dict[str, Any]) -> None:
    result = get_result(case)

    human_review_required = result.get("human_review_required")
    escalation_required = result.get("escalation_required")
    guardrail_triggered = result.get("guardrail_triggered")
    injection_detected = result.get("injection_detected")
    no_answer_triggered = result.get("no_answer_triggered")
    self_eval_passed = result.get("self_evaluation_passed")
    completeness_score = result.get("answer_completeness_score")
    completeness_label = result.get("answer_completeness_label") or "Keine Angabe"

    if escalation_required:
        decision_summary = "Zentrale Klärung oder Rückgabe prüfen"
    elif human_review_required:
        decision_summary = "Fachliche Prüfung vor Freigabe erforderlich"
    else:
        decision_summary = "Reguläre Fachprüfung ohne zusätzliche Eskalation"

    render_review_header(
        "Governance & Kontrolllogik",
        decision_summary,
        badges=[
            f"Workflow: {result.get('workflow_status') or 'keine Angabe'}",
            f"Response Mode: {result.get('response_mode') or 'keine Angabe'}",
            f"Risk Score: {metric_value(result.get('risk_score'), digits=2)}",
        ],
    )

    render_review_tiles([
        {
            "label": "Human Review",
            "value": "Erforderlich" if human_review_required else "Nicht erforderlich",
            "caption": join_readable(
                result.get("human_review_reasons"),
                fallback="Keine zusätzliche Kontrollstufe.",
            ),
            "tone": "warn" if human_review_required else "ok",
        },
        {
            "label": "Eskalation",
            "value": "Erforderlich" if escalation_required else "Nicht erforderlich",
            "caption": join_readable(
                result.get("risk_reasons"),
                fallback="Kein erhöhter Risikohinweis.",
            ),
            "tone": "danger" if escalation_required else "ok",
        },
        {
            "label": "Ergebnisvertrauen",
            "value": metric_value(result.get("calibrated_confidence"), digits=2),
            "caption": "Gesamtbewertung aus Klassifikation, Quellen, Risiko und Antwortabdeckung.",
            "tone": "neutral",
        },
        {
            "label": "Antwortabdeckung",
            "value": f"{metric_value(completeness_score, digits=2)} ({completeness_label})",
            "caption": "Einschätzung, ob der Entwurf das Anliegen inhaltlich abdeckt.",
            "tone": "ok" if isinstance(completeness_score, float) and completeness_score >= 0.8 else "warn",
        },
    ])

    st.divider()
    st.markdown("#### Entscheidung und Aufsicht")
    decision_rows = [
        {
            "Prüfpunkt": "Human Review erforderlich",
            "Status": bool_text(result.get("human_review_required")),
            "Einordnung": join_readable(
                result.get("human_review_reasons"),
                fallback="Standardmäßige fachliche Freigabe.",
            ),
            "Konkreter Prüfhinweis": oversight_hint(result),
        },
        {
            "Prüfpunkt": "Eskalation erforderlich",
            "Status": bool_text(result.get("escalation_required")),
            "Einordnung": join_readable(
                result.get("risk_reasons"),
                fallback="Kein erhöhter Risikohinweis.",
            ),
            "Konkreter Prüfhinweis": escalation_hint(result),
        },
        {
            "Prüfpunkt": "Antwortgenerierung erlaubt",
            "Status": bool_text(result.get("policy_allows_generation")),
            "Einordnung": f"Routing-Status: {result.get('routing_status') or 'keine Angabe'}",
            "Konkreter Prüfhinweis": generation_hint(result),
        },
    ]
    render_visual_checklist(decision_rows, title_key="Prüfpunkt")

    st.markdown("#### Sicherheits- und Qualitätsprüfungen")
    render_review_tiles([
        {
            "label": "Prompt Injection",
            "value": "Erkannt" if injection_detected else "Nicht erkannt",
            "caption": "Bewertet, ob der Bürgertext Systemanweisungen manipulieren soll.",
            "tone": "danger" if injection_detected else "ok",
        },
        {
            "label": "No-Answer",
            "value": "Ausgelöst" if no_answer_triggered else "Nicht ausgelöst",
            "caption": "Zeigt, ob die Informationsgrundlage für eine reguläre Antwort reicht.",
            "tone": "warn" if no_answer_triggered else "ok",
        },
        {
            "label": "Guardrails",
            "value": "Auffällig" if guardrail_triggered else "Unauffällig",
            "caption": join_readable(
                result.get("guardrail_flags"),
                fallback="Keine formalen Auffälligkeiten.",
            ),
            "tone": "warn" if guardrail_triggered else "ok",
        },
        {
            "label": "Self-Evaluation",
            "value": "Bestanden" if self_eval_passed else "Prüfen",
            "caption": join_readable(
                result.get("self_evaluation_issues"),
                fallback="Keine Qualitätsauffälligkeiten.",
            ),
            "tone": "ok" if self_eval_passed else "warn",
        },
    ])

    security_rows = [
        {
            "Prüfung": "Prompt Injection",
            "Status": "Erkannt" if result.get("injection_detected") else "Nicht erkannt",
            "Einordnung": "Sicherheitsrelevant" if result.get("injection_detected") else "Unauffällig",
            "Konkreter Prüfhinweis": injection_details(result),
        },
        {
            "Prüfung": "No-Answer-Fallback",
            "Status": "Ausgelöst" if result.get("no_answer_triggered") else "Nicht ausgelöst",
            "Einordnung": "Antwortgrundlage unzureichend" if result.get("no_answer_triggered") else "Antwortgrundlage vorhanden",
            "Konkreter Prüfhinweis": no_answer_details(result),
        },
        {
            "Prüfung": "Guardrails",
            "Status": "Ausgelöst" if result.get("guardrail_triggered") else "Nicht ausgelöst",
            "Einordnung": join_readable(
                result.get("guardrail_flags"),
                fallback="Keine Guardrail-Auffälligkeiten.",
            ),
            "Konkreter Prüfhinweis": guardrail_details(result),
        },
        {
            "Prüfung": "Self-Evaluation",
            "Status": "Bestanden" if result.get("self_evaluation_passed") else "Prüfen",
            "Einordnung": join_readable(
                result.get("self_evaluation_issues"),
                fallback="Keine Qualitätsauffälligkeiten.",
            ),
            "Konkreter Prüfhinweis": self_evaluation_details(result),
        },
    ]
    render_visual_checklist(security_rows, title_key="Prüfung")

    st.markdown("#### Antwortabdeckung")
    requires_completion = result.get("requires_human_completion")
    covered_aspects = as_list(result.get("covered_aspects"))
    missing_aspects = as_list(result.get("missing_aspects"))
    uncertain_aspects = as_list(result.get("uncertain_aspects"))

    render_review_tiles([
        {
            "label": "Abdeckungswert",
            "value": metric_value(completeness_score, digits=2),
            "caption": "Bewertung, wie weit der Entwurf das Bürgeranliegen inhaltlich abdeckt.",
            "tone": "ok" if isinstance(completeness_score, float) and completeness_score >= 0.8 else "warn",
        },
        {
            "label": "Bewertung",
            "value": completeness_label,
            "caption": "Qualitative Einordnung der Antwortabdeckung.",
            "tone": "neutral",
        },
        {
            "label": "Fachliche Ergänzung",
            "value": "Prüfen" if requires_completion else "Nicht markiert",
            "caption": (
                "Die Antwortabdeckung weist auf mögliche inhaltliche Lücken hin."
                if requires_completion
                else "Keine konkrete Ergänzungspflicht aus der Abdeckungsprüfung."
            ),
            "tone": "warn" if requires_completion else "neutral",
        },
    ])

    if result.get("answer_completeness_reason"):
        st.info(result.get("answer_completeness_reason"))

    aspect_rows = [
        {
            "Prüfung": "Abgedeckte Aspekte",
            "Status": count_label(len(covered_aspects), "Aspekt", "Aspekte"),
            "Einordnung": "Im Entwurf berücksichtigt" if covered_aspects else "Keine Aspekte ausgewiesen",
            "Konkreter Prüfhinweis": "; ".join(str(value) for value in covered_aspects)
            if covered_aspects else "Es wurden keine abgedeckten Aspekte ausgewiesen.",
        },
        {
            "Prüfung": "Fehlende Aspekte",
            "Status": count_label(len(missing_aspects), "Aspekt", "Aspekte"),
            "Einordnung": "Fachlich nachprüfen" if missing_aspects else "Keine fehlenden Aspekte ausgewiesen",
            "Konkreter Prüfhinweis": "; ".join(str(value) for value in missing_aspects)
            if missing_aspects else "Es wurden keine fehlenden Aspekte ausgewiesen.",
        },
        {
            "Prüfung": "Unsichere Aspekte",
            "Status": count_label(len(uncertain_aspects), "Aspekt", "Aspekte"),
            "Einordnung": "Fachlich absichern" if uncertain_aspects else "Keine unsicheren Aspekte ausgewiesen",
            "Konkreter Prüfhinweis": "; ".join(str(value) for value in uncertain_aspects)
            if uncertain_aspects else "Es wurden keine unsicheren Aspekte ausgewiesen.",
        },
    ]
    render_visual_checklist(aspect_rows, title_key="Prüfung")

    with st.expander("Governance-Rohdaten"):
        st.json({
            "risk_score": result.get("risk_score"),
            "risk_reasons": result.get("risk_reasons"),
            "response_mode": result.get("response_mode"),
            "workflow_status": result.get("workflow_status"),
            "human_review_required": result.get("human_review_required"),
            "human_review_reasons": result.get("human_review_reasons"),
            "guardrail_triggered": result.get("guardrail_triggered"),
            "guardrail_flags": result.get("guardrail_flags"),
            "self_evaluation_passed": result.get("self_evaluation_passed"),
            "self_evaluation_issues": result.get("self_evaluation_issues"),
            "answer_completeness_score": result.get("answer_completeness_score"),
            "answer_completeness_label": result.get("answer_completeness_label"),
        }, expanded=False)


def render_aspect_list(title: str, values: list[Any]) -> None:
    if not values:
        return

    st.markdown(f"**{title}:**")

    for value in values:
        st.write(f"- {value}")


def render_answer_completeness_warning(case: dict[str, Any]) -> None:
    result = get_result(case)

    answer_score = result.get("answer_completeness_score")
    answer_label = result.get("answer_completeness_label")
    answer_reason = result.get("answer_completeness_reason")
    missing_aspects = result.get("missing_aspects") or []
    uncertain_aspects = result.get("uncertain_aspects") or []
    requires_human_completion = result.get("requires_human_completion")

    if answer_score is None:
        st.info("Für diesen Fall liegt noch keine Bewertung der Antwortabdeckung vor.")
        return

    try:
        answer_score_float = float(answer_score)
    except (TypeError, ValueError):
        st.warning("Die Antwortabdeckung konnte nicht als numerischer Wert gelesen werden.")
        return

    st.markdown("### Einschätzung der Antwortabdeckung")

    if answer_score_float >= 0.8:
        st.success(
            f"Antwortabdeckung: {answer_score_float:.2f} ({answer_label}). "
            "Der Antwortentwurf deckt das Bürgeranliegen voraussichtlich weitgehend ab."
        )
    elif answer_score_float >= 0.5:
        st.warning(
            f"Antwortabdeckung: {answer_score_float:.2f} ({answer_label}). "
            "Der Antwortentwurf beantwortet das Anliegen vermutlich nur teilweise. "
            "Bitte prüfen, ob alle Punkte ausreichend abgedeckt sind."
        )
    else:
        st.error(
            f"Antwortabdeckung: {answer_score_float:.2f} ({answer_label}). "
            "Der Antwortentwurf ist wahrscheinlich unvollständig und sollte fachlich ergänzt werden."
        )

    if answer_reason:
        st.caption(f"Begründung: {answer_reason}")

    if requires_human_completion:
        if answer_score_float >= 0.8:
            st.info(
                "Hinweis: Das System empfiehlt eine zusätzliche Prüfung, "
                "obwohl die Abdeckung hoch eingeschätzt wurde."
            )
        else:
            st.warning(
                "Das System empfiehlt eine fachliche Ergänzung oder besonders sorgfältige Prüfung."
            )

    render_aspect_list("Möglicherweise fehlende Aspekte", missing_aspects)
    render_aspect_list("Unsichere Aspekte", uncertain_aspects)


def render_sources(case: dict[str, Any]) -> None:
    result = get_result(case)

    retrieved_sources = as_list(result.get("retrieved_sources"))
    used_sources = as_list(result.get("used_sources"))
    retrieved_chunks = as_list(result.get("retrieved_chunks"))
    retrieved_chunk_ids = as_list(result.get("retrieved_chunk_ids"))

    if not retrieved_chunks and retrieved_chunk_ids:
        retrieved_chunks = resolve_retrieved_chunks_from_ids(retrieved_chunk_ids)

    used_source_names = set(str(source) for source in used_sources)
    retrieved_source_names = set(str(source) for source in retrieved_sources)
    unused_sources = sorted(retrieved_source_names - used_source_names)
    source_usage_status = (
        "Quellen wurden im Entwurf genutzt"
        if used_sources
        else "Keine Quelle wurde im Entwurf genutzt"
    )

    render_review_header(
        "Informationsgrundlagen",
        source_usage_status,
        badges=[
            f"{count_label(len(retrieved_sources), 'Quelle')} gefunden",
            f"{count_label(len(used_sources), 'Quelle')} genutzt",
            count_label(len(retrieved_chunks), "Retrieval-Chunk", "Retrieval-Chunks"),
        ],
    )

    render_review_tiles([
        {
            "label": "Retrieval",
            "value": count_label(len(retrieved_sources), "Quelle"),
            "caption": "Informationsgrundlagen, die für das Anliegen gefunden wurden.",
            "tone": "ok" if retrieved_sources else "warn",
        },
        {
            "label": "Quellennutzung",
            "value": count_label(len(used_sources), "Quelle"),
            "caption": "Quellen, auf denen der Antwortentwurf tatsächlich beruht.",
            "tone": "ok" if used_sources else "warn",
        },
        {
            "label": "Chunk-Nachweis",
            "value": count_label(len(retrieved_chunks), "Chunk", "Chunks"),
            "caption": "Textausschnitte, die für die fachliche Prüfung eingesehen werden können.",
            "tone": "ok" if retrieved_chunks else "warn",
        },
        {
            "label": "Nicht genutzte Treffer",
            "value": len(unused_sources),
            "caption": "Gefundene Quellen, die nicht in den Entwurf eingeflossen sind.",
            "tone": "neutral" if unused_sources else "ok",
        },
    ])

    st.markdown("#### Quellenübersicht")
    render_visual_source_overview(
        build_source_overview_rows(
            retrieved_sources=retrieved_sources,
            used_sources=used_sources,
            retrieved_chunks=retrieved_chunks,
        )
    )

    if unused_sources:
        st.info(
            "Einige gefundene Quellen wurden nicht im Entwurf genutzt. "
            "Das ist unkritisch, sollte aber bei fachlichen Grenzfällen mitgeprüft werden."
        )

    st.markdown("#### Retrieval-Chunks")
    st.caption(
        "Die Chunks zeigen die konkreten Textausschnitte, die dem System als Kontext "
        "zur Verfügung standen."
    )

    chunk_rows = []
    for chunk in retrieved_chunks:
        if not isinstance(chunk, dict):
            continue

        chunk_rows.append({
            "Chunk-ID": chunk.get("chunk_id"),
            "Quelle": chunk.get("source"),
            "Kategorie": display_category_name(chunk.get("category")),
            "Abschnitt": chunk.get("section_title"),
            "Auszug": preview_text(chunk.get("content"), limit=260),
        })

    if chunk_rows:
        render_visual_chunk_overview(chunk_rows)
    elif retrieved_chunk_ids:
        st.warning(
            "Für diesen Fall sind nur Retrieval-Chunk-IDs gespeichert. "
            "Die zugehörigen Inhalte konnten nicht aus der Wissensbasis geladen werden."
        )
        render_source_list("Retrieval-Chunk-IDs", retrieved_chunk_ids)
        return
    else:
        st.info("Keine Retrieval-Chunks vorhanden.")
        return

    for source, source_chunks in grouped_chunks_by_source(retrieved_chunks).items():
        with st.expander(f"{source} ({count_label(len(source_chunks), 'Chunk', 'Chunks')})"):
            for index, chunk in enumerate(source_chunks, start=1):
                st.markdown(f"**Chunk {index}: {chunk.get('section_title') or chunk.get('chunk_id') or 'Ausschnitt'}**")

                col1, col2 = st.columns([1, 2])
                col1.caption(f"Kategorie: {display_category_name(chunk.get('category'))}")
                col2.caption(f"Chunk-ID: {chunk.get('chunk_id') or '-'}")
                st.text(chunk.get("content", ""))

                if index < len(source_chunks):
                    st.divider()


def render_original_request(case: dict[str, Any]) -> None:
    metadata = get_email_metadata(case)
    body = case.get("text", "")

    render_review_header(
        "Originalanfrage",
        "Die eingegangene Bürgeranfrage im Format einer geöffneten Mail.",
        badges=[
            f"Betreff: {metadata.get('subject') or 'Ohne Betreff'}",
            f"Absender: {metadata.get('sender') or 'Unbekannt'}",
        ],
    )

    render_mail_header_card(
        "Mailkopf",
        [
            (
                "Von",
                sender_display_name(
                    metadata.get("sender"),
                    metadata.get("sender_address"),
                ),
            ),
            ("Absenderadresse", metadata.get("sender_address") or "Keine Angabe"),
            ("An", ", ".join(as_list(metadata.get("recipients"))) or "Keine Angabe"),
            ("Betreff", metadata.get("subject") or "Ohne Betreff"),
            ("Verarbeitet am", metadata.get("processed_at") or "Keine Angabe"),
        ],
    )
    render_mail_body(body)


def get_internal_forward_subject(case: dict[str, Any]) -> str:
    internal_forward = get_internal_forward(case)

    return (
        internal_forward.get("subject")
        or build_internal_forward_subject(case)
        or "Interne Weiterleitung"
    )


def get_internal_forward_body(case: dict[str, Any]) -> str:
    internal_forward = get_internal_forward(case)

    return (
        internal_forward.get("body")
        or build_internal_forward_body(case)
        or "Für diesen Fall konnte kein Arbeitspaket-Text rekonstruiert werden."
    )


def render_work_package_mail(case: dict[str, Any]) -> None:
    internal_forward = get_internal_forward(case)
    subject = get_internal_forward_subject(case)
    body = get_internal_forward_body(case)

    sent = internal_forward.get("sent")
    status = internal_forward.get("status") or "Keine Angabe"
    recipient = internal_forward.get("to") or case.get("assigned_email") or "Keine Angabe"
    sender = internal_forward.get("from") or "Keine Angabe"
    sent_at = internal_forward.get("sent_at") or "Nicht gesendet"

    render_review_header(
        "Arbeitspaket-Mail an den Fachbereich",
        "Diese Mail zeigt, welche Informationen dem Fachbereich für die Prüfung übermittelt wurden.",
        badges=[
            f"Status: {status}",
            f"Empfänger: {recipient}",
            f"Gesendet: {sent_at}",
        ],
    )

    render_review_tiles([
        {
            "label": "Versandstatus",
            "value": "Gesendet" if sent else "Nicht gesendet",
            "caption": internal_forward.get("error") or "Interne Weiterleitung an den Fachbereich.",
            "tone": "ok" if sent else "warn",
        },
        {
            "label": "Empfänger",
            "value": recipient,
            "caption": "Adresse des zugeordneten Fachbereichs.",
            "tone": "neutral",
        },
        {
            "label": "Absender",
            "value": sender,
            "caption": "Kommunales Postfach, aus dem das Arbeitspaket versendet wurde.",
            "tone": "neutral",
        },
    ])

    st.markdown("#### Mailkopf")
    render_mail_header_card(
        "Interne Weiterleitung",
        [
            ("Von", sender),
            ("An", recipient),
            ("Betreff", subject),
            ("Status", status),
            ("Gesendet am", sent_at),
        ],
    )

    st.markdown("#### Mailinhalt")
    render_mail_body(body, structured=True)


def handle_save_draft(
        case_id: int,
        final_answer: str,
        reviewed_by: str,
        notes: str,
) -> None:
    save_edited_answer(
        case_id=case_id,
        edited_answer=final_answer,
        reviewed_by=reviewed_by,
        notes=notes,
    )

    st.success("Entwurf wurde gespeichert.")
    st.rerun()


def handle_send_answer(
        case_id: int,
        final_answer: str,
        reviewed_by: str,
        notes: str,
) -> None:
    updated_case = approve_and_send_to_citizen(
        case_id=case_id,
        final_answer=final_answer,
        reviewed_by=reviewed_by,
        notes=notes,
    )

    citizen_reply = get_citizen_reply(updated_case)

    if citizen_reply.get("sent"):
        st.success(f"Antwort wurde an {citizen_reply.get('to')} gesendet.")
    else:
        st.error("Antwort konnte nicht gesendet werden.")
        st.code(citizen_reply.get("error") or "Unbekannter Versandfehler.")

    st.rerun()


def render_answer_review(case: dict[str, Any], selected_team: str) -> None:
    case_id = case["case_id"]
    default_answer = get_draft_answer(case)
    result = get_result(case)
    has_answer = bool(default_answer.strip())
    requires_review = bool(result.get("human_review_required"))
    requires_completion = bool(result.get("requires_human_completion"))
    completeness_score = result.get("answer_completeness_score")
    completeness_label = result.get("answer_completeness_label") or "Keine Angabe"

    render_review_header(
        "Antwortfreigabe",
        "Hier wird der KI-generierte Entwurf fachlich geprüft, angepasst und erst danach freigegeben.",
        badges=[
            f"Antwortabdeckung: {metric_value(completeness_score, digits=2)} ({completeness_label})",
            f"Human Review: {bool_text(result.get('human_review_required'))}",
        ],
    )

    render_review_tiles([
        {
            "label": "Antwortentwurf",
            "value": "Vorhanden" if has_answer else "Nicht vorhanden",
            "caption": (
                "Es liegt ein KI-generierter Textvorschlag zur fachlichen Bearbeitung vor."
                if has_answer
                else "Für diesen Fall liegt kein verwendbarer Antworttext vor."
            ),
            "tone": "ok" if has_answer else "warn",
        },
        {
            "label": "Menschliche Prüfung",
            "value": "Vorgesehen" if requires_review else "Reguläre Freigabe",
            "caption": (
                "Der Fall wurde durch die Pipeline für eine fachliche Kontrolle markiert."
                if requires_review
                else "Keine zusätzliche Kontrollstufe über die normale Fachfreigabe hinaus."
            ),
            "tone": "warn" if requires_review else "neutral",
        },
        {
            "label": "Fachliche Ergänzung",
            "value": "Prüfen" if requires_completion else "Nicht markiert",
            "caption": (
                "Die Vollständigkeitsprüfung sieht mögliche inhaltliche Lücken."
                if requires_completion
                else "Die Vollständigkeitsprüfung markiert keine konkrete Ergänzungspflicht."
            ),
            "tone": "warn" if requires_completion else "neutral",
        },
    ])

    render_answer_completeness_warning(case)
    st.divider()

    st.markdown("#### Entwurf bearbeiten")
    st.caption(
        "Der Text in diesem Bereich ist der fachlich zu prüfende Antwortentwurf. "
        "Änderungen werden erst durch Speichern oder Freigabe übernommen."
    )

    with st.form(f"review_form_{case_id}"):
        reviewed_by = st.text_input(
            "Bearbeitet durch",
            value=reviewer_name_for_team(selected_team),
        )

        final_answer = st.text_area(
            "Finale Antwort",
            value=default_answer,
            height=360,
        )

        notes = st.text_area(
            "Prüfnotiz, optional",
            value=get_team_review(case).get("notes", ""),
            height=100,
        )

        col_save, col_send = st.columns(2)

        with col_save:
            save_clicked = st.form_submit_button("Entwurf speichern")

        with col_send:
            send_clicked = st.form_submit_button(
                "Antwort freigeben und senden",
                type="primary",
            )

    if save_clicked:
        handle_save_draft(
            case_id=case_id,
            final_answer=final_answer,
            reviewed_by=reviewed_by,
            notes=notes,
        )

    if send_clicked:
        if not final_answer.strip():
            st.warning("Bitte eine finale Antwort eintragen.")
        else:
            handle_send_answer(
                case_id=case_id,
                final_answer=final_answer,
                reviewed_by=reviewed_by,
                notes=notes,
            )

    st.divider()
    st.markdown("#### Weitere Fallaktionen")

    col_return, col_escalate = st.columns(2)

    with col_return:
        if st.button(
                "An Kontrolldashboard zurückgeben",
                key=f"return_{case_id}",
        ):
            return_case_to_control_dashboard(
                case_id=case_id,
                reviewed_by=reviewer_name_for_team(selected_team),
                notes=(
                    "Fachbereich hält sich nicht für zuständig oder benötigt "
                    "zentrale Prüfung."
                ),
            )

            st.warning("Fall wurde an das Kontrolldashboard zurückgegeben.")
            st.rerun()

    with col_escalate:
        if st.button(
                "Fall eskalieren",
                key=f"escalate_{case_id}",
        ):
            escalate_case(
                case_id=case_id,
                escalated_by=reviewer_name_for_team(selected_team),
                notes="Fall wurde durch den Fachbereich eskaliert.",
            )

            st.warning("Fall wurde eskaliert.")
            st.rerun()


def render_review_case(case: dict[str, Any], selected_team: str) -> None:
    render_case_summary(case)

    tab_original, tab_work_package, tab_answer, tab_sources, tab_governance = st.tabs([
        "Originalanfrage",
        "Arbeitspaket-Mail",
        "Antwortfreigabe",
        "Quellen",
        "Governance",
    ])

    with tab_original:
        render_original_request(case)

    with tab_work_package:
        render_work_package_mail(case)

    with tab_answer:
        render_answer_review(case, selected_team)

    with tab_sources:
        render_sources(case)

    with tab_governance:
        render_governance(case)


def open_cases_table_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for case in cases:
        result = get_result(case)

        rows.append({
            "Fall-ID": case.get("case_id"),
            "Betreff": get_subject(case),
            "Absender": get_sender(case),
            "Bereich": display_result_division(result),
            "Team": display_result_unit_team(result),
            "Antwortmodus": result.get("response_mode") or "Keine Angabe",
            "Confidence": display_table_metric(result.get("calibrated_confidence") or result.get("confidence")),
            "Antwortabdeckung": display_table_metric(result.get("answer_completeness_score")),
            "Fachliche Ergänzung": display_table_bool(result.get("requires_human_completion")),
            "Risiko": display_table_metric(result.get("risk_score")),
            "Verarbeitet am": get_email_metadata(case).get("processed_at") or "Keine Angabe",
        })

    return rows


def sent_cases_table_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for case in cases:
        citizen_reply = get_citizen_reply(case)

        rows.append({
            "Fall-ID": case.get("case_id"),
            "Betreff": get_subject(case),
            "Empfänger": citizen_reply.get("to"),
            "Bereich": display_result_division(get_result(case)),
            "Team": display_result_unit_team(get_result(case)),
            "Gesendet am": citizen_reply.get("sent_at") or "Keine Angabe",
            "Versandstatus": citizen_reply.get("status") or "Keine Angabe",
        })

    return rows


def filter_case_rows(
        rows: list[dict[str, Any]],
        *,
        key_prefix: str,
        title: str,
) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    return render_dataframe_filters(
        df,
        key_prefix=key_prefix,
        title=title,
        excluded_columns={"Fall-ID"},
        visible_item_label="Einträgen"
    )


def render_open_cases_tab(
        open_cases: list[dict[str, Any]],
        selected_team: str,
) -> None:
    st.subheader("Offene Freigaben")

    if not open_cases:
        st.info("Für diesen Fachbereich liegen aktuell keine offenen Freigaben vor.")
        return

    open_cases_df = filter_case_rows(
        open_cases_table_rows(open_cases),
        key_prefix=f"team_review_open_cases_filters_v1_{selected_team}",
        title="Offene Freigaben filtern",
    )

    if open_cases_df.empty:
        st.info("Für die aktuelle Filterauswahl liegen keine offenen Freigaben vor.")
        return

    table_event = st.dataframe(
        open_cases_df,
        width="stretch",
        hide_index=True,
        key=f"team_review_open_cases_table_{selected_team}",
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = table_event.selection.rows

    if not selected_rows:
        st.info("Fall in der Tabelle auswählen, um die Freigabeansicht zu öffnen.")
        return

    selected_index = selected_rows[0]
    if selected_index >= len(open_cases_df):
        st.info("Fall in der Tabelle auswählen, um die Freigabeansicht zu öffnen.")
        return

    selected_case_id = open_cases_df.iloc[selected_index]["Fall-ID"]

    selected_case = next(
        (
            case for case in open_cases
            if case["case_id"] == selected_case_id
        ),
        None,
    )

    if selected_case is None:
        st.info("Der ausgewählte Fall ist in der aktuellen Filterauswahl nicht mehr verfügbar.")
        return

    st.divider()
    render_review_case(selected_case, selected_team)


def render_sent_cases_tab(sent_cases: list[dict[str, Any]], selected_team: str) -> None:
    st.subheader("Gesendete Antworten")

    if not sent_cases:
        st.info("Für diesen Fachbereich wurden noch keine Antworten gesendet.")
        return

    sent_cases_df = filter_case_rows(
        sent_cases_table_rows(sent_cases),
        key_prefix=f"team_review_sent_cases_filters_v1_{selected_team}",
        title="Gesendete Antworten filtern",
    )

    if sent_cases_df.empty:
        st.info("Für die aktuelle Filterauswahl liegen keine gesendeten Antworten vor.")
        return

    st.dataframe(
        sent_cases_df,
        width="stretch",
        hide_index=True,
    )


def render_team_stats_tab(
        open_cases: list[dict[str, Any]],
        sent_cases: list[dict[str, Any]],
        team_cases: list[dict[str, Any]],
        selected_team: str,
) -> None:
    st.subheader("Fachbereichs-Statistik")

    col1, col2, col3 = st.columns(3)
    col1.metric("Offene Freigaben", len(open_cases))
    col2.metric("Gesendete Antworten", len(sent_cases))
    col3.metric("Alle Fälle dieses Fachbereichs", len(team_cases))

    if team_cases:
        st.divider()
        team_cases_df = filter_case_rows(
            [
                {
                    "Fall-ID": case.get("case_id"),
                    "Betreff": get_subject(case),
                    "Bereich": display_result_division(get_result(case)),
                    "Team": display_result_unit_team(get_result(case)),
                    "Workflow-Status": get_result(case).get("workflow_status") or case.get("status"),
                    "Antwortmodus": get_result(case).get("response_mode") or "Keine Angabe",
                    "Erstellt am": case.get("created_at"),
                    "Aktualisiert am": case.get("updated_at"),
                }
                for case in team_cases
            ],
            key_prefix=f"team_review_stats_filters_v1_{selected_team}",
            title="Fachbereichsfälle filtern",
        )

        if team_cases_df.empty:
            st.info("Für die aktuelle Filterauswahl liegen keine Fachbereichsfälle vor.")
            return

        st.dataframe(
            team_cases_df,
            width="stretch",
            hide_index=True,
        )


def render_sidebar(teams: dict[str, dict[str, Any]]) -> str:
    with st.sidebar:
        st.header("Fachbereich")

        selected_team = st.selectbox(
            "Angemeldeten Fachbereich auswählen",
            list(teams.keys()),
            format_func=lambda team_id: teams[team_id].get("name", team_id),
        )

        st.write("**Fachbereich:**", display_team_name(selected_team))
        st.write("**E-Mail:**", teams[selected_team].get("email"))

        if st.button("Aktualisieren"):
            st.rerun()

        st.divider()

        st.markdown("### Schnellzugriff")
        st.link_button(
            "Operative App öffnen",
            "http://localhost:8501",
        )

        st.link_button(
            "Bürger-Mail-Simulator öffnen",
            "http://localhost:8502",
        )

    return selected_team


def main() -> None:
    st.title("✅ Fachbereichs-Freigabe")
    st.caption(
        "Simulation der fachlichen Prüfung und Freigabe von KI-generierten Antwortentwürfen."
    )

    config = load_municipality_config()
    teams = get_review_teams(config)

    if not teams:
        st.error("Keine Fachbereiche in der Konfiguration gefunden.")
        return

    selected_team = render_sidebar(teams)
    cases = load_cases()

    open_cases = get_open_cases_for_team(cases, selected_team)
    sent_cases = get_sent_cases_for_team(cases, selected_team)
    team_cases = get_all_cases_for_team(cases, selected_team)

    tab_open, tab_sent, tab_stats = st.tabs([
        "Offene Freigaben",
        "Gesendete Antworten",
        "Fachbereichs-Statistik",
    ])

    with tab_open:
        render_open_cases_tab(open_cases, selected_team)

    with tab_sent:
        render_sent_cases_tab(sent_cases, selected_team)

    with tab_stats:
        render_team_stats_tab(open_cases, sent_cases, team_cases, selected_team)


if __name__ == "__main__":
    main()
