"""Adaptives Retrieval der Pipeline v5.

Das Modul entscheidet anhand von Klassifikationsvertrauen, Quellenlage und
interner Qualitätsdiagnose, ob die Wissensbasis-Suche erweitert werden soll.
"""

from typing import Any, List, Optional
from src.v5.core.constants import (
    K_TOP_TEAM, K_CONFIDENCE, K_PASSED, K_EXPAND, K_REASONS,
    K_RETRIEVED_CHUNKS, K_RETRIEVAL_EXPANDED, K_RETRIEVAL_REASONS, K_RETRIEVAL_K,
    V_UNKNOWN, REASON_UNKNOWN_TEAM, REASON_LOW_CLASSIFICATION_CONFIDENCE,
    REASON_TOO_FEW_CHUNKS, REASON_SELF_EVAL_FAILED,
    CLASSIFICATION_REVIEW_THRESHOLD
)


def should_expand_retrieval(
        classification: Optional[dict[str, Any]],
        retrieved_chunks: List[dict[str, Any]],
        self_evaluation_result: Optional[dict[str, Any]] = None,
        minimum_chunks: int = 3
) -> dict[str, Any]:
    """
    Bestimmt, ob die Retrieval-Daten expandiert werden sollten, basierend auf den
    gegebenen Eingabeparametern und Evaluationskriterien. Diese Funktion prüft,
    ob bestimmte Bedingungen wie ein unbekanntes Ziel-Team, eine niedrige
    Klassifikationssicherheit, eine unzureichende Anzahl von
    retrieved_chunks oder ein fehlgeschlagenes
    Selbstevaluierungsergebnis erfüllt sind. Falls eine der genannten
    Bedingungen zutrifft, wird die Erweiterung empfohlen.

    :param classification: Ein Wörterbuch, das die Klassifikationsergebnisse
        enthält. Es sollte relevante Schlüssel wie `K_TOP_TEAM` und
        `K_CONFIDENCE` enthalten, um die Zuordnung und die Sicherheit zu bewerten.
    :param retrieved_chunks: Eine Liste von Wörterbüchern, die die bisher
        abgerufenen Daten-Chunk-Objekte repräsentiert.
    :param self_evaluation_result: Optionales Wörterbuch, das die Ergebnisse der
        Selbstevaluierung enthält, inklusive relevanter Schlüssel wie `K_PASSED`,
        um den Erfolg der Evaluierung zu bestimmen.
    :param minimum_chunks: Die Mindestanzahl von `retrieved_chunks`, die benötigt
        wird, bevor eine Expansion vorgeschlagen wird.
    :return: Ein Wörterbuch mit zwei Schlüsseln: `K_EXPAND`, ein boolescher Wert,
        der angibt, ob eine Expansion empfohlen wird, und `K_REASONS`, eine Liste
        von Gründen, die die Empfehlung unterstützen.
    """
    reasons = []

    if classification is not None:
        if classification.get(K_TOP_TEAM) == V_UNKNOWN:
            reasons.append(REASON_UNKNOWN_TEAM)

        if classification.get(K_CONFIDENCE, 0.0) < CLASSIFICATION_REVIEW_THRESHOLD:
            reasons.append(REASON_LOW_CLASSIFICATION_CONFIDENCE)

    if len(retrieved_chunks) < minimum_chunks:
        reasons.append(REASON_TOO_FEW_CHUNKS)

    if self_evaluation_result is not None:
        if not self_evaluation_result.get(K_PASSED, False):
            reasons.append(REASON_SELF_EVAL_FAILED)

    return {
        K_EXPAND: len(reasons) > 0,
        K_REASONS: reasons
    }


def normalize_k(value: Any, default: int) -> int:
    """
    Normalisiert einen Wert `value` als ganzzahlige Variable `k` und stellt sicher,
    dass der Wert positiv ist. Falls die Umwandlung fehlschlägt oder der Wert nicht
    positiv ist, wird der Standardwert `default` zurückgegeben.

    :param value: Der Eingabewert, der in eine Ganzzahl umgewandelt werden soll. Kann
        beliebigen Typ haben, wird jedoch auf `int` überprüft und konvertiert.
    :param default: Der Standardwert, der zurückgegeben wird, wenn `value` nicht
        konvertiert werden kann oder einen Wert kleiner oder gleich null hat.
    :return: Die normalisierte positive Ganzzahl oder der Standardwert `default`, wenn
        die Konvertierung fehlschlägt oder der Wert ungültig ist.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    if value <= 0:
        return default

    return value


def retrieve_adaptively(
        vector_store: Any,
        inquiry_text: str,
        classification: Optional[dict[str, Any]] = None,
        self_evaluation_result: Optional[dict[str, Any]] = None,
        initial_chunks: Optional[List[dict[str, Any]]] = None,
        initial_k: int = 3,
        expanded_k: int = 6
) -> dict[str, Any]:
    """
    Liefert eine adaptive Suche basierend auf einer initialen Abfrage durch den Benutzer,
    einer optionalen Klassifikation sowie einer optionalen Selbstevaluation des Modells.
    Falls erforderlich, kann die Retrieval-Strategie durch zusätzliche Chunks erweitert
    werden, um relevantere Informationen bereitzustellen. Die Entscheidung zur Erweiterung
    beruht auf den Kriterien der gegebenen Klassifikation und Selbstevaluation.

    :param vector_store: Speicherinstanz, die Methoden zur Vektorsuche bereitstellt.
    :param inquiry_text: Text der Benutzeranfrage, der als Eingabe für die Suche dient.
    :param classification: Optionale Klassifikation der Anfrage in Form eines Dictionaries,
        die zur Optimierung der Retrieval-Strategie verwendet werden kann.
    :param self_evaluation_result: Optionales Ergebnis einer Selbstevaluation des Modells,
        das Rückschlüsse auf die Notwendigkeit der Retrieval-Erweiterung erlaubt.
    :param initial_chunks: Optionale Liste der ursprünglichen Chunks, falls diese bereits
        vorher für die Anfrage abgerufen wurden.
    :param initial_k: Anzahl der Chunks (`k`), die bei der anfänglichen Suche abgerufen
        werden sollen. Standardwert ist 3.
    :param expanded_k: Anzahl der Chunks (`k`), die bei einer erweiterten Suche abgerufen
        werden sollen, falls diese als notwendig erachtet wird. Standardwert ist 6.
    :return: Dictionary mit den abgerufenen Chunks und Metadaten zur Retrieval-Strategie,
        einschließlich der Informationen, ob das Retrieval erweitert wurde, der Gründe
        dafür und der tatsächlich verwendeten `k`-Werten.
    """
    initial_k = normalize_k(initial_k, 3)
    expanded_k = normalize_k(expanded_k, 6)

    if initial_chunks is None:
        initial_chunks = vector_store.search(
            inquiry_text,
            k=initial_k
        )

    expansion_decision = should_expand_retrieval(
        classification,
        initial_chunks,
        self_evaluation_result=self_evaluation_result
    )

    if expansion_decision[K_EXPAND]:
        expanded_chunks = vector_store.search(
            inquiry_text,
            k=expanded_k
        )

        return {
            K_RETRIEVED_CHUNKS: expanded_chunks,
            K_RETRIEVAL_EXPANDED: True,
            K_RETRIEVAL_REASONS: expansion_decision[K_REASONS],
            K_RETRIEVAL_K: expanded_k
        }

    return {
        K_RETRIEVED_CHUNKS: initial_chunks,
        K_RETRIEVAL_EXPANDED: False,
        K_RETRIEVAL_REASONS: [],
        K_RETRIEVAL_K: initial_k
    }
