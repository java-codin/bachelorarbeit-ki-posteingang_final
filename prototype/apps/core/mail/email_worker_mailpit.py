"""Mailpit-Worker für den operationsnahen Demonstrationsbetrieb.

Der Worker liest neue Posteingangsnachrichten, startet die konfigurierte
Pipeline-Version und überführt Ergebnisse in den gemeinsamen Fall-Store.
"""

import os
import sys
import time
from datetime import datetime
from email.utils import parseaddr
from pathlib import Path
from typing import Any


import yaml
from dotenv import load_dotenv


CURRENT_FILE = Path(__file__).resolve()
LOCAL_PROTOTYPE_DIR = next(parent for parent in CURRENT_FILE.parents if parent.name == "prototype")
LOCAL_PROJECT_ROOT = LOCAL_PROTOTYPE_DIR.parent

for path in [LOCAL_PROJECT_ROOT, LOCAL_PROTOTYPE_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prototype.shared.bootstrap import ensure_project_import_paths

ensure_project_import_paths(__file__)

from apps.core.mail.email_addresses import normalize_email_address
from apps.core.mail.email_sender import (
    send_internal_team_forward,
    send_status_mail_to_citizen,
    should_send_status_mail,
)
from apps.core.municipality_lookup import get_departments
from apps.core.mail.mailpit_client import (
    MAILPIT_API_URL,
    MAILPIT_INBOX_ADDRESS,
    get_all_mailpit_messages,
    mark_mailpit_message_read,
    normalize_mailpit_message,
)
from apps.core.store import (
    create_case,
    is_email_processed,
    mark_email_processed,
    update_case,
    update_worker_status,
)
from apps.core.version_runner import run_version
from prototype.shared.constants import (
    DEFAULT_EMAIL_POLL_SECONDS,
    DEFAULT_OPERATIONS_VERSION,
    ENCODING_UTF8,
    ENV_EMAIL_POLL_SECONDS,
    ENV_OPERATIONS_VERSION,
)
from prototype.shared.logging_config import get_logger
from prototype.shared.paths import DEFAULT_MUNICIPALITY_CONFIG_PATH, ENV_PATH


load_dotenv(ENV_PATH)

logger = get_logger(__name__)

CONFIG_PATH = DEFAULT_MUNICIPALITY_CONFIG_PATH

OPERATIONS_VERSION = os.getenv(ENV_OPERATIONS_VERSION, DEFAULT_OPERATIONS_VERSION)
EMAIL_POLL_SECONDS = int(os.getenv(ENV_EMAIL_POLL_SECONDS, DEFAULT_EMAIL_POLL_SECONDS))

CASE_STATUS_BLOCKED = "blocked"
CASE_STATUS_ESCALATED = "escalated"
CASE_STATUS_NEEDS_MANUAL_REVIEW = "needs_manual_review"
CASE_STATUS_NEEDS_MANUAL_ROUTING = "needs_manual_routing"
CASE_STATUS_TEAM_REVIEW_PENDING = "team_review_pending"

RESPONSE_MODE_BLOCKED = "blocked"
RESPONSE_MODE_ESCALATION = "escalation"

UNKNOWN_TEAM_VALUES = {None, "", "unknown"}

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_valid_routing_teams() -> set[str]:
    try:
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding=ENCODING_UTF8)) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Routing-Konfiguration konnte nicht geladen werden: %s", exc)
        return set()

    return set(get_departments(config).keys())


VALID_ROUTING_TEAMS = load_valid_routing_teams()


def extract_email_address(value: str | None) -> str | None:
    if not value:
        return None

    _, address = parseaddr(value)
    return address or value


def looks_like_email(value: str | None) -> bool:
    return bool(value and "@" in value and "." in value.split("@")[-1])


def split_sender_identity(
        sender: str | None,
        sender_address: str | None = None,
) -> tuple[str | None, str | None]:
    if not sender and not sender_address:
        return None, None

    sender_text = (sender or "").strip()
    parsed_name, parsed_address = parseaddr(sender_text)

    clean_address = None
    for candidate in [sender_address, parsed_address, sender_text]:
        candidate_text = (candidate or "").strip()
        if looks_like_email(candidate_text):
            clean_address = candidate_text
            break

    if parsed_name:
        clean_name = parsed_name.strip()
    elif sender_text and not looks_like_email(sender_text):
        clean_name = sender_text.strip().strip('"')
    else:
        clean_name = None

    if clean_name == clean_address:
        clean_name = None

    return clean_name, clean_address


