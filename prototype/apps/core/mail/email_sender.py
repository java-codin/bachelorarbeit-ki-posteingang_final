"""Erzeugt und versendet simulierte E-Mail-Antworten im Operations-Prototyp.

Das Modul kapselt Betreff-, Textkörper- und SMTP/Mailpit-Logik, damit UI- und
Workflow-Code keine Transportdetails kennen müssen.
"""

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from textwrap import dedent, indent
from typing import Any

import yaml
from dotenv import load_dotenv

from apps.core.municipality_lookup import get_department_display_name
from prototype.shared.constants import (
    DEFAULT_CENTRAL_POSTBOX_ADDRESS,
    DEFAULT_CENTRAL_POSTBOX_NAME,
    DEFAULT_MAILPIT_SMTP_HOST,
    DEFAULT_MAILPIT_SMTP_PORT,
    ENCODING_UTF8,
    ENV_CENTRAL_POSTBOX_ADDRESS,
    ENV_CENTRAL_POSTBOX_NAME,
    ENV_MAILPIT_SMTP_HOST,
    ENV_MAILPIT_SMTP_PORT,
    REQUEST_TIMEOUT_SECONDS,
)
from prototype.shared.paths import DEFAULT_MUNICIPALITY_CONFIG_PATH, ENV_PATH


CONFIG_PATH = DEFAULT_MUNICIPALITY_CONFIG_PATH

load_dotenv(ENV_PATH)

MAILPIT_SMTP_HOST = os.getenv(ENV_MAILPIT_SMTP_HOST, DEFAULT_MAILPIT_SMTP_HOST)
MAILPIT_SMTP_PORT = int(os.getenv(ENV_MAILPIT_SMTP_PORT, DEFAULT_MAILPIT_SMTP_PORT))

CENTRAL_POSTBOX_NAME = os.getenv(
    ENV_CENTRAL_POSTBOX_NAME,
    DEFAULT_CENTRAL_POSTBOX_NAME,
)

CENTRAL_POSTBOX_ADDRESS = os.getenv(
    ENV_CENTRAL_POSTBOX_ADDRESS,
    DEFAULT_CENTRAL_POSTBOX_ADDRESS,
)

STATUS_BLOCKED = "blocked"
STATUS_TEAM_REVIEW_PENDING = "team_review_pending"
STATUS_NEEDS_MANUAL_ROUTING = "needs_manual_routing"
STATUS_ESCALATED = "escalated"

RESPONSE_MODE_BLOCKED = "blocked"

LEGACY_DRAFT_REVIEW_NOTICE = (
    "Hinweis: Diese Antwort wurde auf Grundlage eines KI-gestützten "
    "Antwortentwurfs erstellt und vor dem Versand fachlich geprüft."
)

FINAL_REVIEW_NOTICE = (
    "Hinweis: Diese Antwort wurde im Rahmen einer prototypischen "
    "KI-gestützten Bearbeitung nach fachlicher Freigabe versendet."
)

_config_cache: dict[str, Any] | None = None


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_municipality_config() -> dict[str, Any]:
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    try:
        config_text = CONFIG_PATH.read_text(encoding=ENCODING_UTF8)
        _config_cache = yaml.safe_load(config_text) or {}
    except (OSError, yaml.YAMLError):
        _config_cache = {}

    return _config_cache


def get_team_display_name(team_id: str | None) -> str | None:
    """
    Liest den Anzeigennamen eines Teams aus der municipality.yaml.
    Fällt bei Fehlern auf die technische Team-ID zurück.
    """
    if not team_id:
        return None

    config = load_municipality_config()
    return get_department_display_name(config, team_id)


def should_send_status_mail(result: dict[str, Any], case_status: str | None) -> bool:
    """
    Statusmails werden nicht versendet, wenn eine Prompt Injection
    oder ein blockierter Fall erkannt wurde.
    """
    if result.get("injection_detected"):
        return False

    if result.get("response_mode") == RESPONSE_MODE_BLOCKED:
        return False

    if case_status == STATUS_BLOCKED:
        return False

    return True


def build_status_mail_subject(original_subject: str | None) -> str:
    if not original_subject:
        return "Eingangsbestätigung zu Ihrer Anfrage"

    return f"Eingangsbestätigung: {original_subject}"


