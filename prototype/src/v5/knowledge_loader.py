"""Wissensbasis-Lader der Pipeline v5.

Die Funktionen lesen Markdown-Dokumente ein, entfernen technische Steuerzeichen
und reichern Inhalte mit Metadaten für Chunking und Retrieval an.
"""

import re
from pathlib import Path
from typing import Any, List, Union

from prototype.shared.constants import ENC_UTF8, EXT_MD, FILENAME_README
from src.v5.core.constants import K_FILENAME, K_FILEPATH, K_CATEGORY, K_CONTENT


METADATA_CATEGORY_PATTERN = re.compile(
    r"^\*\*(?:Retrieval-Kategorie|Bereich-ID):\*\*\s*([^<\n]+)",
    re.MULTILINE,
)


def extract_document_category(content: str, fallback: str) -> str:
    match = METADATA_CATEGORY_PATTERN.search(content)
    if not match:
        return fallback

    category = match.group(1).strip()
    return category or fallback


def load_knowledge_base(folder_path: Union[str, Path]) -> List[dict[str, Any]]:
    """
    Lädt eine Wissensdatenbank aus einer gegebenen Ordnerstruktur.

    Es werden Dateien mit einer bestimmten Dateierweiterung innerhalb des angegebenen
    Ordners rekursiv durchsucht und eingelesen. README-Dateien werden übersprungen.
    Die Methode extrahiert den Dateinamen, den Dateipfad, die Kategorie (aus dem
    übergeordneten Ordner) und den Inhalt der Dateien. Die extrahierten Informationen
    werden in einer Liste von `dict`-Objekten zurückgegeben.

    :param folder_path: Der Pfad zum Ordner, der die Wissensdatenbank enthält. Kann
        als `str` oder `Path` angegeben werden.
    :return: Eine Liste von `dict`-Objekten, wobei jedes `dict` die folgenden Schlüssel
        enthält:
        - `K_FILENAME`: Der Name der Datei.
        - `K_FILEPATH`: Der vollständige Pfad zur Datei.
        - `K_CATEGORY`: Der Name des übergeordneten Ordners (als Kategorie).
        - `K_CONTENT`: Der Inhalt der Datei als `str`.
    """
    folder_path = Path(folder_path)

    documents = []

    for file_path in Path(folder_path).rglob(EXT_MD):
        if file_path.name.lower() == FILENAME_README:
            continue

        content = file_path.read_text(encoding=ENC_UTF8)

        category = extract_document_category(content, file_path.parent.name)

        documents.append({
            K_FILENAME: file_path.name,
            K_FILEPATH: str(file_path),
            K_CATEGORY: category,
            K_CONTENT: content
        })

    return documents
