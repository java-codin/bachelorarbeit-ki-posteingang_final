"""Strukturorientiertes Chunking der Pipeline v3.

Das Modul erzeugt Chunks für die Wissensbasis und erhält Abschnittszusammenhänge,
damit Retrieval und Guardrail-Auswertung nachvollziehbar bleiben.
"""

from src.v3.core import constants as c


def structure_chunk_text(text, max_chars=c.DEFAULT_CHUNK_MAX_CHARS):
    """
    Teilt einen gegebenen Text in kleinere Abschnitte (Chunks) auf, basierend auf einer
    vorab definierten maximalen Zeichenanzahl und einer Abschnittstrennungslogik.

    Die Funktion zerlegt den Eingabetext in Abschnitte, die durch die Konstante
    `c.SEP_NL2` definiert sind. Diese Abschnitte werden dann zu Chunks zusammengefügt,
    solange die Gesamtlänge der Chunks die durch `max_chars` vorgegebene maximale
    Zeichenanzahl nicht überschreitet. Falls die Länge eines neuen Abschnitts die
    Grenze überschreiten würde, wird ein neuer Chunk begonnen.

    :param text: Der Eingabetext, der in kleinere Abschnitte zerlegt werden soll.
    :type text: str
    :param max_chars: Die maximale Zeichenanzahl für einen Chunk. Standardwert ist
        `c.DEFAULT_CHUNK_MAX_CHARS`.
    :type max_chars: int
    :return: Eine Liste mit Text-Chunks, bei denen jeder Chunk die maximale
        Zeichenanzahl nicht überschreitet.
    :rtype: list[str]
    """
    sections = text.split(c.SEP_NL2)
    chunks = []
    current_chunk = ""

    for section in sections:
        section = section.strip()

        if not section:
            continue

        if len(current_chunk) + len(section) <= max_chars:
            current_chunk += c.SEP_NL2 + section
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            current_chunk = section

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def create_chunks(documents):
    """
    Teilt die bereitgestellten Dokumente in kleinere Abschnitte (Chunks) auf und erstellt für jeden Chunk
    einen Datensatz mit Metadaten wie ID, Quelle und Kategorie.

    :param documents: Eine Liste von Dokumenten, die verarbeitet werden sollen. Jedes Dokument ist ein
        Wörterbuch, das verschiedene Schlüssel für Metadaten und Inhalte enthält (z. B. `c.K_CONTENT`,
        `c.K_CATEGORY`, `c.K_FILENAME`, `c.K_FILEPATH`).
    :type documents: list[dict[str, Any]]

    :return: Eine Liste von Chunks, wobei jeder Chunk eine Struktur mit Daten und Metadaten enthält. Jeder
        Datensatz enthält `c.K_CHUNK_ID`, `c.K_CONTENT`, `c.K_TEXT`, `c.K_SOURCE`, `c.K_CATEGORY` und
        `c.K_FILEPATH`.
    :rtype: list[dict[str, Any]]
    """
    chunks = []

    for document in documents:
        for chunk_index, chunk in enumerate(structure_chunk_text(document[c.K_CONTENT])):
            chunks.append({
                c.K_CHUNK_ID: (
                    f"{document[c.K_CATEGORY]}{c.CHUNK_ID_SEP}"
                    f"{document[c.K_FILENAME]}{c.CHUNK_ID_SEP}"
                    f"{chunk_index + 1}"
                ),
                c.K_CONTENT: chunk,
                c.K_TEXT: chunk,
                c.K_SOURCE: document[c.K_FILENAME],
                c.K_CATEGORY: document[c.K_CATEGORY],
                c.K_FILEPATH: document[c.K_FILEPATH],
            })

    return chunks