def build_status_mail_body(case_status: str | None, assigned_team: str | None = None) -> str:
    team_name = get_team_display_name(assigned_team)

    if case_status == STATUS_TEAM_REVIEW_PENDING and team_name:
        status_text = (
            "Ihre Anfrage ist bei der Kommune eingegangen und wurde "
            f"vorläufig dem zuständigen Fachteam „{team_name}“ zur Prüfung zugeordnet."
        )
    elif case_status == STATUS_NEEDS_MANUAL_ROUTING:
        status_text = (
            "Ihre Anfrage ist bei der Kommune eingegangen und wird derzeit "
            "manuell geprüft, damit sie der zuständigen Stelle zugeordnet werden kann."
        )
    elif case_status == STATUS_ESCALATED:
        status_text = (
            "Ihre Anfrage ist bei der Kommune eingegangen und wird einer "
            "erweiterten Prüfung unterzogen."
        )
    else:
        status_text = "Ihre Anfrage ist bei der Kommune eingegangen und wird geprüft."

    return dedent(f"""
        Guten Tag,

        {status_text}

        Bitte beachten Sie:
        Diese Nachricht ist eine automatische Eingangsbestätigung. Sie enthält noch keine fachliche Entscheidung oder verbindliche Auskunft.

        Eine inhaltliche Antwort erhalten Sie nach Prüfung durch das zuständige Fachteam.

        Mit freundlichen Grüßen
        {CENTRAL_POSTBOX_NAME}
    """).strip()


def send_status_mail_to_citizen(
        to_email: str | None,
        original_subject: str | None,
        case_status: str | None,
        assigned_team: str | None = None
) -> dict[str, Any]:
    """
    Sendet eine automatische Eingangs- bzw. Statusbestätigung an den Bürger.
    Die Mail kommt bewusst von der zentralen Posteingangsadresse.
    """
    subject = build_status_mail_subject(original_subject)
    body = build_status_mail_body(case_status, assigned_team)

    return send_smtp_mail(
        from_name=CENTRAL_POSTBOX_NAME,
        from_email=CENTRAL_POSTBOX_ADDRESS,
        to_email=to_email,
        subject=subject,
        body=body,
        reply_to=CENTRAL_POSTBOX_ADDRESS,
    )


