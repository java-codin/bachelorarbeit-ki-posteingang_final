"""Quellenextraktion der Pipeline v4.

Die Funktionen gleichen verwendete Quellen aus einem Antwortentwurf mit den
abgerufenen Chunks ab und bereiten Quellenlisten für Evaluation und Ausgabe vor.
"""

from typing import Any

from src.v4.core.constants import K_SOURCE


def extract_used_sources_from_answer(answer: str, retrieved_chunks: list[dict[str, Any]]) -> list[str]:
    """
    Extrahiert eine Liste der genutzten Quellen aus einer Antwort basierend auf den
    bereitgestellten abgerufenen Chunks. Die Funktion identifiziert Quellen, die in
    der textuellen Darstellung der Antwort erscheinen, und gibt diese als Liste zurück.

    :param answer: Die generierte Antwort in Form eines `str`, in der nach genutzten
        Quellen gesucht wird.
    :param retrieved_chunks: Eine Liste von Dictionaries, die abgerufene Dokumenten-Chunks
        darstellen. Jedes Dictionary muss einen Eintrag mit dem Schlüssel `K_SOURCE`
        enthalten, der die Quelle als `str` angibt.
    :return: Eine Liste der genutzten Quellen als `list[str]`, wobei jede Quelle in der
        Antwort vorkommt.
    """
    retrieved_sources = list({
        chunk[K_SOURCE] for chunk in retrieved_chunks
    })

    used_sources = []

    answer_lower = answer.lower()

    for source in retrieved_sources:
        if source.lower() in answer_lower:
            used_sources.append(source)

    return used_sources


def extract_used_chunks_from_sources(used_sources: list[str], retrieved_chunks: list[dict[str, Any]]) -> list[
    dict[str, Any]]:
    """
    Filtert aus einer Liste von Chunks diejenigen, die auf den angegebenen verwendeten Quellen basieren.

    Diese Funktion durchsucht die angegebene Liste von `retrieved_chunks` und gibt nur die
    Einträge zurück, deren `K_SOURCE`-Wert in der Liste `used_sources` enthalten ist. Die
    Gefilterten Chunks stellen die Texte oder Daten dar, die aus relevanten Quellen
    stammen und für die weitere Verarbeitung berücksichtigt werden sollen.

    :param used_sources: Eine Liste von Quellennamen (`str`), die verwendet wurden.
    :param retrieved_chunks: Eine Liste von Chunks, wobei jeder Chunk ein `dict` ist, das Metadaten
        wie die Quelle (`K_SOURCE`) enthält.
    :return: Eine Liste von Chunks (`list[dict[str, Any]]`), die aus den in `used_sources` aufgeführten
        Quellen stammen.
    """
    return [
        chunk for chunk in retrieved_chunks
        if chunk[K_SOURCE] in used_sources
    ]
