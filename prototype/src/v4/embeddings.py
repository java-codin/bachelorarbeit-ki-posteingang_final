"""Embedding-Zugriff der Pipeline v4.

Die Datei erhält den v4-Importpfad und delegiert die eigentliche
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
