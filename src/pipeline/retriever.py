"""
src/pipeline/retriever.py — Multi-source hybrid retriever.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import ALL_SOURCES, TOP_K_PER_SOURCE, TOP_K_OVERSAMPLE
from src.pipeline.embedder import Embedder
from src.pipeline.vector_store import VectorStore


class Retriever:
    """
    Retrieves candidate chunks from ChromaDB across multiple sources.

    Strategy:
    1. Embed the query once.
    2. Query each enabled source separately (TOP_K_PER_SOURCE per source).
    3. Merge all results, deduplicate by chunk ID.
    4. Sort by embedding distance (ascending = more similar).
    5. Return the top TOP_K_OVERSAMPLE candidates for the reranker.
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        enabled_sources: list[str] | None = None,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.enabled_sources = enabled_sources or ALL_SOURCES

    def retrieve(self, query: str) -> list[dict]:
        """
        Retrieve and merge candidate chunks for the given query.
        Returns list of result dicts sorted by embedding similarity.
        """
        query_embedding = self.embedder.embed(query)
        seen_ids: set[str] = set()
        all_candidates: list[dict] = []

        for source in self.enabled_sources:
            results = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=TOP_K_PER_SOURCE,
                source_filter=source,
            )
            for result in results:
                if result["id"] not in seen_ids:
                    seen_ids.add(result["id"])
                    all_candidates.append(result)

        # Sort by cosine distance (lower = more similar)
        all_candidates.sort(key=lambda x: x["distance"])
        return all_candidates[:TOP_K_OVERSAMPLE]

