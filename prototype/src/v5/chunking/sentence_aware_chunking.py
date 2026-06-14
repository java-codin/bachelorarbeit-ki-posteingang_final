"""Satzorientiertes Chunking der Pipeline v5.

Die Strategie versucht, Chunk-Grenzen an Satzenden zu setzen, damit Retrieval-
Kontexte lesbarer bleiben als bei rein festen Zeichenfenstern.
"""

import re
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


def sentence_aware_chunk_text(
        text: str,
        max_chars: int = 700
) -> List[str]:
    """
    Teilt einen Text satzgrenzenorientiert unter Beachtung einer maximalen Zeichenlänge.

    Die Funktion verarbeitet den Eingabetext, indem sie ihn an Satzgrenzen unterteilt
    und sicherstellt, dass die resultierenden Abschnitte eine maximale Anzahl von
    Zeichen, definiert durch den Parameter ``max_chars``, nicht überschreiten.
    Falls ein Satz alleine länger als die angegebene maximale Zeichenlänge ist, wird
    er dennoch als eigenständiger Abschnitt hinzugefügt. Die Verarbeitung ignoriert
    leere Sätze und trimmt führende sowie abschließende Leerzeichen in jedem Abschnitt.

    :param text: Der Eingabetext, der in satzgrenzenorientierte Abschnitte unterteilt werden soll.
    :type text: str
    :param max_chars: Die maximale Zeichenanzahl, die ein Abschnitt haben darf. Standardwert ist ``700``.
    :type max_chars: int
    :return: Eine Liste von Zeichenketten, bei denen jede Zeichenkette einen
             satzgrenzenorientierten Abschnitt des ursprünglichen Textes repräsentiert.
    :rtype: List[str]
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk = f"{current_chunk} {sentence}".strip()
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            current_chunk = sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def create_chunks(
        documents: List[dict[str, Any]],
        max_chars: int = 700,
        strategy_name: str = "sentence_aware"
) -> List[dict[str, Any]]:
    """
    Erstellt eine Liste von Text-Chunks basierend auf den gegebenen Dokumenten. Das Ziel ist,
    den Text jedes Dokuments mit einer maximalen Zeichenanzahl `max_chars` in kleinere
    Chunks zu unterteilen. Jeder erstellte Chunk wird mit einer eindeutigen ID, Kategorie,
    Inhaltsquelle und zusätzlichen Metadaten versehen. Die Strategie zur Chunk-Erzeugung
    kann über den Parameter `strategy_name` spezifiziert werden.

    :param documents: Eine Liste von Dictionaries, wobei jedes Dictionary ein Dokument
        repräsentiert. Die Schlüssel der Dictionaries beinhalten Metadaten wie
        `K_FILENAME` (Dateiname), `K_FILEPATH` (Pfad zur Datei), `K_CATEGORY`
        (Kategorie) und `K_CONTENT` (Textinhalt), die zusammen die Verarbeitung
        strukturieren.
    :param max_chars: Die maximale Anzahl an Zeichen, die ein einzelner Chunk enthalten
        darf. Standardwert ist 700.
    :param strategy_name: Ein String, der die benutzte Strategie zur Erzeugung der
        Text-Chunks definiert. Standardwert ist `"sentence_aware"`.
    :return: Eine Liste von Dictionaries, wobei jedes Dictionary einen erzeugten
        Chunk repräsentiert. Die Chunks enthalten unter anderem folgende Informationen:
        `K_CHUNK_ID` (eindeutige Chunk-ID), `K_SOURCE` (Name der Quelle),
        `K_FILEPATH` (Pfad zur Quelle), `K_CATEGORY` (Kategorie des Dokuments),
        `K_CHUNK_INDEX` (Index des Chunks innerhalb des Dokuments) und
        `K_CONTENT` (Textinhalt des Chunks).
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
                sentence_aware_chunk_text(content, max_chars=max_chars),
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
