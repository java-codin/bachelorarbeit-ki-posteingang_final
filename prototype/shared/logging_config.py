"""
Einheitliches Logging für Apps, Worker und Hilfsmodule des Prototyps.

Das Logging schreibt standardmäßig auf die Konsole. Für den wissenschaftlichen
Prototyp bleibt die Ausgabe bewusst einfach und nachvollziehbar.
"""

import logging
import os
import sys

from prototype.shared.constants import (
    DEFAULT_LOG_LEVEL,
    ENCODING_UTF8,
    ENV_PROTOTYPE_LOG_LEVEL,
    LOG_DATE_FORMAT_DEFAULT,
    LOG_FORMAT_DEFAULT,
)

_logging_configured = False

EXTERNAL_LOGGER_LEVELS = {
    "faiss": logging.WARNING,
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "sentence_transformers": logging.WARNING,
    "transformers": logging.WARNING,
    "urllib3": logging.WARNING,
}


def configure_utf8_stdio() -> None:
    """
    Konfiguriert die Standardausgabe und Standardfehlerausgabe des Systems auf UTF-8.

    Diese Funktion überprüft, ob die Streams `sys.stdout` und `sys.stderr` die Methode
    `reconfigure` unterstützen. Falls dies der Fall ist, wird ihre Kodierung auf UTF-8
    gesetzt. Diese Einstellung gewährleistet, dass alle in diesen Streams ausgegebenen
    Zeichen im UTF-8-Format kodiert werden und somit internationale Zeichen korrekt
    darstellbar sind.

    :param stream: Die Datenströme, die konfiguriert werden sollen (Standardausgabe und
        Standardfehlerausgabe).
    :return: Es wird kein Wert zurückgegeben.
    """
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding=ENCODING_UTF8)


def get_log_level() -> int:
    """
    Liest die aktuelle Protokollierungsstufe (Log-Level) aus der Umgebungskonfiguration aus
    und gibt diese als numerischen Wert zurück. Falls die konfigurierte Protokollstufe
    nicht bekannt ist, wird `logging.INFO` als Standardwert verwendet.

    Das Protokollierungslevel wird in der Umgebungsvariablen `ENV_PROTOTYPE_LOG_LEVEL`
    gespeichert. Wenn diese Umgebungsvariable nicht gesetzt ist, wird `DEFAULT_LOG_LEVEL`
    als Fallback verwendet.

    :return: Die numerische Protokollstufe gemäß den Konventionen des `logging`-Moduls.
    :rtype: int
    """
    configured_level = os.getenv(ENV_PROTOTYPE_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper()
    return getattr(logging, configured_level, logging.INFO)


def configure_external_loggers() -> None:
    """
    Konfiguriert die Protokollierungsstufen für externe Logger basierend auf den in
    `EXTERNAL_LOGGER_LEVELS` definierten Einstellungen.

    Diese Methode iteriert durch alle Einträge in `EXTERNAL_LOGGER_LEVELS` und setzt die Protokollierungsstufe
    für den entsprechenden Logger auf den angegebenen Wert.

    Die Konfiguration dient zur Harmonisierung der Protokollierungsstufen für verschiedene externe
    Bibliotheken oder Module, um die Protokollausgabe zu vereinfachen und gezielt analysieren zu
    können.

    :return: Keine Rückgabewerte.
    """
    for logger_name, level in EXTERNAL_LOGGER_LEVELS.items():
        logging.getLogger(logger_name).setLevel(level)


def configure_logging(force: bool = False) -> None:
    """
    Konfiguriert die Protokollierung für die Anwendung. Diese Funktion initialisiert ein Standard-Protokollierungssetup,
    sofern es nicht bereits konfiguriert wurde, oder überschreibt die bestehende
    Konfiguration, wenn `force` auf `True` gesetzt ist.

    Die Konfiguration umfasst das Setzen eines Standardprotokollierungsformats, eines Levels und
    die Anpassung der UTF-8-Stdio-Ausgabe. Außerdem werden externe Logger für eine konsistente
    Protokollierung angepasst.

    :param force: Wenn `True`, werden die bestehenden Protokollierungseinstellungen überschrieben,
        auch wenn diese bereits initialisiert wurden. Andernfalls wird die Konfiguration nur
        vorgenommen, wenn dies noch nicht geschehen ist.
    :return: Keine Rückgabe.
    """
    global _logging_configured

    if _logging_configured and not force:
        return

    configure_utf8_stdio()

    logging.basicConfig(
        level=get_log_level(),
        format=LOG_FORMAT_DEFAULT,
        datefmt=LOG_DATE_FORMAT_DEFAULT,
        force=force,
    )

    configure_external_loggers()

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Erstellt und konfiguriert ein `Logger`-Objekt mit dem angegebenen Namen.

    Diese Funktion initialisiert die Protokollierung, falls sie noch nicht konfiguriert wurde,
    und erstellt eine neue `Logger`-Instanz mit dem übergebenen Namen. Hierdurch können
    Nachrichten mit unterschiedlichen Protokollierungsstufen für die Nachvollziehbarkeit
    und Fehlersuche protokolliert werden.

    :param name: Der Name des anzulegenden oder abzurufenden Loggers.
    :type name: str
    :return: Das konfigurierte Logger-Objekt, das zum Protokollieren von Nachrichten verwendet wird.
    :rtype: logging.Logger
    """
    configure_logging()
    return logging.getLogger(name)
