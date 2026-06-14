"""Datensparsames Audit-Logging der Pipeline v5.

Das Modul reduziert Pipeline-Ergebnisse auf auditierbare Metadaten und schreibt
sie als JSONL, ohne vollständige Bürgertexte oder Antwortentwürfe zu persistieren.
"""

import json
from datetime import datetime
from typing import Any, Union

from prototype.shared.constants import ENC_UTF8
from src.v5.core.constants import K_AUDIT_TIMESTAMP

AUDIT_EXCLUDE_KEYS = {
    # Bürgertext und Antwortvolltexte
    "text",
    "draft_answer",
    "answer",

    # Retrieval-/Wissensbasis-Volltexte
    "retrieved_chunks",
    "used_chunks",
    "content",

    # Potenziell personenbezogene oder unnötig konkrete Kommunikationsdaten
    "target_email",
    "email",
    "from",
    "to",
    "sender",
    "sender_address",
    "recipient",
    "recipients",

    # Freitext-Begründungen mit möglichem Bezug auf Eingabetext
    "reason",
    "reasoning",
    "injection_reasoning",
    "risk_reasons",
    "human_review_reasons",
    "self_evaluation_issues",
    "reflections",
}


def redact_audit_data(value: Union[dict, list, Any]) -> Union[dict, list, Any]:
    """
    Erstellt eine datensparsame Audit-Ansicht der Pipeline-Ergebnisse.

    Die Funktion durchläuft verschachtelte Dictionaries und Listen rekursiv und
    entfernt Felder aus ``AUDIT_EXCLUDE_KEYS``. Strukturierte Metriken,
    Statuswerte, IDs und Modellmetadaten bleiben erhalten.

    :param value: Daten, die bearbeitet werden sollen. Kann ein `dict`, eine
        `list` oder ein anderes beliebiges Objekt sein.
    :return: Bearbeitete Daten mit entfernten sensiblen Informationen.
        Der Rückgabewert hat denselben Typ wie der Eingabeparameter `value`.
    """
    if isinstance(value, dict):
        # Die Filterung erfolgt schlüsselbasiert, damit neue strukturierte
        # Metriken automatisch erhalten bleiben und Volltexte explizit gesperrt sind.
        return {
            key: redact_audit_data(item)
            for key, item in value.items()
            if key not in AUDIT_EXCLUDE_KEYS
        }

    if isinstance(value, list):
        return [redact_audit_data(item) for item in value]

    return value


def log_decision(filepath: str, data: Union[dict, list, Any]) -> None:
    """
    Protokolliert Entscheidungsdaten in einer angegebenen Datei, wobei sensible Informationen
    aus den protokollierten Daten entfernt werden.

    Die Funktion entfernt sensible Daten aus den übergebenen Entscheidungsdaten mit der Funktion
    `redact_audit_data`. Anschließend wird ein Zeitstempel mit dem aktuellen Zeitpunkt im ISO-Format
    zu den auditfähigen Daten hinzugefügt und diese in der angegebenen Datei gespeichert.

    :param filepath: Dateipfad der Datei, in die die protokollierten Daten als JSON-Zeile
        geschrieben werden sollen.
    :type filepath: str
    :param data: Entscheidungsdaten, die protokolliert werden sollen. Dies kann ein Dictionary,
        eine Liste oder ein beliebiges anderes Datenelement sein.
    :type data: Union[dict, list, Any]
    :return: Es wird kein Wert zurückgegeben.
    :rtype: None
    """
    audit_entry = redact_audit_data(data)
    if not isinstance(audit_entry, dict):
        audit_entry = {"value": audit_entry}
    
    audit_entry[K_AUDIT_TIMESTAMP] = datetime.now().isoformat()

    with open(filepath, "a", encoding=ENC_UTF8) as f:
        f.write(json.dumps(audit_entry, ensure_ascii=False)+ "\n")
