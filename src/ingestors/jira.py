"""
src/ingestors/jira.py — Ingestor for Jira incident tickets.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class JiraIngestor(BaseIngestor):
    """
    Ingests Jira incident tickets.
    Each ticket produces: a full summary chunk, and one chunk per comment.
    """

    source_name = Source.JIRA

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "jira_incidents.json")
        incidents: list[dict] = data.get("incidents", [])
        docs: list[SourceDocument] = []

        for incident in incidents:
            ticket_id = incident.get("key", incident.get("id", "UNKNOWN"))

            # Full ticket summary chunk
            summary_text = self._ticket_to_text(incident)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=ticket_id,
                    text=summary_text,
                    metadata={
                        "ticket_id": ticket_id,
                        "priority": incident.get("priority", ""),
                        "status": incident.get("status", ""),
                        "created": incident.get("created", ""),
                        "summary": incident.get("summary", ""),
                        "assignee": incident.get("assignee", ""),
                    },
                    chunk_index=0,
                )
            )

            # One chunk per comment (rich investigation context)
            comments = incident.get("comments", [])
            for ci, comment in enumerate(comments):
                comment_text = (
                    f"[Jira Comment | {ticket_id}]\n"
                    f"Author: {comment.get('author', 'unknown')} | "
                    f"Time: {comment.get('created', '')}\n"
                    f"{comment.get('body', '')}"
                )
                docs.append(
                    SourceDocument(
                        source=self.source_name,
                        doc_id=ticket_id,
                        text=comment_text,
                        metadata={
                            "ticket_id": ticket_id,
                            "comment_index": ci,
                            "author": comment.get("author", ""),
                            "created": comment.get("created", ""),
                        },
                        chunk_index=ci + 1,
                    )
                )

        return docs

    def _ticket_to_text(self, incident: dict) -> str:
        lines = [
            f"[Jira Incident | {incident.get('key', '')}]",
            f"Summary: {incident.get('summary', '')}",
            f"Priority: {incident.get('priority', '')} | Severity: {incident.get('severity', '')}",
            f"Status: {incident.get('status', '')} | Assignee: {incident.get('assignee', '')}",
            f"Created: {incident.get('created', '')}",
            f"Components: {', '.join(incident.get('components', []))}",
            f"Labels: {', '.join(incident.get('labels', []))}",
            "",
            "Description:",
            incident.get("description", ""),
        ]
        if incident.get("resolution"):
            lines += ["", f"Resolution: {incident['resolution']}"]
        if incident.get("affected_customers"):
            lines.append(f"Affected Customers: {incident['affected_customers']}")
        if incident.get("revenue_impact_usd"):
            lines.append(f"Revenue Impact: ${incident['revenue_impact_usd']:,}")
        return "\n".join(lines)

