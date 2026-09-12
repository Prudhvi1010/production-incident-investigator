"""
src/ingestors/cloudwatch.py — Ingestor for AWS CloudWatch log events.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class CloudWatchIngestor(BaseIngestor):
    """
    Ingests CloudWatch log events.
    Each log event becomes its own chunk (events are already atomic).
    Groups of related events are also combined into window chunks.
    """

    source_name = Source.CLOUDWATCH

    def __init__(self, window_size: int = 5):
        self.window_size = window_size

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "cloudwatch_logs.json")
        events: list[dict] = data.get("events", [])
        log_group: str = data.get("log_group", "unknown")
        docs: list[SourceDocument] = []

        # Individual event chunks
        for i, event in enumerate(events):
            text = self._event_to_text(event, log_group)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=f"event-{i}",
                    text=text,
                    metadata={
                        "timestamp": event.get("timestamp", ""),
                        "level": event.get("level", ""),
                        "log_group": log_group,
                        "service": event.get("service", ""),
                        "error_code": event.get("error_code", ""),
                    },
                    chunk_index=0,
                )
            )

        # Sliding window chunks (capture temporal patterns)
        for start in range(0, len(events), self.window_size // 2):
            window = events[start : start + self.window_size]
            if len(window) < 2:
                continue
            text_lines = [f"[CloudWatch Window: {log_group}]"]
            for ev in window:
                text_lines.append(self._event_to_text(ev, log_group))
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=f"window-{start}",
                    text="\n".join(text_lines),
                    metadata={
                        "window_start": events[start].get("timestamp", ""),
                        "window_end": window[-1].get("timestamp", ""),
                        "log_group": log_group,
                        "event_count": len(window),
                    },
                    chunk_index=0,
                )
            )

        return docs

    def _event_to_text(self, event: dict, log_group: str) -> str:
        ts = event.get("timestamp", "")
        level = event.get("level", "INFO")
        msg = event.get("message", "")
        service = event.get("service", "")
        extra = {
            k: v
            for k, v in event.items()
            if k not in {"timestamp", "level", "message", "service"}
        }
        text = f"[CloudWatch | {log_group}] {ts} [{level}] {service}: {msg}"
        if extra:
            details = " | ".join(f"{k}={v}" for k, v in extra.items())
            text += f"\n  Details: {details}"
        return text

