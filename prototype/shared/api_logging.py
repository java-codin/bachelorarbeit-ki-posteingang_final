"""
Einheitliche, datensparsame Logging-Helfer für Pipeline-APIs.

Die Helfer loggen nur technische und fachliche Statuswerte. Bürgertexte,
Antwortentwürfe, E-Mail-Adressen und Quelleninhalte werden bewusst nicht
ausgegeben.
"""

from logging import Logger
from typing import Any


UNKNOWN_CASE_ID = "n/a"


def safe_case_id(row_metadata: dict[str, Any] | None, key: str = "case_id") -> Any:
    """
    Extrahiert die `case_id` aus einem gegebenen Metadaten-Wörterbuch oder liefert
    eine Standardkennung zurück, wenn die Metadaten nicht existieren oder leer sind.

    Wenn der Schlüssel `key` im Wörterbuch `row_metadata` nicht vorhanden ist,
    wird ebenfalls eine Standardkennung zurückgegeben. Diese Funktion kann
    beispielsweise verwendet werden, um eindeutige Fallkennungen konsistent
    abzurufen oder Platzhalter bei unvollständigen Daten bereitzustellen.

    :param row_metadata: Ein optionales `dict`, das Metadaten zu einer Datenzeile
        enthält. Falls `None` oder leer, wird eine Standardkennung genutzt.
    :param key: Der Schlüssel im Wörterbuch `row_metadata`, der die Fallkennung
        identifiziert. Standardmäßig wird nach `case_id` gesucht.
    :return: Die Fallkennung (z. B. `case_id`), falls im `row_metadata`-Wörterbuch
        vorhanden. Andernfalls wird eine vordefinierte Standardkennung zurückgegeben.
    """
    if row_metadata is None:
        return UNKNOWN_CASE_ID

    if hasattr(row_metadata, "empty") and row_metadata.empty:
        return UNKNOWN_CASE_ID

    return row_metadata.get(key, UNKNOWN_CASE_ID)


def format_fields(**fields: Any) -> str:
    """
    Generiert eine Zeichenkette, die die Schlüssel-Wert-Paare von Feldern darstellt,
    wobei ausschließlich Felder mit nicht-`None` Werten eingeschlossen werden.
    Felder mit dem Wert `None` werden ignoriert. Das Ergebnis ist eine durch
    „ | “ getrennte Darstellung der Schlüssel-Wert-Paare im Format
    „Schlüssel=Wert“. Falls keine gültigen Felder vorhanden sind, wird ein
    leerer String zurückgegeben.

    :param fields: Schlüssel-Wert-Paare, die aus beliebigen Daten bestehen können.
        Felder mit dem Wert `None` werden ausgeschlossen.
    :return: Eine durch „ | “ getrennte Darstellung der gültigen Schlüssel-Wert-Paare
        oder ein leerer String, falls keine gültigen Felder bestehen.
    """
    safe_fields = {
        key: value
        for key, value in fields.items()
        if value is not None
    }

    if not safe_fields:
        return ""

    return " | " + " | ".join(
        f"{key}={value}"
        for key, value in safe_fields.items()
    )


def log_pipeline_start(
        logger: Logger,
        *,
        version: str,
        case_id: Any = UNKNOWN_CASE_ID,
) -> None:
    """
    Protokolliert den Start der Pipeline, indem relevante Informationen wie die
    Pipeline-Version und die Fall-ID in das Log geschrieben werden.

    :param logger: Ein Logger-Objekt, das zur Ausgabe der Log-Nachricht verwendet wird.
    :param version: Die Version der gestarteten Pipeline als `str`.
    :param case_id: Die Fall-ID zur Identifikation oder Kontextualisierung der Pipeline-Ausführung.
                    Wenn keine ID angegeben ist, wird ein Standardwert verwendet.
    :return: Gibt keinen Rückgabewert zurück.
    """
    logger.info(
        "Pipeline gestartet%s",
        format_fields(version=version, case_id=case_id),
    )