def send_smtp_mail(
        from_name: str | None,
        from_email: str | None,
        to_email: str | None,
        subject: str,
        body: str,
        reply_to: str | None = None
) -> dict[str, Any]:
    if not from_email:
        return {
            "sent": False,
            "status": "missing_sender",
            "error": "Keine Absenderadresse vorhanden.",
            "sent_at": None,
        }

    if not to_email:
        return {
            "sent": False,
            "status": "missing_recipient",
            "error": "Keine Empfängeradresse vorhanden.",
            "sent_at": None,
        }

    sender_name = from_name or from_email
    formatted_sender = formataddr((sender_name, from_email))

    message = EmailMessage()
    message["From"] = formatted_sender
    message["To"] = to_email
    message["Subject"] = subject

    if reply_to:
        message["Reply-To"] = reply_to

    message.set_content(body)

    try:
        with smtplib.SMTP(
                MAILPIT_SMTP_HOST,
                MAILPIT_SMTP_PORT,
                timeout=REQUEST_TIMEOUT_SECONDS,
        ) as smtp:
            smtp.send_message(message)

        return {
            "sent": True,
            "status": "sent",
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "sent_at": now_iso(),
            "error": None,
        }

    except (OSError, smtplib.SMTPException) as exc:
        return {
            "sent": False,
            "status": "error",
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "sent_at": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_reply_subject(original_subject: str | None) -> str:
    if not original_subject:
        return "Antwort auf Ihre Anfrage"

    if original_subject.lower().startswith("re:"):
        return original_subject

    return f"Re: {original_subject}"


def format_list(values: list[Any] | None) -> str:
    if not values:
        return "- Keine Angaben"

    return "\n".join(f"- {value}" for value in values)


def format_value(value: Any, fallback: str = "Keine Angabe") -> str:
    if value is None:
        return fallback

    if isinstance(value, float):
        return f"{value:.2f}"

    return str(value)


def format_bool(value: Any) -> str:
    if value is True:
        return "Ja"

    if value is False:
        return "Nein"

    return "Keine Angabe"


def format_team_list(values: list[Any] | None) -> str:
    if not values:
        return "- Keine Angaben"

    return "\n".join(
        f"- {get_team_display_name(str(value)) or value}"
        for value in values
    )


def indent_list(text: str) -> str:
    return indent(text, "  ")


def build_internal_forward_subject(case: dict[str, Any]) -> str:
    subject = case.get("email_metadata", {}).get("subject", "Bürgeranliegen")
    team_id = case.get("assigned_team")
    team = get_team_display_name(team_id) or team_id or "unbekannt"

    return f"[KI-Routing][{team}] {subject}"


def build_internal_forward_body(case: dict[str, Any]) -> str:
    result = case.get("result", {})
    metadata = case.get("email_metadata", {})

    team_id = case.get("assigned_team")
    team_name = get_team_display_name(team_id) or team_id or "unbekannt"
    predicted_team = result.get("predicted_team")
    predicted_team_name = get_team_display_name(predicted_team) or predicted_team or "Keine Angabe"
    answer_text = result.get("draft_answer") or result.get("answer") or "Kein Antwortentwurf vorhanden."
    original_text = case.get("text") or "Keine Originalanfrage vorhanden."
    top3_text = indent_list(format_team_list(result.get("top3")))
    used_sources_text = indent_list(format_list(result.get("used_sources")))
    retrieved_sources_text = indent_list(format_list(result.get("retrieved_sources")))

    template = dedent("""
        Arbeitspaket zur fachlichen Prüfung
        ===================================

        Das KI-Assistenzsystem hat eine neue Bürgeranfrage verarbeitet und
        dem folgenden Fachbereich zur Prüfung vorgelegt.

        1. Zuständiger Fachbereich
        --------------------------
        Fachbereich:     {team_name}
        Funktionsadresse: {assigned_email}

        2. Eingangsdaten
        ----------------
        Betreff:          {subject}
        Absender:         {sender}
        Absenderadresse:  {sender_address}
        Eingangsquelle:   {source}

        3. KI-Routing und Prüfindikatoren
        ---------------------------------
        Vorgeschlagenes Fachteam:     {predicted_team_name}
        Alternative Fachteams:
        {top3_text}

        Klassifikationssicherheit:    {confidence}
        Ergebnisvertrauen:            {calibrated_confidence}
        Workflow-Status:              {workflow_status}
        Human Review erforderlich:    {human_review_required}
        Antwortabdeckung:             {completeness_score} ({completeness_label})

        4. Originalanfrage
        ------------------
        {original_text}

        5. KI-generierter Antwortentwurf
        --------------------------------
        {answer_text}

        6. Informationsgrundlagen
        -------------------------
        Verwendete Quellen:
        {used_sources_text}

        Gefundene Quellen:
        {retrieved_sources_text}

        7. Erforderliche Aktion
        -----------------------
        Bitte prüfen Sie den Antwortentwurf in der Fachteam-Freigabe-App.
        Die Antwort wird erst nach fachlicher Freigabe an die Bürgeradresse
        versendet.
    """).strip()

    return template.format(
        team_name=team_name,
        assigned_email=case.get("assigned_email") or "Keine Angabe",
        subject=metadata.get("subject") or "Ohne Betreff",
        sender=metadata.get("sender") or "Keine Angabe",
        sender_address=metadata.get("sender_address") or "Keine Angabe",
        source=case.get("source") or "Keine Angabe",
        predicted_team_name=predicted_team_name,
        top3_text=top3_text,
        confidence=format_value(result.get("confidence")),
        calibrated_confidence=format_value(result.get("calibrated_confidence")),
        workflow_status=result.get("workflow_status") or "Keine Angabe",
        human_review_required=format_bool(result.get("human_review_required")),
        completeness_score=format_value(result.get("answer_completeness_score")),
        completeness_label=result.get("answer_completeness_label") or "Keine Angabe",
        original_text=original_text,
        answer_text=answer_text,
        used_sources_text=used_sources_text,
        retrieved_sources_text=retrieved_sources_text,
    )


def send_internal_team_forward(case: dict[str, Any]) -> dict[str, Any]:
    """
    Sendet ein internes Arbeitspaket an das zuständige Fachteam
    """
    assigned_email = case.get("assigned_email")
    subject = build_internal_forward_subject(case)
    body = build_internal_forward_body(case)

    result = send_smtp_mail(
        from_name=CENTRAL_POSTBOX_NAME,
        from_email=CENTRAL_POSTBOX_ADDRESS,
        to_email=assigned_email,
        subject=subject,
        body=body,
        reply_to=CENTRAL_POSTBOX_ADDRESS,
    )
    result["body"] = body

    return result


def build_final_citizen_body(final_answer: str) -> str:
    cleaned_answer = remove_legacy_draft_review_notice(final_answer)

    return f"{cleaned_answer}\n\n---\n{FINAL_REVIEW_NOTICE}".strip()


def remove_legacy_draft_review_notice(final_answer: str) -> str:
    cleaned_answer = final_answer.replace(LEGACY_DRAFT_REVIEW_NOTICE, "").rstrip()

    while "\n\n\n" in cleaned_answer:
        cleaned_answer = cleaned_answer.replace("\n\n\n", "\n\n")

    return cleaned_answer


def send_final_reply_to_citizen(case: dict[str, Any], final_answer: str) -> dict[str, Any]:
    """
    Sendet die finale, freigegebene Antwort an den Bürger.
    Absender ist die zugeordnete Fachteam-Adresse.
    """
    metadata = case.get("email_metadata", {})

    to_email = metadata.get("sender_address")
    original_subject = metadata.get("subject")

    from_email = case.get("assigned_email")
    assigned_team = case.get("assigned_team")
    from_name = get_team_display_name(assigned_team) or assigned_team or "Fachteam"

    subject = build_reply_subject(original_subject)
    body = build_final_citizen_body(final_answer)

    return send_smtp_mail(
        from_name=from_name,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body=body,
        reply_to=from_email,
    )
