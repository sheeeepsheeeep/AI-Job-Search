"""
ChromaDB vector store service for document embedding and semantic search.
Uses PersistentClient so embeddings survive server restarts.
"""

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Wrapper around ChromaDB for adding, querying, and deleting documents."""

    def __init__(self, persist_dir: str) -> None:
        """Initialise the ChromaDB persistent client.

        Args:
            persist_dir: Directory where ChromaDB stores its data on disk.
        """
        self._persist_dir = persist_dir
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Default collection for job-search documents
        self._collection = self._client.get_or_create_collection(
            name="job_search_docs",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStoreService initialised – persist_dir=%s", persist_dir)

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        """Return an existing collection or create a new one.

        Args:
            name: Collection name.

        Returns:
            The ChromaDB Collection object.
        """
        collection = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Using collection '%s' (count=%d)", name, collection.count())
        return collection

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Add (or update) a document in the vector store.

        Args:
            doc_id: Unique identifier for the document.
            text: The text content to embed and store.
            metadata: Optional key-value metadata attached to the document.
            collection_name: Optional collection to use; defaults to the main collection.
        """
        col = (
            self.get_or_create_collection(collection_name)
            if collection_name
            else self._collection
        )
        col.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        logger.info("Upserted document '%s' into collection '%s'", doc_id, col.name)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        collection_name: str | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform a semantic similarity search.

        Args:
            query_text: Natural-language query.
            n_results: Maximum number of results to return.
            collection_name: Optional collection to query.
            where: Optional metadata filter (ChromaDB where clause).

        Returns:
            List of dicts, each containing 'id', 'document', 'metadata', and
            'distance' keys, ordered by relevance (closest first).
        """
        col = (
            self.get_or_create_collection(collection_name)
            if collection_name
            else self._collection
        )

        # Guard against querying an empty collection
        if col.count() == 0:
            logger.warning("Query on empty collection '%s' – returning []", col.name)
            return []

        query_params: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": min(n_results, col.count()),
        }
        if where:
            query_params["where"] = where

        results = col.query(**query_params)

        # Flatten the batch-of-one into a simple list
        documents: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            documents.append(
                {
                    "id": doc_id,
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distances[i] if i < len(distances) else None,
                }
            )

        logger.info(
            "Query returned %d results from collection '%s'",
            len(documents),
            col.name,
        )
        return documents

    def delete_document(
        self,
        doc_id: str,
        collection_name: str | None = None,
    ) -> None:
        """Remove a document from the vector store.

        Args:
            doc_id: The identifier of the document to delete.
            collection_name: Optional collection to target.
        """
        col = (
            self.get_or_create_collection(collection_name)
            if collection_name
            else self._collection
        )
        col.delete(ids=[doc_id])
        logger.info("Deleted document '%s' from collection '%s'", doc_id, col.name)

    def list_collections(self) -> list[str]:
        """Return names of all collections in the store."""
        return [c.name for c in self._client.list_collections()]
