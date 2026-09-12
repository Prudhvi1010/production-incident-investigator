"""
src/pipeline/vector_store.py — ChromaDB persistent vector store.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import chromadb
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, CHROMA_DISTANCE
from src.models.document import SourceDocument


class VectorStore:
    """
    ChromaDB-backed persistent vector store.

    Collections are keyed by CHROMA_COLLECTION.
    Supports per-source filtered queries for multi-source retrieval.
    """

    def __init__(self):
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": CHROMA_DISTANCE},
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def upsert(
        self,
        docs: list[SourceDocument],
        embeddings: list[list[float]],
    ) -> None:
        """Upsert documents and their embeddings into the collection."""
        if not docs:
            return
        self._collection.upsert(
            ids=[doc.chroma_id for doc in docs],
            embeddings=embeddings,
            documents=[doc.text for doc in docs],
            metadatas=[
                {
                    "source": doc.source,
                    "doc_id": doc.doc_id,
                    "chunk_index": doc.chunk_index,
                    **{
                        # ChromaDB requires all metadata values to be str/int/float/bool
                        k: (str(v) if not isinstance(v, (str, int, float, bool)) else v)
                        for k, v in doc.metadata.items()
                    },
                }
                for doc in docs
            ],
        )

    def reset(self) -> None:
        """Delete and recreate the collection (full re-index)."""
        try:
            self._client.delete_collection(CHROMA_COLLECTION)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": CHROMA_DISTANCE},
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        source_filter: str | None = None,
    ) -> list[dict]:
        """
        Query by embedding vector. Optionally filter by source.
        Returns list of result dicts with keys: id, text, metadata, distance.
        """
        where = {"source": source_filter} if source_filter else None
        # Clamp n_results to available docs
        available = self.count(source=source_filter)
        n_results = min(n_results, max(1, available))

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        items: list[dict] = []
        for i in range(len(results["ids"][0])):
            items.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )
        return items

    def count(self, source: str | None = None) -> int:
        """Return the number of stored chunks, optionally filtered by source."""
        if source is None:
            return self._collection.count()
        # ChromaDB doesn't have a direct count-with-filter, so peek
        try:
            results = self._collection.get(
                where={"source": source}, include=[]
            )
            return len(results["ids"])
        except Exception:
            return 0

    def get_sources(self) -> list[str]:
        """Return distinct source names present in the collection."""
        try:
            all_meta = self._collection.get(include=["metadatas"])["metadatas"]
            return list({m["source"] for m in all_meta if "source" in m})
        except Exception:
            return []

