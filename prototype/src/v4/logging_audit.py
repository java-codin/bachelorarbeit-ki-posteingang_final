"""Audit-Logging der Pipeline v4.

Das Modul schreibt entscheidungsrelevante Fallmetadaten als JSONL, damit
Routing, Risiko und Review-Bedarf nachträglich nachvollziehbar bleiben.
"""

import json
from datetime import datetime
from pathlib import Path

from prototype.shared.constants import ENC_UTF8
from src.v4.core.constants import K_AUDIT_TIMESTAMP


def log_decision(filepath: Path, data: dict) -> None:
    """
    Protokolliert eine Entscheidung durch das Speichern eines Audit-Eintrags in einer Datei.

    Diese Funktion erstellt eine Kopie der übergebenen Daten, ergänzt sie um einen
    Zeitstempel, der den Zeitpunkt der Protokollierung repräsentiert, und schreibt
    den resultierenden Audit-Eintrag als JSON-Objekt in die angegebene Datei. Die Datei
    wird im Anhängemodus geöffnet, sodass mehrere Einträge hintereinander gespeichert
    werden können.

    :param filepath: Der Pfad zu der Datei, in welche der Audit-Eintrag geschrieben wird.
    :type filepath: Path
    :param data: Die Quell-Daten des Audit-Eintrags, dargestellt in Form eines
                 Wörterbuchs. Diese Daten werden um einen Audit-Zeitstempel ergänzt.
    :type data: dict
    :return: Gibt nichts zurück.
    """
    audit_entry = data.copy()
    audit_entry[K_AUDIT_TIMESTAMP] = datetime.now().isoformat()

    with Path(filepath).open("a", encoding=ENC_UTF8) as file:
        file.write(
            json.dumps(audit_entry, ensure_ascii=False) + "\n"
        )
