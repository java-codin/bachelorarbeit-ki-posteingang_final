"""Audit-Logging der Pipeline v3.

Das Modul schreibt je verarbeitetem Fall eine JSONL-Zeile mit
entscheidungsrelevanten Metadaten für Nachvollziehbarkeit und Evaluation.
"""

import json
from datetime import datetime
from pathlib import Path

from prototype.shared.constants import ENC_UTF8
from src.v3.core import constants as c


def log_decision(filepath: Path, data: dict) -> None:
    """
    Protokolliert eine Entscheidungsaufnahme, indem Daten in eine JSONL-Datei
    geschrieben werden. Das Audit-Datenobjekt wird mit einem Zeitstempel ergänzt
    und im angegebenen Pfad gespeichert. Der Prozess unterstützt die Nachvollziehbarkeit
    und spätere Analyse der Entscheidungsprozesse.

    :param filepath: Pfad zu der JSONL-Datei, in die die Auditdaten geschrieben werden.
    :type filepath: Path
    :param data: Datenobjekt, das die Details der Entscheidung enthält. Wird um
        einen Zeitstempel ergänzt, bevor es gespeichert wird.
    :type data: dict
    """
    audit_entry = data.copy()
    audit_entry[c.K_AUDIT_TIMESTAMP] = datetime.now().isoformat()

    filepath.write_text(
        _append_jsonl(filepath, audit_entry),
        encoding=ENC_UTF8,
    )


def _append_jsonl(filepath: Path, entry: dict) -> str:
    """
    Fügt einen neuen Eintrag in einer JSONL-Datei hinzu.

    Diese Funktion prüft, ob die Datei unter dem angegebenen Pfad existiert. Falls sie
    existiert, wird der aktuelle Inhalt der Datei gelesen. Der neue Eintrag wird im JSON-Format
    serialisiert und an das bisherige Dateiformat als neue Zeile angehängt. Falls die Datei
    nicht existiert, wird nur der neue Eintrag als Inhalt der Datei erstellt.

    :param filepath: Der Pfad zur JSONL-Datei, die modifiziert oder erstellt werden soll.
    :type filepath: Path
    :param entry: Ein Wörterbuch, das serialisiert und in die Datei geschrieben wird.
    :type entry: dict
    :return: Der komplette neue Inhalt der Datei als Zeichenkette, einschließlich des
        hinzugefügten Eintrags.
    :rtype: str
    """
    existing_content = filepath.read_text(encoding=ENC_UTF8) if filepath.exists() else ""
    return existing_content + json.dumps(entry, ensure_ascii=False) + "\n"
