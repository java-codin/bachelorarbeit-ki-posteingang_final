"""Wissensbasis-Lader der Pipeline v2.

Die Funktion liest Markdown-Dateien aus der konfigurierten Wissensbasis und
bereitet sie als Dokumente für Chunking und Retrieval auf.
"""

from pathlib import Path

from prototype.shared.constants import ENC_UTF8, EXT_MD, FILENAME_README
from src.v2.core import constants as c


def load_knowledge_base(folder_path):
    """
    Lädt eine Wissensbasis aus Markdown-Dateien in einem angegebenen Ordner.

    Diese Funktion durchsucht alle Unterordner des angegebenen Ordners
    rekursiv nach Dateien, die mit der durch die Konstante `EXT_MD`
    definierten Dateiendung übereinstimmen. README-Dateien (definiert
    durch `FILENAME_README`) werden übersprungen. Für jede gefundene
    Datei wird ein Wörterbuch erstellt, das folgende Informationen enthält:
    - `K_FILENAME`: Der Name der Datei.
    - `K_FILEPATH`: Der vollständige Pfad der Datei als `str`.
    - `K_CATEGORY`: Der Name des übergeordneten Ordners, in dem
      sich die Datei befindet.
    - `K_CONTENT`: Der Inhalt der Datei als `str`, gelesen unter
      Verwendung der UTF-8-Codierung (`ENC_UTF8`).

    Die Informationen aller gefundenen Dateien werden in einer Liste
    gesammelt und zurückgegeben.

    :param folder_path: Der Pfad zu dem Ordner, in dem die Wissensbasis-
        Dateien gesucht werden sollen.
    :type folder_path: str

    :return: Eine Liste von Wörterbüchern, wobei jedes Wörterbuch
        Informationen über eine Datei der Wissensbasis enthält.
    :rtype: list[dict]
    """
    documents = []

    for file_path in Path(folder_path).rglob(EXT_MD):
        if file_path.name.lower() == FILENAME_README:
            continue

        documents.append({
            c.K_FILENAME: file_path.name,
            c.K_FILEPATH: str(file_path),
            c.K_CATEGORY: file_path.parent.name,
            c.K_CONTENT: file_path.read_text(encoding=ENC_UTF8),
        })

    return documents
