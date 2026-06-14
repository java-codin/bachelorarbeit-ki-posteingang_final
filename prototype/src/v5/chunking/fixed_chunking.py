"""Fixed-Size-Chunking der Pipeline v5.

Die Strategie zerlegt Dokumente in gleichmäßige Textfenster und dient als
vergleichbare Baseline für struktur- und satzorientierte Chunking-Experimente.
"""

from typing import Any, List

from src.v5.core.constants import (
    CHUNK_ID_SEP,
    K_CATEGORY,
    K_CHUNK_ID,
    K_CHUNK_INDEX,
    K_CONTENT,
    K_FILENAME,
    K_FILEPATH,
    K_SOURCE,
    K_TEXT,
    V_UNKNOWN,
)


def fixed_chunk_text(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
) -> List[str]:
    """
    Teilt einen gegebenen Text in kleinere Abschnitte (Chunks) mit einer
    festgelegten Größe auf. Optional kann eine Überlappung zwischen den
    einzelnen Chunks definiert werden.

    Dieser Algorithmus sorgt dafür, dass die Chunks keine Leerzeichen
    am Anfang oder Ende haben und die Aufteilung so effizient wie möglich erfolgt.

    :param text: Der Eingabetext, der in kleinere Abschnitte aufgeteilt werden soll.
    :param chunk_size: Die maximale Größe eines einzelnen Chunks, inkl. Zeichenanzahl.
    :param overlap: Die Anzahl überlappender Zeichen zwischen aufeinander folgenden Chunks.
    :return: Eine Liste von Chunks, wobei jeder Eintrag ein `str` ist.
    """
    chunks = []
    start = 0
    chunk_size = max(1, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size // 2))
    step = max(1, chunk_size - overlap)

    while start < len(text):
        chunk = text[start:start + chunk_size].strip()

        if chunk:
            chunks.append(chunk)

        start += step

    return chunks


def create_chunks(
        documents: List[dict[str, Any]],
        chunk_size: int = 500,
        overlap: int = 50,
        strategy_name: str = "fixed"
) -> List[dict[str, Any]]:
    """
    Teilt Inhalte aus einer Liste von Dokumenten in kleinere Textausschnitte (Chunks) auf,
    abhängig von der angegebenen Strategie, Chunk-Größe und Überlappung. Diese Funktion
    führt eine feste Chunks-Handling-Strategie aus und erzeugt eindeutige `chunk_id`s
    unter Einbeziehung des `strategy_name`, der Kategorie, des Dateinamens und des Chunk-Index.

    :param documents: Eine Liste von Dokumenten, wobei jedes Dokument ein `dict` ist,
        das Informationen wie `K_FILENAME`, `K_FILEPATH`, `K_CATEGORY` und `K_CONTENT` enthält.
    :param chunk_size: Die maximale Länge eines Chunks in Zeichen.
    :param overlap: Die Anzahl der Zeichen, die zwischen aufeinander folgenden Chunks überlappen.
    :param strategy_name: Der Name der Strategie, die zur Identifikation der Chunks verwendet wird.
    :return: Eine Liste von `dict`, wobei jedes `dict` die Informationen eines Chunks enthält,
        einschließlich `K_CHUNK_ID`, `K_SOURCE`, `K_FILEPATH`, `K_CATEGORY`, `K_CHUNK_INDEX`,
        `K_CONTENT` und `K_TEXT`.
    """
    chunks = []

    for document in documents:
        filename = document.get(K_FILENAME, V_UNKNOWN)
        filepath = document.get(K_FILEPATH, "")
        category = document.get(K_CATEGORY, V_UNKNOWN)
        content = document.get(K_CONTENT, "")

        if not content.strip():
            continue

        for chunk_index, chunk_text in enumerate(
                fixed_chunk_text(content, chunk_size=chunk_size, overlap=overlap),
                start=1
        ):
            chunk_id = (
                f"{strategy_name}{CHUNK_ID_SEP}"
                f"{category}{CHUNK_ID_SEP}"
                f"{filename}{CHUNK_ID_SEP}"
                f"{chunk_index}"
            )

            chunks.append({
                K_CHUNK_ID: chunk_id,
                K_SOURCE: filename,
                K_FILEPATH: filepath,
                K_CATEGORY: category,
                K_CHUNK_INDEX: chunk_index,
                K_CONTENT: chunk_text,
                K_TEXT: chunk_text,
            })

    return chunks
