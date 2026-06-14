"""Quellenextraktion und Quellen-ID-Abgleich der Pipeline v5.

Die Funktionen ordnen vom LLM genannte Quellen-IDs den tatsächlich abgerufenen
Chunks zu und markieren ungültige Quellenverweise für Guardrails.
"""

from typing import Any, List

from src.v5.core.constants import K_SOURCE, K_SOURCE_ID, K_USED_SOURCE_IDS, K_INVALID_SOURCE_IDS, K_USED_SOURCES, \
    K_USED_CHUNKS


def attach_source_ids(retrieved_chunks: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """
    Fügt eindeutige Quellen-IDs zu den übergebenen Chunks hinzu.

    Diese Funktion bereichert die übergebenen `retrieved_chunks`, die als Liste von
    Dictionaries vorliegen, indem sie jedem Chunk ein neues Feld `K_SOURCE_ID`
    hinzufügt. Dieses Feld enthält eine eindeutige ID in der Form von `"S<Index>"`,
    wobei `<Index>` die Position des Chunks in der Liste ist, beginnend bei 1.
    Das Resultat ist eine Liste mit angereicherten Chunks.

    :param retrieved_chunks: Eine Liste von Chunks, dargestellt als
        `List[dict[str, Any]]`, die verarbeitet werden sollen.
    :return: Eine Liste von Chunks, wobei jeder Chunk um eine eindeutige
        Quellen-ID im Feld `K_SOURCE_ID` ergänzt wurde.
    :rtype: List[dict[str, Any]]
    """
    chunks_with_ids = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        enriched = chunk.copy()
        enriched[K_SOURCE_ID] = f"S{index}"
        chunks_with_ids.append(enriched)

    return chunks_with_ids


def resolve_used_sources(
        used_source_ids: List[str],
        retrieved_chunks: List[dict[str, Any]]
) -> dict[str, Any]:
    """
    Löst die verwendeten Quell-IDs auf, indem überprüft wird, ob die angegebenen Quell-IDs
    in den bereitgestellten Daten vorhanden sind. Die Funktion ordnet dabei gültige Quell-IDs
    ihren entsprechenden Daten zu und generiert Listen der verwendeten Quellen und der
    ungültigen Quell-IDs.

    :param used_source_ids: Eine Liste von Quell-IDs, die aufgelöst werden sollen.
    :param retrieved_chunks: Eine Liste von Dictionaries mit den Datenfragmenten,
        die zur Überprüfung der Quell-IDs herangezogen werden. Jedes Dictionary sollte
        das Schlüssel-Attribut `K_SOURCE_ID` zur Identifikation enthalten.
    :return: Ein Dictionary mit den folgenden Schlüsseln:
        - `K_USED_SOURCE_IDS`: Eine Liste der Quell-IDs, die erfolgreich aufgelöst wurden.
        - `K_USED_SOURCES`: Eine Liste der Datennamen der erfolgreichen Quellen.
        - `K_USED_CHUNKS`: Eine Liste der Datenfragmente, die zu den erfolgreich
          aufgelösten Quell-IDs gehören.
        - `K_INVALID_SOURCE_IDS`: Eine Liste der Quell-IDs, die nicht in `retrieved_chunks`
          gefunden wurden.
    """
    valid_ids = {
        chunk[K_SOURCE_ID]: chunk
        for chunk in retrieved_chunks
        if K_SOURCE_ID in chunk
    }

    resolved_chunks = []
    invalid_ids = []

    for source_id in used_source_ids or []:
        if source_id in valid_ids:
            resolved_chunks.append(valid_ids[source_id])
        else:
            invalid_ids.append(source_id)

    used_sources = sorted({
        chunk[K_SOURCE]
        for chunk in resolved_chunks
    })

    return {
        K_USED_SOURCE_IDS: [chunk[K_SOURCE_ID] for chunk in resolved_chunks],
        K_USED_SOURCES: used_sources,
        K_USED_CHUNKS: resolved_chunks,
        K_INVALID_SOURCE_IDS: invalid_ids
    }
