"""Strukturorientiertes Chunking der Pipeline v2.

Das Modul zerlegt Wissensbasis-Texte in begrenzte Abschnitte und erhält dabei
möglichst viel inhaltlichen Kontext für Retrieval-Experimente.
"""

from src.v2.core import constants as c


def structure_chunk_text(text: str, max_chars: int = c.DEFAULT_CHUNK_MAX_CHARS) -> list[str]:
    """
    Teilt einen gegebenen Text in mehrere Abschnitte (Chunks) auf, wobei die maximale Zeichenanzahl
    pro Chunk durch den Parameter `max_chars` begrenzt ist. Abschnitte im Text werden anhand des
    vordefinierten Abschnittstrenners `c.SEP_NL2` aufgeteilt. Leere Abschnitte werden übersprungen.
    Falls ein Abschnitt nicht in den aktuellen Chunk passt, wird ein neuer Chunk gestartet.

    :param text: Der Eingabetext, der in Abschnitte aufgeteilt werden soll.
    :param max_chars: Die maximale Anzahl an Zeichen pro Chunk. Standardwert ist
        durch `c.DEFAULT_CHUNK_MAX_CHARS` definiert.
    :return: Eine Liste von Strings, wobei jeder Eintrag einen Textchunk darstellt.
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


def create_chunks(documents: list[dict]) -> list[dict]:
    """
    Erzeugt Textabschnitte („Chunks“) aus einer Liste von Dokumenten. Jedes Dokument wird in kleinere
    Textsegmente aufgeteilt, wobei jedes Segment mit Metadaten wie einem eindeutigen Chunk-Identifier,
    dem Dateinamen, der Kategorie und dem ursprünglichen Dateipfad angereichert wird.

    Die Funktion ermöglicht eine detaillierte Verarbeitung und Zuordnung von Dokumentinhalten,
    indem eine segmentierte Struktur erzeugt wird, die für nachfolgende Schritte wie Klassifikation,
    Routing oder Antwortentwürfe verwendet werden kann.

    :param documents:
        Eine Liste von Dictionaries, die die zu verarbeitenden Dokumente repräsentieren.
        Jedes Dictionary enthält notwendige Metadaten wie `c.K_CONTENT`, `c.K_CATEGORY`,
        `c.K_FILENAME` und `c.K_FILEPATH`.
    :return:
        Eine Liste von Dictionaries, die die erzeugten Textabschnitte („Chunks“) enthalten.
        Jeder Eintrag in der Liste repräsentiert einen Textabschnitt mit Metadaten,
        einschließlich eindeutiger Chunk-ID, Inhalt, Kategorie, Dateiquelle und Dateipfad.
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
