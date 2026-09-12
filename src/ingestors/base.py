"""
src/ingestors/base.py — Abstract base class for all source ingestors.
"""
from abc import ABC, abstractmethod
from pathlib import Path
import json
import sys

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.document import SourceDocument


class BaseIngestor(ABC):
    """All ingestors implement this interface."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the canonical source identifier (e.g. 'cloudwatch')."""
        ...

    @abstractmethod
    def ingest(self) -> list[SourceDocument]:
        """Load raw data, chunk it, and return SourceDocuments."""
        ...

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_json(self, path: Path) -> dict | list:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 400,
        overlap: int = 40,
    ) -> list[str]:
        """Split text into word-count chunks with overlap."""
        words = text.split()
        chunks: list[str] = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)
            if i + chunk_size >= len(words):
                break
            i += chunk_size - overlap
        return chunks

    def _dict_to_text(self, d: dict, indent: int = 0) -> str:
        """Flatten a nested dict to readable key: value lines."""
        lines: list[str] = []
        prefix = "  " * indent
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}:")
                lines.append(self._dict_to_text(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{prefix}{k}: {', '.join(str(i) for i in v)}")
            else:
                lines.append(f"{prefix}{k}: {v}")
        return "\n".join(lines)

