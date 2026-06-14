"""Strukturorientiertes Chunking der Pipeline v5.

Das Modul nutzt Überschriften und Absätze, um Wissensbasis-Dokumente in
fachlich zusammenhängende Retrieval-Einheiten zu zerlegen.
"""

import re


from typing import Any, List


from src.v5.core.constants import (
    K_TITLE, K_CONTENT, CHAR_HASH, REGEX_HEADING, SEP_NL2, SEP_SENTENCE,
    K_FILENAME, K_FILEPATH, K_CATEGORY, K_SOURCE, K_SECTION_TITLE,
    K_SECTION_INDEX, K_CHUNK_INDEX, K_CHUNK_ID, K_TEXT, V_UNKNOWN,
    CHUNK_ID_SEP, SEP_NL
)
from src.v5.core.response_messages import DEFAULT_DOC_TITLE, SECTION_TITLE_PATTERN


def split_into_sections(content: str) -> List[dict[str, str]]:
    """
    Teilt den gegebenen Inhalt in Abschnitte, die durch Titel anhand eines
    vordefinierten regulären Ausdrucks erkannt werden, und gibt eine Liste von
    Abschnitten zurück. Jeder Abschnitt wird als Wörterbuch mit den Schlüsseln
    `title` und `content` repräsentiert.

    Jeder Abschnitt beginnt mit einer Überschrift, die mit dem angegebenen
    Regulären Ausdruck übereinstimmt, und schließt den zugehörigen Text ein,
    bis eine neue Überschrift gefunden wird. Falls kein bestimmter Abschnitt
    enthalten ist, wird der `DEFAULT_DOC_TITLE` verwendet.

    :param content: Der gesamte Textinhalt, der in Abschnitte unterteilt werden
        soll. Der Text wird zeilenweise verarbeitet.
    :return: Eine Liste von Abschnitten, wobei jeder Abschnitt durch ein
        Wörterbuch beschrieben wird. Das Wörterbuch enthält die Schlüssel
        `title` (Titel des Abschnitts) und `content` (Inhalt des Abschnitts).
    """

    lines = content.splitlines()

    sections = []
    current_title = DEFAULT_DOC_TITLE
    current_lines = []

    heading_pattern = re.compile(REGEX_HEADING)

    for line in lines:
        stripped = line.strip()

        is_heading = bool(heading_pattern.match(stripped))

        if is_heading:
            if current_lines:
                sections.append({
                    K_TITLE: current_title,
                    K_CONTENT: SEP_NL.join(current_lines).strip()
                })

            current_title = stripped.lstrip(CHAR_HASH).strip()
            current_lines = [line]

        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            K_TITLE: current_title,
            K_CONTENT: SEP_NL.join(current_lines).strip()
        })

    return sections


