"""FAISS-Retrieval der Pipeline v4.

Das Modul baut den Vektorindex aus Chunks auf und liefert relevante
Wissensbasis-Ausschnitte inklusive Retrieval-Distanzen.
"""

import faiss
import numpy as np
from typing import Any

from src.v4.core.constants import (
    DTYPE_FLOAT32,
    K_CONTENT,
    K_DISTANCE,
    K_TEXT,
    RETRIEVAL_K,
)
from src.v4.embeddings import create_embedding, create_embeddings


class VectorStore:
    """
    Die Klasse `VectorStore` verwaltet Dokumente und ermöglicht die Erstellung eines Indexes für
    Vektorsuche sowie eine effiziente Suche innerhalb der gespeicherten Dokumente. Der Hauptzweck
    der Klasse besteht darin, über embedding-basierte Ähnlichkeitsbewertung relevante Dokumente aus
    einer Sammlung abzurufen.

    :ivar documents: Eine Liste von Dokumenten, die für die Suche indexiert wurden. Jedes Dokument
        wird als `dict` repräsentiert.
    :type documents: list[dict[str, Any]]
    :ivar index: Der FAISS-Index, der für die Vektorsuche verwendet wird. Dieser Index ermöglicht
        die Berechnung von Ähnlichkeiten zwischen Vektoren.
    :type index: faiss.IndexFlatL2
    """
    def __init__(self) -> None:
        """
        Repräsentiert eine Klasse zur Initialisierung von Dokumenten und Indexen.

        Diese Klasse dient der Speicherung einer Liste von Dokumenten sowie
        einem Index, der entsprechenden Operationen unterzogen werden kann.

        :ivar documents: Eine Liste, die Dokumente speichert. Initialisiert als leere Liste.
        :ivar index: Eine Indexstruktur. Initialisiert als `None`.
        """
        self.documents = []
        self.index = None

    def build_index(self, chunks: list[dict[str, Any]]) -> None:
        """
        Erstellt einen Index basierend auf den bereitgestellten Dokument-Chunks.

        Die Funktion filtert die übergebenen `chunks`, um sicherzustellen, dass
        nur solche Chunks berücksichtigt werden, die Inhalte unter den Schlüsseln
        `K_CONTENT` oder `K_TEXT` enthalten. Diese Inhalte werden verwendet, um
        Embedding-Vektoren zu erstellen. Anschließend wird ein FAISS-Index mit
        den berechneten Embedding-Vektoren aufgebaut, der zur effizienten
        Ähnlichkeitssuche dient.

        Falls es keine gültigen Dokumente gibt, wird der Index auf `None` gesetzt
        und die Verarbeitung abgebrochen.

        :param chunks: Liste von Wörterbüchern (Daten-Chunks), die verarbeitet
            werden sollen. Jedes Wörterbuch sollte die Schlüssel `K_CONTENT` oder
            `K_TEXT` enthalten, deren Werte Inhalte darstellen, die in den Index
            aufgenommen werden.
        :return: Keine Rückgabe. Der FAISS-Index wird intern in der
            Klasseninstanz gespeichert.
        """
        self.documents = [
            chunk for chunk in chunks
            if (chunk.get(K_CONTENT) or chunk.get(K_TEXT) or "").strip()
        ]

        if not self.documents:
            self.index = None
            return

        texts = [
            chunk.get(K_CONTENT) or chunk.get(K_TEXT)
            for chunk in self.documents
        ]
        embeddings = np.array(create_embeddings(texts)).astype(DTYPE_FLOAT32)

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

    def search(self, query: str, k: int = RETRIEVAL_K) -> list[dict[str, Any]]:
        """
        Führt eine Suchanfrage durch, um relevante Dokumente basierend auf einem Query und
        einer maximalen Anzahl an Ergebnissen (`k`) zu finden. Die Funktion verwendet Embeddings
        und einen Index, um die am besten passenden Dokumente zu identifizieren.

        Die Ähnlichkeiten zwischen dem Query und den Dokumenten werden berechnet, und die
        Ergebnisse werden nach Distanz sortiert. Jedes Dokument im Ergebnis enthält zusätzlich
        eine Metainformation über die berechnete Distanz.

        :param query: Der Eingabetext, auf dessen Basis die Suche durchgeführt wird.
        :param k: Die maximale Anzahl von Dokumenten im Ergebnis. Standardmäßig wird der Wert
            von `RETRIEVAL_K` verwendet.
        :return: Eine Liste von Dokument-Dictionaries, die dem Query entsprechen. Jedes Dokument
            enthält die berechnete Distanz unter dem Schlüssel `K_DISTANCE`.
        """
        if self.index is None or len(self.documents) == 0:
            return []

        query_embedding = np.array([
            create_embedding(query)
        ]).astype(DTYPE_FLOAT32)

        distances, indices = self.index.search(query_embedding, k)

        results = []

        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            document = self.documents[idx].copy()
            document[K_DISTANCE] = float(distance)
            results.append(document)

        return results


def build_vector_store(chunks: list[dict[str, Any]]) -> VectorStore:
    """
    Erstellt einen `VectorStore` und baut einen Index auf Basis der übergebenen
    Daten auf.

    Diese Funktion erzeugt ein neues Objekt vom Typ `VectorStore` und initialisiert
    dessen Index mithilfe der bereitgestellten Liste von Datenfragmenten.
    Die Daten innerhalb der Liste sollten als Wörterbücher strukturiert sein.

    :param chunks: Eine Liste von Datenfragmenten, die als Wörterbücher
        strukturiert sind. Diese Daten werden genutzt, um den Index
        des `VectorStore` aufzubauen.
    :return: Ein `VectorStore`-Objekt, das mit einem Index basierend
        auf den bereitgestellten Dateninitialisiert wurde.
    """
    vector_store = VectorStore()
    vector_store.build_index(chunks)
    return vector_store
