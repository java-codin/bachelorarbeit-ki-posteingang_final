"""Strukturorientiertes Chunking der Pipeline v4.

Das Modul zerlegt Wissensbasis-Dokumente in Chunks mit Metadaten, die für
Retrieval, Quellenbindung und Monitoring nachvollziehbar bleiben.
"""

from typing import Any, List

from src.v4.core.constants import (
    CHUNK_ID_SEP,
    DEFAULT_CHUNK_MAX_CHARS,
    K_CATEGORY,
    K_CHUNK_ID,
    K_CONTENT,
    K_FILENAME,
    K_FILEPATH,
    K_SOURCE,
    K_TEXT,
    SEP_NL2,
)


def structure_chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_MAX_CHARS) -> List[str]:
    """
    Zerlegt einen Text in kleinere Abschnitte (Chunks), deren maximale Länge durch
    `max_chars` beschränkt ist. Die Trennung erfolgt anhand eines definierten
    Separators `SEP_NL2`, der Abschnitte im Text kennzeichnet. Jeder Abschnitt wird geprüft,
    ob er in den aktuellen Chunk passt; falls nicht, wird ein neuer Chunk begonnen.

    Diese Funktion dient der Vorbereitung von Text für Prozesse, die bestimmte
    Längenbegrenzungen erfordern, z. B. für nachgelagerte Verarbeitungsschritte
    oder Modell-Inputs mit begrenztem Kontextfenster.

    :param text: Der Eingabetext, der aufgeteilt werden soll.
    :param max_chars: Die maximale Zeichenanzahl für jeden Chunk. Standard ist
        `DEFAULT_CHUNK_MAX_CHARS`.
    :return: Eine Liste von Strings, wobei jeder String einen Chunk repräsentiert,
        der die Zeichenbegrenzung nicht überschreitet.
    """
    sections = text.split(SEP_NL2)
    chunks = []
    current_chunk = ""

    for section in sections:
        section = section.strip()

        if not section:
            continue

        if len(current_chunk) + len(section) <= max_chars:
            current_chunk += SEP_NL2 + section
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            current_chunk = section

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def create_chunks(documents: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """
    Erstellt Textausschnitte (Chunks) aus einer Liste von Dokumenten und fügt
    metadatenreiche Informationen zu jedem Chunk hinzu. Diese Funktion wird
    hauptsächlich genutzt, um Dokumente in kleinere, verarbeitbare Einheiten
    aufzuteilen, die weitere Verarbeitung oder Analysen unterstützen können.

    :param documents:
        Eine Liste von Dokumenten, wobei jedes Dokument ein Wörterbuch mit
        spezifischen Schlüsseln wie `K_CONTENT`, `K_CATEGORY`, `K_FILENAME`
        und `K_FILEPATH` ist. Der Inhalt unter `K_CONTENT` wird in kleinere
        Abschnitte unterteilt, um einzelne Chunks zu erzeugen.

    :return:
        Eine Liste von Chunks. Jedes Chunk ist ein Wörterbuch, das die
        Metadaten des ursprünglichen Dokuments ergänzt, wie die Chunk-ID
        (`K_CHUNK_ID`), der zugehörige Inhalt (`K_CONTENT`), der ursprüngliche
        Dateiname als Quelle (`K_SOURCE`), die Kategorie (`K_CATEGORY`) und
        den Dateipfad (`K_FILEPATH`).
    """
    chunks = []

    for document in documents:
        for chunk_index, chunk in enumerate(structure_chunk_text(document[K_CONTENT])):
            chunks.append({
                K_CHUNK_ID: (
                    f"{document[K_CATEGORY]}{CHUNK_ID_SEP}"
                    f"{document[K_FILENAME]}{CHUNK_ID_SEP}"
                    f"{chunk_index + 1}"
                ),
                K_CONTENT: chunk,
                K_TEXT: chunk,
                K_SOURCE: document[K_FILENAME],
                K_CATEGORY: document[K_CATEGORY],
                K_FILEPATH: document[K_FILEPATH],
            })

    return chunks
