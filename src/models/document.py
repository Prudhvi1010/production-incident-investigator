"""
src/models/document.py — Core data model for ingested source chunks.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceDocument:
    """A single chunk of text from an operational data source."""

    source: str               # Source name (e.g. "cloudwatch", "jira")
    doc_id: str               # Unique document identifier within the source
    text: str                 # Chunk text — what gets embedded and retrieved
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0      # Position within the parent document

    @property
    def chroma_id(self) -> str:
        """Stable unique ID for ChromaDB upserts."""
        return f"{self.source}::{self.doc_id}::chunk{self.chunk_index}"

    def __repr__(self) -> str:
        preview = self.text[:80].replace("\n", " ")
        return f"<SourceDocument source={self.source!r} id={self.doc_id!r} chunk={self.chunk_index} text={preview!r}...>"

