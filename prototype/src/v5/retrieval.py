"""FAISS-Retrieval der Pipeline v5.

Das Modul baut den Vektorindex aus Wissensbasis-Chunks und liefert relevante
Quellen inklusive Distanz- und Score-Metadaten.
"""

from typing import Any, List, Optional

import numpy as np
import faiss

from src.v5.embeddings import create_embedding, create_embeddings
from src.v5.core.constants import K_CONTENT, K_TEXT, K_DISTANCE, K_SCORE, DTYPE_FLOAT32


class VectorStore:
    """
    Eine Klasse zur Verwaltung und Suche in einem Vektorspeicher.

    Diese Klasse implementiert einen Vektorspeicher, der durch FAISS-Indizes
    durchsuchbar gemacht wird. Der Speicher unterstützt die Einbettung von
    Dokumenten in Vektorform und ermöglicht die Suche nach den
    relevantesten Einträgen basierend auf einer Anfrage.

    :ivar documents: Eine Liste der gespeicherten Dokumente.
    :type documents: List[dict[str, Any]]
    :ivar index: Der FAISS-Index für die Vektorrepräsentationen der Dokumente.
    :type index: Optional[faiss.IndexFlatL2]
    """
    def __init__(self) -> None:
        """
        Initialisiert eine Instanz der Klasse.

        Die Klasse organisiert und verarbeitet Dokumente sowie deren Indexierung und unterstützt
        embeddings-basierte Abfragen. Die Attribute dienen der Verwaltung der Dokumente, der Erstellung
        eines FAISS-Indizes und der Zwischenspeicherung von Query-Embeddings.

        Attributes:
            documents (List[dict[str, Any]]): Eine Liste von Dokumenten, die in Form von
                Dictionaries vorliegen. Jedes Dictionary speichert Informationen zu einem
                individuellen Dokument.
            index (Optional[faiss.IndexFlatL2]): Ein optionaler FAISS-Index, der zur Suche
                und Verwaltung von Dokumentembeddings verwendet wird.
        """
        self.documents: List[dict[str, Any]] = []
        self.index: Optional[faiss.IndexFlatL2] = None
        self._query_embedding_cache: dict[str, np.ndarray] = {}

    def build_index(self, chunks: List[dict[str, Any]]) -> None:
        """
        Führt den Aufbau eines Indexes aus, indem Embeddings aus den gegebenen Daten berechnet
        und zu einem FAISS-Index hinzugefügt werden.

        Diese Methode dient zur Erstellung eines Index basierend auf einer Liste von Dokumenten
        und deren Embeddings. Der Index erlaubt spätere effiziente Ähnlichkeitssuche. Es werden
        ausschließlich Dokumente berücksichtigt, die Inhalte im Feld `K_CONTENT` oder `K_TEXT`
        enthalten.

        :param chunks:
            Eine Liste von Dokumenten, die als Eingabe für den Aufbau des Indexes dient. Jedes Dokument
            ist ein Wörterbuch mit potentiellen Feldern `K_CONTENT` und/oder `K_TEXT`, welche die relevanten
            Inhalte enthalten.
        :return:
            Kein Rückgabewert. Der erstellte Index wird als Attribut `index` in der Instanz gespeichert.
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
        self._query_embedding_cache.clear()

    def search(
            self,
            query: str,
            k: Optional[int] = 3,
            top_k: Optional[int] = None
    ) -> List[dict[str, Any]]:
        """
        Führt eine Ähnlichkeitssuche mit einem gegebenen `query` durch und gibt die
        relevantesten Ergebnisse aus der Dokumentensammlung zurück. Basierend auf
        einer eingebetteten Repräsentation des `query` und der Dokumente wird die
        Suche in einem vordefinierten Index durchgeführt.

        Ergebnisse werden nach der Ähnlichkeit mit dem `query` bewertet und enthalten
        sowohl die Distanz als auch einen berechneten Score für die Relevanz.
        Standardmäßig wird die L2-Distanz verwendet, wobei ein niedrigerer Wert eine
        höhere Ähnlichkeit darstellt.

        :param query: Die Anfrage, die für die Ähnlichkeitssuche verwendet wird.
        :param k: Die maximale Anzahl der zurückzugebenden Ergebnisse
            (Standardwert ist `3`).
        :param top_k: Optionaler Ersatz für `k`, um die Anzahl der Ergebnisse
            explizit festzulegen. Falls angegeben, überschreibt `top_k` den Wert von `k`.
        :return: Eine Liste der Ergebnisse. Jedes Ergebnis ist ein `dict`, das die
            Informationen des entsprechenden Dokuments zusammen mit `K_DISTANCE`
            und `K_SCORE` enthält, die die Ähnlichkeitswerte darstellen.
        """
        if top_k is not None:
            k = top_k

        if k is None:
            k = 3

        try:
            k = int(k)
        except(TypeError, ValueError):
            k = 3

        if k <= 0:
            k = 3

        if self.index is None or len(self.documents) == 0:
            return []

        if query not in self._query_embedding_cache:
            self._query_embedding_cache[query] = np.array([
                create_embedding(query)
            ]).astype(DTYPE_FLOAT32)

        query_embedding = self._query_embedding_cache[query]

        k = min(k, len(self.documents))

        distances, indices = self.index.search(query_embedding, k)

        results = []

        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            document = self.documents[idx].copy()
            document[K_DISTANCE] = float(distance)

            # Bei L2-Distanz gilt: Kleiner ist = besser.
            # Score ist nur eine lesbare Hilfskennzahl
            document[K_SCORE] = float(1 / (1 + distance))

            results.append(document)

        return results


def build_vector_store(chunks: List[dict[str, Any]]) -> VectorStore:
    """
    Erstellt und gibt einen `VectorStore` zurück, der auf Basis der übergebenen
    `chunks` aufgebaut wird. Der `VectorStore` wird verwendet, um Indexstrukturen
    zu erstellen, die eine effiziente Abfrage von Vektordaten ermöglichen.

    :param chunks: Eine Liste von Wörterbüchern, die die Daten enthalten, aus
        denen der Index im `VectorStore` erstellt wird. Jedes Wörterbuch in der
        Liste repräsentiert eine einzelne Einheit von Daten, die indiziert werden
        soll.
    :return: Ein `VectorStore`, der die erstellten Indexstrukturen enthält.
    """
    vector_store = VectorStore()
    vector_store.build_index(chunks)
    return vector_store
