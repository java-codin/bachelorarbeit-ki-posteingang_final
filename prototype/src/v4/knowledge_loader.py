"""Wissensbasis-Lader der Pipeline v4.

Die Funktion liest Markdown-Dokumente ein und reichert sie mit Metadaten für
Chunking, Retrieval und Quellenbindung an.
"""

from pathlib import Path
from typing import Union, List, Any

from prototype.shared.constants import ENC_UTF8, EXT_MD, FILENAME_README
from src.v4.core.constants import K_FILENAME, K_FILEPATH, K_CATEGORY, K_CONTENT


def load_knowledge_base(folder_path: Union[str, Path]) -> List[dict[str, Any]]:
    """
    Lädt eine Wissensbasis aus Dateien innerhalb eines angegebenen Ordners. Unterstützt werden nur
    Dateien mit der definierten Endung, wobei README-Dateien ausgeschlossen werden. Jede Datei wird
    als Dokument interpretiert und in eine strukturierte Form gebracht, die Metadaten wie Dateiname,
    Dateipfad, Kategorie und Inhalt enthält.

    :param folder_path: Der Pfad zu dem Ordner, der die Wissensbasis-Dateien enthält. Kann als `str`
        oder `Path` übergeben werden.
    :return: Eine Liste von Dokumenten, wobei jedes Dokument als `dict` repräsentiert ist, das die
        Schlüssel `K_FILENAME` (Dateiname), `K_FILEPATH` (absoluter Dateipfad als `str`),
        `K_CATEGORY` (Name des Elternordners der Datei) und `K_CONTENT` (Inhalt der Datei) enthält.
    """
    folder_path = Path(folder_path)

    documents = []

    for file_path in Path(folder_path).rglob(EXT_MD):
        if file_path.name.lower() == FILENAME_README:
            continue

        content = file_path.read_text(encoding=ENC_UTF8)

        category = file_path.parent.name

        documents.append({
            K_FILENAME: file_path.name,
            K_FILEPATH: str(file_path),
            K_CATEGORY: category,
            K_CONTENT: content
        })

    return documents
