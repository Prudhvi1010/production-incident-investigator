"""
src/ingestors/runbook.py — Ingestor for operational runbooks.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class RunbookIngestor(BaseIngestor):
    """
    Ingests runbooks.
    Creates a summary chunk per runbook and one chunk per step group.
    """

    source_name = Source.RUNBOOK

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "runbooks.json")
        docs: list[SourceDocument] = []

        for rb in data.get("runbooks", []):
            rb_id = rb.get("id", "unknown")

            # Runbook header chunk
            header = self._runbook_header(rb)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=rb_id,
                    text=header,
                    metadata={
                        "runbook_id": rb_id,
                        "title": rb.get("title", ""),
                        "service": rb.get("service", ""),
                        "severity_applicability": rb.get("severity_applicability", []),
                        "type": "header",
                    },
                    chunk_index=0,
                )
            )

            # One chunk per step
            for step in rb.get("steps", []):
                step_text = self._step_to_text(rb_id, rb.get("title", ""), step)
                docs.append(
                    SourceDocument(
                        source=self.source_name,
                        doc_id=rb_id,
                        text=step_text,
                        metadata={
                            "runbook_id": rb_id,
                            "step_number": step.get("step", 0),
                            "step_title": step.get("title", ""),
                            "service": rb.get("service", ""),
                            "type": "step",
                        },
                        chunk_index=step.get("step", 0),
                    )
                )

        return docs

    def _runbook_header(self, rb: dict) -> str:
        lines = [
            f"[Runbook | {rb.get('id', '')}]",
            f"Title: {rb.get('title', '')}",
            f"Service: {rb.get('service', '')} | Version: {rb.get('version', '')}",
            f"Last Updated: {rb.get('last_updated', '')} | Owner: {rb.get('owner', '')}",
            f"Applies to Severity: {', '.join(rb.get('severity_applicability', []))}",
            f"Description: {rb.get('description', '')}",
            f"Steps: {len(rb.get('steps', []))}",
        ]
        escalation = rb.get("escalation", {})
        if escalation:
            lines.append("Escalation:")
            for level, contact in escalation.items():
                lines.append(f"  {level}: {contact}")
        return "\n".join(lines)

    def _step_to_text(self, rb_id: str, rb_title: str, step: dict) -> str:
        lines = [
            f"[Runbook | {rb_id} | Step {step.get('step', '?')}: {step.get('title', '')}]",
            f"Runbook: {rb_title}",
        ]
        if step.get("condition"):
            lines.append(f"Condition: {step['condition']}")
        lines.append("Actions:")
        for action in step.get("actions", []):
            lines.append(f"  - {action}")
        return "\n".join(lines)