def log_step_result(
        logger: Logger,
        *,
        version: str,
        case_id: Any = UNKNOWN_CASE_ID,
        step: str,
        duration: float,
        **fields: Any,
) -> None:
    """
    Protokolliert die Ergebnisse eines abgeschlossenen Pipeline-Schritts im gegebenen Logger.

    Diese Funktion erstellt eine strukturierte Log-Meldung, die Informationen über den
    abgeschlossenen Schritt sowie zusätzliche Felder enthält. Dies kann zu Analysezwecken
    oder für die Nachverfolgbarkeit bei der Verarbeitung von Datenpipelines verwendet werden.

    :param logger: Verwalteter Logger, der die Log-Ausgabe handhabt.
    :param version: Versionsbezeichnung des aktuellen Ausführungsstatus der Pipeline.
    :param case_id: ID des Falls, der mit diesem Schritt verknüpft ist. Optional, Standardwert ist `UNKNOWN_CASE_ID`.
    :param step: Name oder Beschreibung des Pipeline-Schritts.
    :param duration: Dauer des Pipeline-Schritts in Sekunden.
    :param fields: Zusätzliche Felder als Schlüssel-Wert-Paare, die in die Log-Ausgabe aufgenommen werden sollen.
    :return: Gibt keinen Rückgabewert zurück, erzeugt aber eine Log-Meldung im gegebenen Logger.
    """
    logger.info(
        "Pipeline-Schritt abgeschlossen%s",
        format_fields(
            version=version,
            case_id=case_id,
            step=step,
            duration_seconds=duration,
            **fields,
        ),
    )


def log_pipeline_event(
        logger: Logger,
        *,
        version: str,
        case_id: Any = UNKNOWN_CASE_ID,
        event: str,
        step: str | None = None,
        **fields: Any,
) -> None:
    """
    Protokolliert ein strukturiertes Pipeline-Ereignis außerhalb eines regulären
    Schrittabschlusses.

    Der Helfer ist für besondere Zustände gedacht, zum Beispiel frühe
    Sicherheitsabbrüche oder erneute Retrieval-Versuche. Die Felder folgen
    demselben datensparsamen Format wie die übrigen Pipeline-Logs.

    :param logger: Verwalteter Logger für die Ausgabe.
    :param version: Version der Pipeline, in der das Ereignis auftritt.
    :param case_id: Fallkennung für die Nachvollziehbarkeit.
    :param event: Technischer Name des Ereignisses.
    :param step: Optionaler Pipeline-Schritt, dem das Ereignis zugeordnet ist.
    :param fields: Zusätzliche strukturierte Metadaten zum Ereignis.
    :return: Gibt keinen Rückgabewert zurück.
    """
    logger.info(
        "Pipeline-Ereignis%s",
        format_fields(
            version=version,
            case_id=case_id,
            event=event,
            step=step,
            **fields,
        ),
    )


def log_pipeline_complete(
        logger: Logger,
        *,
        version: str,
        case_id: Any = UNKNOWN_CASE_ID,
        duration: float,
        **fields: Any,
) -> None:
    """
    Protokolliert den Abschluss einer Pipeline-Ausführung inklusive relevanter Metadaten.

    Diese Funktion erstellt einen Log-Eintrag, der den Abschluss einer Pipeline-Ausführung
    signalisiert. Es werden Informationen wie die verwendete Version, die Fall-ID,
    die Ausführungsdauer sowie beliebige zusätzliche Felder in den Log aufgenommen.
    Alle übergebenen Felder werden in einem menschenlesbaren Format formatiert.

    :param logger: Der Logger, der für das Erstellen des Log-Eintrags verwendet wird.
    :param version: Version des Systems oder der Pipeline, für die der Abschluss
                    protokolliert wird.
    :param case_id: Eine identifizierbare Fall-ID, die mit der Pipeline-Ausführung
                    in Zusammenhang steht. Dieser Wert wird standardmäßig als
                    UNKNOWN_CASE_ID gesetzt, falls keine spezifische ID bereitgestellt
                    wird.
    :param duration: Die Dauer der Pipeline-Ausführung in Sekunden.
    :param fields: Zusätzliche benannte Felder mit Metadaten, die dem Log hinzugefügt werden.
    :return: Gibt keinen Wert zurück.
    """
    logger.info(
        "Pipeline abgeschlossen%s",
        format_fields(
            version=version,
            case_id=case_id,
            duration_seconds=duration,
            **fields,
        ),
    )
