"""FAISS-Retrieval der Pipeline v3.

Das Modul baut einen Vektorindex aus Wissensbasis-Chunks und sucht relevante
Quellen für die Antwortgenerierung.
"""

import faiss
import numpy as np
from typing import List

from src.v3.core import constants as c
from src.v3.embeddings import create_embedding, create_embeddings


class VectorStore:
    """
    Verwaltet eine Sammlung von Dokumenten und ermöglicht deren Suche durch
    Nutzung von Embedding-gestützter Ähnlichkeitsbewertung.

    Diese Klasse dient als einfaches Framework für das Speichern von Dokumenten, das
    Erstellen eines Vektorraumbasierten Indexes und das Durchführen von Ähnlichkeitssuchen.
    Sie unterstützt einen prototypischen Workflow, der in Zusammenhang mit der Bewertung
    von Generative AI Anwendungen, wie z. B. Klassifikation, Routing, und Abrufoperationen,
    stehen könnte.

    :ivar documents: Liste der gespeicherten Dokumente, die als Eingabedaten für die
                     Indizierung und Suche verwendet werden.
    :type documents: list
    :ivar index: Repräsentiert den FAISS-Index für die Embedding-Suche. Falls keine
                 Dokumente vorhanden sind, bleibt dieser auf `None` gesetzt.
    :type index: Optional[faiss.Index]
    """
    def __init__(self) -> None:
        self.documents = []
        self.index = None

    def build_index(self, chunks: List[dict]) -> None:
        """
        Erstellt einen FAISS-Index basierend auf den übergebenen Daten.

        Diese Funktion verarbeitet die übergebenen `chunks`, filtert leere oder
        irrelevante Inhalte heraus und erstellt einen FAISS-Index für effiziente
        nähere Nachbarschaftssuche (KNN) auf Grundlage von Embedding-Vektoren.

        :param chunks: Eine Liste von `dict`-Objekten. Jedes `dict` enthält mögliche
            Inhalte, wie durch die Schlüsselkonstanten `K_CONTENT` oder `K_TEXT` definiert.
        :return: Gibt nichts zurück. Die Ergebnisse werden als Attribute gespeichert:
            - `documents`: Gefilterte Liste der Eingabe-Daten abhängig von validem Inhalt.
            - `index`: Der erstellte FAISS-Index, falls gültige Daten vorliegen.
        """
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

    def search(self, query: str, k: int = c.RETRIEVAL_K) -> List[dict]:
        """
        Sucht relevante Dokumente in einem Vektorindex basierend auf einer Abfrage und gibt die
        am besten passenden Ergebnisse zurück.

        Die Funktion nutzt einen Vektorähnlichkeits-Ansatz, um die Abfrage (`query`) mit den zuvor
        indizierten Dokumenten zu vergleichen. Das Ergebnis sind bis zu `k` Dokumente mit der
        niedrigsten Distanz zur Abfrage. Für jedes Ergebnis wird die Distanz zum Abfragevektor
        hinzugefügt.

        :param query: Die Abfrage, für die relevante Dokumente im Index gesucht werden sollen.
        :param k: Die maximale Anzahl der zurückzugebenden Ergebnisse. Standardwert ist durch
            `c.RETRIEVAL_K` definiert.
        :return: Eine Liste von Dokumenten, die relevantesten Dokumente im Index. Jedes Dokument
            enthält die ursprünglichen Felder sowie die berechnete Distanz (`c.K_DISTANCE`) zur Abfrage.
        """
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
    Erstellt und baut einen Index für einen VectorStore basierend auf den
    übergebenen `chunks`. Diese Funktion dient zur Initialisierung und
    Strukturierung eines vektorbasierten Speichersystems, das in der
    wissenschaftlichen Prototypentwicklung zur Klassifikation, Routing
    oder Antwortentwürfen verwendet werden kann.

    :param chunks: Die Daten, die in den VectorStore eingefügt und indexiert
        werden sollen.
    :type chunks: list
    :return: Ein instanziierter und indexierter VectorStore.
    :rtype: VectorStore
    """
    vector_store = VectorStore()
    vector_store.build_index(chunks)
    return vector_store
