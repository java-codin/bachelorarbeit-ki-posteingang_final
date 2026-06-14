"""Embedding-Zugriff der Pipeline v2.

Die Datei erhält den historischen Importpfad von v2 und delegiert die eigentliche
Embedding-Erzeugung an die gemeinsame Implementierung.
"""

from shared.embeddings import (
    create_embedding,
    create_embeddings,
    get_embedding_metadata
)

__all__ = [
    "create_embedding",
    "create_embeddings",
    "get_embedding_metadata",
]