def determine_case_status(result: dict[str, Any]) -> str:
    """
    Entscheidet, ob ein Fall direkt ans Fachteam geht oder im zentralen
    Kontrolldashboard geprüft werden muss.
    """
    if result.get("status") != "ok":
        return CASE_STATUS_NEEDS_MANUAL_REVIEW

    response_mode = result.get("response_mode")
    target_team = result.get("target_team")
    target_email = result.get("target_email")

    if response_mode == RESPONSE_MODE_BLOCKED:
        return CASE_STATUS_BLOCKED

    if response_mode == RESPONSE_MODE_ESCALATION:
        return CASE_STATUS_ESCALATED

    if result.get("escalation_required"):
        return CASE_STATUS_ESCALATED

    if target_team in UNKNOWN_TEAM_VALUES:
        return CASE_STATUS_NEEDS_MANUAL_ROUTING

    if not target_email:
        return CASE_STATUS_NEEDS_MANUAL_ROUTING

    return CASE_STATUS_TEAM_REVIEW_PENDING


def build_team_review(case_status: str) -> dict[str, Any]:
    review_status = (
        "pending"
        if case_status == CASE_STATUS_TEAM_REVIEW_PENDING
        else "not_started"
    )

    return {
        "status": review_status,
        "reviewed_by": None,
        "reviewed_at": None,
        "decision": None,
        "edited_answer": None,
        "notes": "",
    }


def build_status_mail_state(
        sender_address: str | None,
        status: str = "not_attempted",
) -> dict[str, Any]:
    return {
        "sent": False,
        "to": sender_address,
        "from": None,
        "subject": None,
        "sent_at": None,
        "status": status,
        "error": None,
    }


def build_internal_forward_state(
        assigned_email: str | None,
        status: str = "not_attempted",
) -> dict[str, Any]:
    return {
        "sent": False,
        "to": assigned_email,
        "from": None,
        "subject": None,
        "body": None,
        "sent_at": None,
        "status": status,
        "error": None,
    }


def build_citizen_reply_state(sender_address: str | None) -> dict[str, Any]:
    return {
        "sent": False,
        "to": sender_address,
        "from": None,
        "subject": None,
        "final_answer": None,
        "sent_at": None,
        "status": "not_sent",
        "error": None,
    }


def determine_assignment(
        result: dict[str, Any],
        case_status: str,
) -> tuple[str | None, str | None, str | None]:
    if case_status != CASE_STATUS_TEAM_REVIEW_PENDING:
        return None, None, None

    return (
        result.get("target_team"),
        result.get("target_email"),
        "system",
    )


def build_case_payload(
        inquiry_text: str,
        pipeline_version: str,
        case_status: str,
        assigned_team: str | None,
        assigned_email: str | None,
        assigned_by: str | None,
        message_id: str,
        subject: str,
        sender: str,
        from_address: str | None,
        sender_address: str | None,
        recipients: list[str],
        result: dict[str, Any],
) -> dict[str, Any]:
    sender_name, clean_sender_address = split_sender_identity(sender, sender_address or from_address)
    clean_from_address = from_address or clean_sender_address

    return {
        "text": inquiry_text,
        "version": pipeline_version,
        "status": case_status,
        "assigned_team": assigned_team,
        "assigned_email": assigned_email,
        "assigned_by": assigned_by,
        "review_note": "",
        "source": "mailpit",
        "email_metadata": {
            "mailpit_id": message_id,
            "subject": subject,
            "sender": sender_name,
            "from": clean_from_address,
            "sender_address": clean_sender_address,
            "recipients": recipients,
            "processed_at": now_iso(),
        },
        "team_review": build_team_review(case_status),
        "status_mail": build_status_mail_state(sender_address),
        "internal_forward": build_internal_forward_state(assigned_email),
        "citizen_reply": build_citizen_reply_state(sender_address),
        "result": result,
    }


def status_mail_update(status_mail_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status_mail": {
            "sent": status_mail_result.get("sent"),
            "to": normalize_email_address(status_mail_result.get("to")),
            "from": normalize_email_address(status_mail_result.get("from")),
            "subject": status_mail_result.get("subject"),
            "sent_at": status_mail_result.get("sent_at"),
            "status": status_mail_result.get("status"),
            "error": status_mail_result.get("error"),
        }
    }


def internal_forward_update(forward_result: dict[str, Any]) -> dict[str, Any]:
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


def get_message_id(summary: dict[str, Any]) -> str | None:
    return summary.get("ID") or summary.get("id")


def mark_message_processed(processed_key: str, message_id: str) -> None:
    mark_email_processed(processed_key)
    mark_mailpit_message_read(message_id)


