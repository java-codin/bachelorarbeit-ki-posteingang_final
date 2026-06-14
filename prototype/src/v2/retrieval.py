"""FAISS-Retrieval der Pipeline v2.

Das Modul baut einen lokalen Vektorindex aus Chunks und sucht relevante
Wissensbasis-Ausschnitte für ein Bürgeranliegen.
"""

import faiss
import numpy as np

from src.v2.core import constants as c
from src.v2.embeddings import create_embedding, create_embeddings


class VectorStore:
    """
    Eine Klasse zur Verwaltung und Suche von Vektordarstellungen von Dokumenten.

    Diese Klasse unterstützt das Erstellen eines Indexes für Dokumente basierend auf
    ihren Vektor-Einbettungen. Sie ermöglicht die Suche nach ähnlichen Dokumenten
    basierend auf einer Abfrage, indem sie den nächstliegenden Nachbarn im
    Vektorraum findet.

    :ivar documents: Liste von Dokumenten, die dem Index hinzugefügt wurden.
    :type documents: list
    :ivar index: Der FAISS-Index für die Suche im Vektorraum.
    :type index: Union[faiss.IndexFlatL2, None]
    """
    def __init__(self):
        self.documents = []
        self.index = None

    def build_index(self, chunks):
        self.documents = [
            chunk for chunk in chunks
            if (chunk.get(c.K_CONTENT) or chunk.get(c.K_TEXT) or "").strip()
        ]

        if not self.documents:
            self.index = None
            return

        texts = [
            chunk.get(c.K_CONTENT) or chunk.get(c.K_TEXT)
            for chunk in self.documents
        ]
        embeddings = np.array(create_embeddings(texts)).astype(c.DTYPE_FLOAT32)

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

    def search(self, query, k=c.RETRIEVAL_K):
        if self.index is None or len(self.documents) == 0:
            return []

        query_embedding = np.array([
            create_embedding(query)
        ]).astype(c.DTYPE_FLOAT32)

        distances, indices = self.index.search(query_embedding, k)

        results = []

        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            document = self.documents[idx].copy()
            document[c.K_DISTANCE] = float(distance)
            results.append(document)

        return results


def build_vector_store(chunks):
    """
    Erstellt und initialisiert einen neuen `VectorStore` unter Verwendung der übergebenen `chunks`.

    Diese Funktion erzeugt eine Instanz von `VectorStore` und baut einen Index basierend
    auf den übergebenen `chunks`. `chunks` repräsentiert die Daten, die im `VectorStore`
    verarbeitet und indexiert werden sollen.

    :param chunks: Die Daten, die im `VectorStore` indexiert werden sollen.
    :type chunks: list
    :return: Eine initialisierte Instanz von `VectorStore`, bei der der Index auf Grundlage
             der `chunks` aufgebaut wurde.
    :rtype: VectorStore
    """
    vector_store = VectorStore()
    vector_store.build_index(chunks)
    return vector_store
