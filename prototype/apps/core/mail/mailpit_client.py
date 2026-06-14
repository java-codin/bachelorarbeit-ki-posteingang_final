"""HTTP-Client für Mailpit im lokalen Demonstrationssetup.

Die Funktionen normalisieren Mailpit-Nachrichten auf ein stabiles internes
Format und halten die restliche Anwendung von API-Details frei.
"""

import os
from email.utils import parseaddr
from typing import Any

import requests
from dotenv import load_dotenv

from prototype.shared.constants import (
    DEFAULT_MAILPIT_API_URL,
    DEFAULT_MAILPIT_INBOX_ADDRESS,
    ENV_MAILPIT_API_URL,
    ENV_MAILPIT_INBOX_ADDRESS,
    REQUEST_TIMEOUT_SECONDS,
)
from prototype.shared.paths import ENV_PATH


load_dotenv(ENV_PATH)


MAILPIT_API_URL = os.getenv(
    ENV_MAILPIT_API_URL,
    DEFAULT_MAILPIT_API_URL,
)

MAILPIT_INBOX_ADDRESS = os.getenv(
    ENV_MAILPIT_INBOX_ADDRESS,
    DEFAULT_MAILPIT_INBOX_ADDRESS,
)


def mailpit_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    response = requests.request(
        method,
        f"{MAILPIT_API_URL}{endpoint}",
        timeout=REQUEST_TIMEOUT_SECONDS,
        **kwargs,
    )
    response.raise_for_status()
    return response


def delete_all_mailpit_messages() -> dict[str, Any]:
    """
    Löscht alle Nachrichten aus dem Mailpit-Postfach.
    Achtung: Das betrifft alle in Mailpit gespeicherten Nachrichten.
    """
    mailpit_request("DELETE", "/messages", json={})

    return {
        "status": "ok",
        "message": "Alle Mailpit-Nachrichten wurden gelöscht.",
    }


def mark_mailpit_message_read(message_id: str) -> None:
    mailpit_request(
        "PUT",
        "/messages",
        json={
            "IDs": [message_id],
            "Read": True,
        },
    )


def get_mailpit_messages(limit: int = 50, start: int = 0) -> list[dict[str, Any]]:
    response = mailpit_request(
        "GET",
        "/messages",
        params={
            "start": start,
            "limit": limit,
        },
    )

    data = response.json()
    return data.get("messages") or data.get("Messages") or []


def get_all_mailpit_messages(
        *,
        page_size: int = 100,
        max_messages: int = 500,
) -> list[dict[str, Any]]:
    messages = []
    start = 0

    while len(messages) < max_messages:
        page_limit = min(page_size, max_messages - len(messages))
        page = get_mailpit_messages(limit=page_limit, start=start)

        if not page:
            break

        messages.extend(page)

        if len(page) < page_limit:
            break

        start += len(page)

    return messages


def get_mailpit_message_detail(message_id: str) -> dict[str, Any]:
    response = mailpit_request("GET", f"/message/{message_id}")
    return response.json()


def get_address(value: Any) -> str:
    if isinstance(value, dict):
        return (
            value.get("Address")
            or value.get("address")
            or value.get("Email")
            or value.get("email")
            or ""
        )

    return str(value)


def get_recipients_from_message(message: dict[str, Any]) -> list[str]:
    recipients = []

    for field in ["To", "to"]:
        values = message.get(field, [])

        if isinstance(values, list):
            recipients.extend(get_address(item) for item in values)

    return [recipient for recipient in recipients if recipient]


def get_raw_from_from_message(message: dict[str, Any]) -> str:
    sender = message.get("From") or message.get("from") or ""

    if isinstance(sender, dict):
        name = sender.get("Name") or sender.get("name") or ""
        address = (
            sender.get("Address")
            or sender.get("address")
            or sender.get("Email")
            or sender.get("email")
            or ""
        )

        if name and address:
            return f"{name} <{address}>"

        return str(name or address or "")

    return str(sender or "")


def get_sender_from_message(message: dict[str, Any]) -> str:
    name, _ = get_sender_parts_from_message(message)

    return name


def get_sender_parts_from_message(message: dict[str, Any]) -> tuple[str, str]:
    raw_from = get_raw_from_from_message(message)
    name, address = parseaddr(raw_from)

    return name.strip().strip('"'), address.strip()


def get_subject_from_message(message: dict[str, Any]) -> str:
    return (
        message.get("Subject")
        or message.get("subject")
        or "(Kein Betreff)"
    )


def get_created_from_message(message: dict[str, Any]) -> str:
    return (
        message.get("Created")
        or message.get("created")
        or message.get("Date")
        or message.get("date")
        or ""
    )


def get_read_from_message(message: dict[str, Any]) -> bool | None:
    if "Read" in message:
        return message.get("Read")

    return message.get("read")


def get_text_from_message(message: dict[str, Any]) -> str:
    return (
        message.get("Text")
        or message.get("text")
        or message.get("Snippet")
        or message.get("snippet")
        or message.get("Body")
        or message.get("body")
        or ""
    ).strip()


def message_targets_address(message: dict[str, Any], address: str) -> bool:
    if not address:
        return False

    recipients = {
        recipient.lower()
        for recipient in get_recipients_from_message(message)
    }

    return address.lower() in recipients


def normalize_mailpit_message(summary: dict[str, Any]) -> dict[str, Any]:
    message_id = summary.get("ID") or summary.get("id")

    if not message_id:
        raise ValueError("Mailpit-Nachricht enthält keine ID.")

    detail = get_mailpit_message_detail(message_id)
    recipients = get_recipients_from_message(detail)
    body = get_text_from_message(detail)
    sender_name, sender_address = get_sender_parts_from_message(detail)

    return {
        "message_id": message_id,
        "subject": get_subject_from_message(detail),
        "sender": sender_name,
        "from": sender_address,
        "sender_address": sender_address,
        "recipients": recipients,
        "to_inbox": MAILPIT_INBOX_ADDRESS.lower() in {
            recipient.lower()
            for recipient in recipients
        },
        "created": get_created_from_message(detail),
        "read": get_read_from_message(detail),
        "snippet": body[:250],
        "body": body,
    }


def normalize_messages(
        summaries: list[dict[str, Any]],
        *,
        ignore_errors: bool = True,
) -> list[dict[str, Any]]:
    normalized_messages = []

    for summary in summaries:
        try:
            normalized_messages.append(normalize_mailpit_message(summary))
        except (requests.RequestException, ValueError) as exc:
            if not ignore_errors:
                raise exc

    return normalized_messages


def get_inbox_messages(limit: int = 50) -> list[dict[str, Any]]:
    summaries = get_all_mailpit_messages(max_messages=limit)

    return [
        message
        for message in normalize_messages(summaries)
        if message["to_inbox"]
    ]


def get_messages_for_address(
        address: str | None,
        limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Gibt alle Mailpit-Nachrichten zurück, die an eine bestimmte Adresse gerichtet sind.
    Dadurch kann im Bürger-Mail-Simulator eine simulierte Inbox pro Absender angezeigt werden.
    """
    if not address:
        return []

    summaries = get_mailpit_messages(limit=limit)
    normalized_messages = normalize_messages(summaries)
    address_lower = address.lower()

    return [
        message
        for message in normalized_messages
        if address_lower in {
            recipient.lower()
            for recipient in message.get("recipients", [])
        }
    ]