def process_message_summary(summary: dict[str, Any]) -> bool:
    message_id = get_message_id(summary)

    if not message_id:
        return False

    processed_key = f"mailpit:{message_id}"

    if is_email_processed(processed_key):
        return False

    try:
        message = normalize_mailpit_message(summary)
    except Exception as exc:
        logger.error("Mailpit-Nachricht %s konnte nicht normalisiert werden: %s", message_id, exc)
        return False

    if not message["to_inbox"]:
        return False

    subject = message["subject"]
    sender = message["sender"]
    sender_address = message.get("sender_address") or message.get("from") or extract_email_address(sender)
    from_address = message.get("from") or sender_address
    recipients = message["recipients"]
    body = message["body"]

    if not body:
        logger.warning("Nachricht %s hat keinen Textinhalt.", message_id)
        mark_message_processed(processed_key, message_id)
        return False

    inquiry_text = body
    pipeline_version = OPERATIONS_VERSION or DEFAULT_OPERATIONS_VERSION

    logger.info("Neue Sandbox-Mail erkannt: %s", subject)
    logger.info("Absender: %s", sender)
    logger.info("Verarbeitung mit %s startet.", pipeline_version)

    update_worker_status(
        state="processing",
        message="Neue E-Mail wird verarbeitet.",
        current_email_id=message_id,
        current_subject=subject,
        last_error=None,
    )

    result = run_version(pipeline_version, inquiry_text)
    case_status = determine_case_status(result)
    assigned_team, assigned_email, assigned_by = determine_assignment(result, case_status)

    case = create_case(
        build_case_payload(
            inquiry_text=inquiry_text,
            pipeline_version=pipeline_version,
            case_status=case_status,
            assigned_team=assigned_team,
            assigned_email=assigned_email,
            assigned_by=assigned_by,
            message_id=message_id,
            subject=subject,
            sender=sender,
            from_address=from_address,
            sender_address=sender_address,
            recipients=recipients,
            result=result,
        )
    )

    status_mail_result = build_status_mail_state(sender_address, status="not_sent")

    if should_send_status_mail(result, case_status):
        logger.info("Sende Statusmail an %s.", sender_address)

        status_mail_result = send_status_mail_to_citizen(
            to_email=sender_address,
            original_subject=subject,
            case_status=case_status,
            assigned_team=assigned_team,
        )

        logger.info("Statusmail-Versandstatus: %s", status_mail_result.get("status"))

    else:
        status_mail_result["status"] = "not_allowed"
        status_mail_result["error"] = (
            "Statusmail wurde nicht versendet, weil der Fall blockiert wurde "
            "oder eine Prompt Injection erkannt wurde."
        )

    update_case(case["case_id"], status_mail_update(status_mail_result))

    if case_status == CASE_STATUS_TEAM_REVIEW_PENDING:
        logger.info("Sende internes Arbeitspaket an %s.", assigned_email)

        forward_result = send_internal_team_forward(case)
        update_case(case["case_id"], internal_forward_update(forward_result))

        logger.info("Interner Versandstatus: %s", forward_result.get("status"))

    mark_message_processed(processed_key, message_id)

    update_worker_status(
        state="processed",
        message="E-Mail wurde verarbeitet.",
        current_email_id=None,
        current_subject=None,
        last_processed_email_id=message_id,
        last_processed_subject=subject,
        last_case_id=case["case_id"],
        last_status=case_status,
        last_error=None,
    )

    logger.info(
        "Fall %s erstellt. Status: %s, Team: %s",
        case["case_id"],
        case_status,
        assigned_team,
    )

    return True


def poll_mailpit_once() -> int:
    try:
        messages = get_all_mailpit_messages(max_messages=500)
    except Exception as exc:
        logger.error("Fehler beim Abrufen der Mailpit-Nachrichten: %s", exc)
        return 0

    if not messages:
        logger.info("Keine Nachrichten in Mailpit.")
        return 0

    processed_count = 0

    for summary in messages:
        if process_message_summary(summary):
            processed_count += 1

    return processed_count


def main() -> None:
    logger.info("Mailpit Worker gestartet.")
    logger.info("Mailpit API: %s", MAILPIT_API_URL)
    logger.info("Eingangsadresse: %s", MAILPIT_INBOX_ADDRESS)
    logger.info("Version: %s", OPERATIONS_VERSION)
    logger.info("Intervall: %s Sekunden", EMAIL_POLL_SECONDS)

    update_worker_status(
        state="idle",
        message="Mailpit Worker wurde gestartet.",
        current_email_id=None,
        current_subject=None,
        last_error=None,
    )

    while True:
        try:
            processed_count = poll_mailpit_once()

            update_worker_status(
                state="idle",
                message=(
                    f"Postfachüberprüfung abgeschlossen. "
                    f"Verarbeitete Nachrichten: {processed_count}."
                ),
                current_email_id=None,
                current_subject=None,
            )

        except Exception as exc:
            logger.error("%s: %s", type(exc).__name__, exc)

            update_worker_status(
                state="error",
                message="Bei der E-Mail-Verarbeitung ist ein Fehler aufgetreten.",
                last_error=f"{type(exc).__name__}: {exc}",
            )

        time.sleep(EMAIL_POLL_SECONDS)


if __name__ == "__main__":
    main()
