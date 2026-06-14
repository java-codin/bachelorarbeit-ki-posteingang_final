"""Wissensbasis-Lader der Pipeline v3.

Die Funktion liest Markdown-Dateien ein und stellt strukturierte Dokumente für
Chunking, Retrieval und quellengebundene Antwortgenerierung bereit.
"""

from pathlib import Path

from prototype.shared.constants import ENC_UTF8, EXT_MD, FILENAME_README
from src.v3.core import constants as c


def load_knowledge_base(folder_path: Path) -> list[dict[str, str]]:
    """
    Lädt eine Wissensdatenbank aus Markdown-Dateien in einem gegebenen Verzeichnis.

    Der Ordner wird rekursiv durchsucht, und alle Markdown-Dateien, die nicht
    `README.md` heißen, werden in ein Dokumentliste extrahiert. Jedes Dokument
    wird als `dict` gespeichert, das Metadaten wie den Dateinamen, den Pfad, die
    Kategorie (basierend auf dem übergeordneten Ordner) und den Inhalt der Datei
    enthält.

    :param folder_path: Der Pfad zu dem Ordner, der die Markdown-Dateien enthält.
    :type folder_path: str
    :return: Eine Liste von `dict`, wobei jedes Element Informationen zu einer Datei
        enthält (`K_FILENAME`, `K_FILEPATH`, `K_CATEGORY`, `K_CONTENT`).
    :rtype: list[dict[str, str]]
    """
    documents = []

    for file_path in folder_path.rglob(EXT_MD):
        if file_path.name.lower() == FILENAME_README:
            continue

        documents.append({
            c.K_FILENAME: file_path.name,
            c.K_FILEPATH: str(file_path),
            c.K_CATEGORY: file_path.parent.name,
            c.K_CONTENT: file_path.read_text(encoding=ENC_UTF8),
        })

    return documents
