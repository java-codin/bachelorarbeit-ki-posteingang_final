"""Embedding-Zugriff der Pipeline v3.

Die Datei hält den versionsspezifischen Importpfad stabil und delegiert die
eigentliche Embedding-Erzeugung an die gemeinsame Implementierung.
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