def split_text_with_overlap(
        text: str,
        max_chars: int = 1800,
        overlap_chars: int = 200
) -> List[str]:
    """
    Teilt einen gegebenen Text in Abschnitte mit einer definierten maximalen Zeichenanzahl
    und optionalem Überlappungsbereich. Dabei wird versucht, intelligente
    Trennungen an Absatz- oder Satzgrenzen vorzunehmen, um Lesbarkeit zu wahren.

    Der Algorithmus analysiert den Text und bestimmt Trennstellen so, dass Absätze
    und Sätze respektiert werden, wenn möglich. Ist dies nicht möglich,
    erfolgt die Trennung nach der maximal erlaubten Länge. Ein Überlappungsbereich
    sorgt dafür, dass Abschnitte eine gewisse Redundanz enthalten, um
    Kontext in aufeinanderfolgenden Textteilen zu bewahren.

    :param text: Der Eingabetext, der in Abschnitte unterteilt werden soll.
    :type text: str
    :param max_chars: Die maximale Anzahl an Zeichen, die ein Abschnitt enthalten darf.
    :type max_chars: int
    :param overlap_chars: Die Anzahl an Zeichen, die als Überlappung zwischen Abschnitten
                          dient. Dies hilft bei der Wahrung von Kontext.
    :type overlap_chars: int
    :return: Eine Liste von Textabschnitten, die den Eingabetext in kleinere Teile aufteilt.
    :rtype: List[str]
    """

    text = text.strip()
    max_chars = max(1, int(max_chars))
    overlap_chars = max(0, min(int(overlap_chars), max_chars // 2))

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        window = text[start:end]

        paragraph_break = window.rfind(SEP_NL2)
        sentence_break = window.rfind(SEP_SENTENCE)

        if paragraph_break > max_chars * 0.5:
            split_at = start + paragraph_break
        elif sentence_break > max_chars * 0.5:
            split_at = start + sentence_break + 1
        else:
            split_at = end

        chunk = text[start:split_at].strip()

        if chunk:
            chunks.append(chunk)

        next_start = max(0, split_at - overlap_chars)
        start = next_start if next_start > start else split_at

        if start >= len(text):
            break

    return chunks


def create_chunks(
        documents: List[dict[str, Any]],
        max_chars: int = 1800,
        overlap_chars: int = 200
) -> List[dict[str, Any]]:
    """
    Teilt Dokumentinhalte in kleinere Abschnitte auf, die eine maximale Zeichenanzahl nicht überschreiten,
    mit optionalem Zeichenüberlappung zwischen benachbarten Abschnitten. Diese Funktion ermöglicht die
    strukturelle Partitionierung eines oder mehrerer Dokumente, um beispielsweise eine effizientere Verarbeitung
    von Inhalten zu unterstützen.

    :param documents:
        Eine Liste von Dokument-Dictionaries, die partitioniert werden sollen. Jedes Dokument sollte die Schlüssel
        `K_FILENAME`, `K_FILEPATH`, `K_CATEGORY`, `K_CONTENT` und optional `K_TITLE` enthalten. Der Schlüssel
        `K_CONTENT` repräsentiert den Hauptinhalt des Dokuments als Text.
    :param max_chars:
        Maximale Anzahl von Zeichen pro Abschnitt. Dieser Wert definiert die Obergrenze für die Länge der resultierenden
        Textabschnitte. Der Standardwert ist `1800`.
    :param overlap_chars:
        Anzahl der Zeichenüberlappung zwischen aufeinanderfolgenden Abschnitten. Dies kann hilfreich sein, um den
        Zusammenhang zwischen Abschnitten zu erhalten. Der Standardwert ist `200`.
    :return:
        Eine Liste von Dictionaries, wobei jedes Dictionary einen Textabschnitt repräsentiert. Die Abschnitte
        enthalten folgende Schlüssel:
        - `K_CHUNK_ID`: Eine eindeutige Kennung für den Abschnitt bestehend aus Kategorie, Originaldateiname,
          Abschnitts- und Chunks-Index.
        - `K_SOURCE`: Der ursprüngliche Dateiname des Dokuments.
        - `K_FILEPATH`: Der ursprüngliche Dateipfad des Dokuments.
        - `K_CATEGORY`: Die Kategorie des Dokuments.
        - `K_SECTION_TITLE`: Der Titel des Abschnitts, falls vorhanden, oder ein generierter Titel basierend auf
           der Abschnittsnummer.
        - `K_SECTION_INDEX`: Der Index des Abschnitts innerhalb des Dokuments.
        - `K_CHUNK_INDEX`: Der Index des Chunks innerhalb des Abschnitts.
        - `K_CONTENT`: Der Text des Chunks.
        - `K_TEXT`: Eine identische Kopie des Textes des Chunks zur Weiterverarbeitung.
    """

    chunks = []

    for document in documents:
        filename = document.get(K_FILENAME, V_UNKNOWN)
        filepath = document.get(K_FILEPATH, "")
        category = document.get(K_CATEGORY, V_UNKNOWN)
        content = document.get(K_CONTENT, "")

        if not content or not content.strip():
            continue

        sections = split_into_sections(content)

        for section_index, section in enumerate(sections, start=1):
            section_title = section.get(K_TITLE, SECTION_TITLE_PATTERN.format(index=section_index))
            section_text = section.get(K_CONTENT, "")

            if not section_text.strip():
                continue

            text_chunks = split_text_with_overlap(
                section_text,
                max_chars=max_chars,
                overlap_chars=overlap_chars
            )

            for chunk_index, chunk_text in enumerate(text_chunks, start=1):
                chunk_id = (
                    f"{category}{CHUNK_ID_SEP}"
                    f"{filename}{CHUNK_ID_SEP}"
                    f"{section_index}{CHUNK_ID_SEP}"
                    f"{chunk_index}"
                )

                chunks.append({
                    K_CHUNK_ID: chunk_id,
                    K_SOURCE: filename,
                    K_FILEPATH: filepath,
                    K_CATEGORY: category,
                    K_SECTION_TITLE: section_title,
                    K_SECTION_INDEX: section_index,
                    K_CHUNK_INDEX: chunk_index,
                    K_CONTENT: chunk_text,
                    K_TEXT: chunk_text
                })

    return chunks
