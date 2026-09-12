"""
src/investigator.py — Main orchestrator for the Production Incident Investigator RAG.

Pipeline:
  Sources → Ingestors → Embedder → VectorStore
                                         ↓
  Query ──────────────────────── Retriever → Reranker → Generator → IncidentReport
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google import genai

from config import ALL_SOURCES
from src.ingestors import get_all_ingestors, BaseIngestor
from src.pipeline.embedder import Embedder
from src.pipeline.vector_store import VectorStore
from src.pipeline.retriever import Retriever
from src.pipeline.reranker import Reranker
from src.pipeline.generator import Generator
from src.models.incident_report import IncidentReport

load_dotenv()


class Investigator:
    """
    Top-level orchestrator.

    Usage:
        investigator = Investigator()
        investigator.ingest_all()                        # one-time ingestion
        report = investigator.investigate("payment 500s") # investigate any query
    """

    def __init__(
        self,
        enabled_sources: list[str] | None = None,
        api_key: str | None = None,
    ):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Add it to your .env file or pass api_key= argument."
            )

        self.client = genai.Client(api_key=api_key)
        self.enabled_sources = enabled_sources or ALL_SOURCES

        self.embedder = Embedder(self.client)
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.embedder, self.vector_store, self.enabled_sources)
        self.reranker = Reranker(self.client)
        self.generator = Generator(self.client)

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest_all(
        self,
        verbose: bool = True,
        reset: bool = False,
    ) -> int:
        """
        Ingest all 7 sources into the vector store.

        Args:
            verbose: Print progress to stdout.
            reset: Wipe the vector store before ingesting (full re-index).

        Returns:
            Total number of chunks ingested.
        """
        if reset:
            if verbose:
                print("🗑️  Resetting vector store...")
            self.vector_store.reset()

        ingestors = get_all_ingestors()
        total = 0
        for ingestor in ingestors:
            docs = ingestor.ingest()
            if not docs:
                if verbose:
                    print(f"  ⚠️  {ingestor.source_name}: 0 documents")
                continue
            embeddings = self.embedder.embed_batch(
                [d.text for d in docs], verbose=verbose
            )
            self.vector_store.upsert(docs, embeddings)
            total += len(docs)
            if verbose:
                print(f"  ✅ {ingestor.source_name}: {len(docs)} chunks ingested")

        if verbose:
            print(f"\n📦 Total chunks in store: {self.vector_store.count()}")
        return total

    def ingest_source(self, ingestor: BaseIngestor, verbose: bool = True) -> int:
        """Ingest a single source."""
        docs = ingestor.ingest()
        if not docs:
            return 0
        embeddings = self.embedder.embed_batch([d.text for d in docs], verbose=verbose)
        self.vector_store.upsert(docs, embeddings)
        if verbose:
            print(f"✅ {ingestor.source_name}: {len(docs)} chunks ingested")
        return len(docs)

    # ── Investigation ─────────────────────────────────────────────────────────

    def investigate(
        self,
        query: str,
        verbose: bool = False,
    ) -> tuple[IncidentReport, dict]:
        """
        Run the full RAG pipeline for an incident query.

        Returns:
            (IncidentReport, pipeline_metadata dict)
        """
        meta: dict = {"query": query}

        # 1. Retrieve
        if verbose:
            print(f"🔍 Retrieving candidates for: {query!r}")
        candidates = self.retriever.retrieve(query)
        meta["candidates_count"] = len(candidates)
        if verbose:
            print(f"  Found {len(candidates)} candidates from {self.enabled_sources}")

        # 2. Rerank
        if verbose:
            print("📊 Reranking with Gemini Flash...")
        ranked = self.reranker.rerank(query, candidates)
        meta["ranked_count"] = len(ranked)
        meta["sources_in_context"] = list({c["metadata"].get("source", "") for c in ranked})
        if verbose:
            print(f"  {len(ranked)} chunks passed reranking threshold")

        # 3. Generate
        if verbose:
            print("🤖 Generating incident report with Gemini 3.1 Pro Preview...")
        report = self.generator.generate(query, ranked)
        meta["report_severity"] = report.severity
        meta["report_confidence"] = report.confidence

        return report, meta

    # ── Utilities ─────────────────────────────────────────────────────────────

    def store_stats(self) -> dict:
        """Return stats about the current vector store contents."""
        sources = self.vector_store.get_sources()
        return {
            "total_chunks": self.vector_store.count(),
            "sources": {s: self.vector_store.count(source=s) for s in sources},
        }

    def is_indexed(self) -> bool:
        """Check if the vector store has any documents."""
        return self.vector_store.count() > 0

