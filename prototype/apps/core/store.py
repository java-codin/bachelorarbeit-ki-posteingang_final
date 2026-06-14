"""Dateibasierter Operations-Store für die lokalen Demonstrations-Apps.

Die Funktionen verwalten Fälle, verarbeitete E-Mails und Worker-Status in JSON
und nutzen einfache Dateisperren für konkurrierende Schreibzugriffe.
"""

import json
import shutil
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from prototype.shared.constants import (
    ENCODING_UTF8,
    JSON_INDENT,
    LOCK_POLL_SECONDS,
    LOCK_TIMEOUT_SECONDS,
)
from prototype.shared.paths import (
    CASES_PATH,
    DASHBOARD_METRICS_PATH,
    LAST_RUN_PATH,
    METRICS_PATH,
    MONITORING_PATH,
    OPERATIONS_CACHE_DIR,
    OPERATIONS_OUTPUT_DIR,
    OPERATIONS_PYCACHE_DIR,
    PROCESSED_EMAILS_PATH,
    RUNTIME_STATE_PATH,
    WORKER_STATUS_PATH,
)


STORE_DIR = OPERATIONS_OUTPUT_DIR
ENCODING = ENCODING_UTF8


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_worker_status(message: str = "Worker wurde noch nicht gestartet.") -> dict[str, Any]:
    return {
        "state": "idle",
        "message": message,
        "current_email_id": None,
        "current_subject": None,
        "last_processed_email_id": None,
        "last_processed_subject": None,
        "last_case_id": None,
        "last_status": None,
        "last_error": None,
        "updated_at": now_iso(),
    }


def ensure_store_dir() -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding=ENCODING))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    ensure_store_dir()

    path.write_text(
        json.dumps(data, indent=JSON_INDENT, ensure_ascii=False),
        encoding=ENCODING,
    )


@contextmanager
def file_lock(path: Path):
    """
    Sperrt eine JSON-Datei während eines schreibenden Zugriffs.

    Der Kontext wird nur betreten, wenn die Sperrdatei erfolgreich erzeugt
    wurde. Bei Timeout wird ein Fehler ausgelöst, damit kein Schreibzugriff ohne
    erworbene Sperre stattfindet.
    """
    ensure_store_dir()
    lock_path = path.with_suffix(".lock")
    started_at = time.monotonic()
    acquired = False

    while not acquired:
        try:
            lock_path.touch(exist_ok=False)
            acquired = True
        except FileExistsError as exc:
            # Ein Timeout beendet den kritischen Bereich bewusst mit Fehler,
            # statt ohne Sperre weiterzuschreiben.
            if time.monotonic() - started_at >= LOCK_TIMEOUT_SECONDS:
                raise TimeoutError(
                    f"Dateisperre konnte nicht innerhalb von "
                    f"{LOCK_TIMEOUT_SECONDS} Sekunden erworben werden: {lock_path}"
                ) from exc

            time.sleep(LOCK_POLL_SECONDS)

    try:
        yield
    finally:
        if acquired:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


def ensure_cases_store() -> None:
    ensure_store_dir()

    if not CASES_PATH.exists():
        write_json(CASES_PATH, [])


def ensure_processed_emails_store() -> None:
    ensure_store_dir()

    if not PROCESSED_EMAILS_PATH.exists():
        write_json(PROCESSED_EMAILS_PATH, [])


def ensure_worker_status_store() -> None:
    ensure_store_dir()

    if not WORKER_STATUS_PATH.exists():
        write_json(WORKER_STATUS_PATH, default_worker_status())


def load_cases() -> list[dict[str, Any]]:
    ensure_cases_store()
    return read_json(CASES_PATH, [])


def save_cases(cases: list[dict[str, Any]]) -> None:
    with file_lock(CASES_PATH):
        write_json(CASES_PATH, cases)


def load_processed_emails() -> list[str]:
    ensure_processed_emails_store()
    return read_json(PROCESSED_EMAILS_PATH, [])


def save_processed_emails(processed_emails: list[str]) -> None:
    with file_lock(PROCESSED_EMAILS_PATH):
        write_json(PROCESSED_EMAILS_PATH, processed_emails)


def load_worker_status() -> dict[str, Any]:
    ensure_worker_status_store()
    return read_json(WORKER_STATUS_PATH, default_worker_status())


def save_worker_status(status: dict[str, Any]) -> None:
    write_json(WORKER_STATUS_PATH, status)


def update_worker_status(**updates) -> dict[str, Any]:
    status = load_worker_status()
    status.update(updates)
    status["updated_at"] = now_iso()

    save_worker_status(status)
    return status


def is_email_processed(email_id: str) -> bool:
    return email_id in load_processed_emails()


def mark_email_processed(email_id: str) -> None:
    processed_emails = load_processed_emails()

    if email_id not in processed_emails:
        processed_emails.append(email_id)

    save_processed_emails(processed_emails)


def next_case_id(cases: list[dict[str, Any]]) -> int:
    if not cases:
        return 1

    return max(case.get("case_id", 0) for case in cases) + 1


def create_case(case_data: dict[str, Any]) -> dict[str, Any]:
    with file_lock(CASES_PATH):
        cases = load_cases()

        case = dict(case_data)
        case["case_id"] = next_case_id(cases)
        case["created_at"] = now_iso()
        case["updated_at"] = now_iso()

        cases.append(case)
        write_json(CASES_PATH, cases)

    return case


def update_case(case_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
    with file_lock(CASES_PATH):
        cases = load_cases()
        updated_case = None

        for case in cases:
            if case.get("case_id") == case_id:
                case.update(updates)
                case["updated_at"] = now_iso()
                updated_case = case
                break

        write_json(CASES_PATH, cases)

    return updated_case


def reset_cases() -> None:
    save_cases([])


def reset_processed_emails() -> None:
    save_processed_emails([])


def reset_worker_status() -> None:
    save_worker_status(
        default_worker_status(
            message="Applikationszustand wurde vollständig zurückgesetzt.",
        )
    )


def delete_file_if_exists(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()


def delete_dir_if_exists(path: Path) -> None:
    if path.exists() and path.is_dir():
        shutil.rmtree(path)


def reset_operations_runtime_files() -> None:
    """
    Löscht lokale Laufzeitdateien der operativen E-Mail-App.
    Die zentralen Store-Dateien werden nicht gelöscht, sondern sauber zurückgesetzt.
    """
    files_to_delete = [
        METRICS_PATH,
        MONITORING_PATH,
        DASHBOARD_METRICS_PATH,
        LAST_RUN_PATH,
        RUNTIME_STATE_PATH,
    ]

    dirs_to_delete = [
        OPERATIONS_CACHE_DIR,
        OPERATIONS_PYCACHE_DIR,
    ]

    for path in files_to_delete:
        delete_file_if_exists(path)

    for path in dirs_to_delete:
        delete_dir_if_exists(path)


def factory_reset_operations_store() -> dict[str, str]:
    ensure_cases_store()
    ensure_processed_emails_store()
    ensure_worker_status_store()

    reset_cases()
    reset_processed_emails()
    reset_worker_status()
    reset_operations_runtime_files()

    return {
        "status": "ok",
        "message": "Operations-Store wurde auf Werkseinstellungen zurückgesetzt.",
    }
