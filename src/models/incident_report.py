"""
src/models/incident_report.py — Structured output model for Gemini-generated reports.
"""
from pydantic import BaseModel, Field
from typing import Literal


class TimelineEvent(BaseModel):
    timestamp: str = Field(description="ISO 8601 timestamp or relative time string")
    event: str = Field(description="Description of what happened at this point")
    source: str = Field(description="Which data source this event came from")


class EvidenceItem(BaseModel):
    source: str = Field(description="Data source (cloudwatch, jira, github, etc.)")
    doc_id: str = Field(description="Document/ticket/PR identifier")
    excerpt: str = Field(description="Relevant text excerpt from the source")
    relevance_score: float = Field(description="Reranker relevance score 0-10")


class IncidentReport(BaseModel):
    incident_id: str = Field(description="Incident identifier (e.g. INC-20240315-001)")
    severity: Literal["P1", "P2", "P3", "P4"] = Field(description="Incident severity")
    summary: str = Field(description="2-3 sentence executive summary of the incident")
    root_cause: str = Field(description="Detailed root cause explanation with evidence")
    timeline: list[TimelineEvent] = Field(description="Chronological sequence of events")
    affected_services: list[str] = Field(description="List of impacted services")
    evidence: list[EvidenceItem] = Field(description="Top supporting evidence chunks")
    recommended_fix: str = Field(description="Detailed fix recommendation")
    rollback_steps: list[str] = Field(description="Ordered rollback/remediation steps")
    prevention: str = Field(description="How to prevent this class of incident in future")
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Confidence in root cause based on evidence quality"
    )

    def to_markdown(self) -> str:
        """Render the report as markdown for display."""
        sev_emoji = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}.get(self.severity, "⚪")
        conf_emoji = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❓"}.get(self.confidence, "")
        lines = [
            f"# Incident Report: {self.incident_id}",
            f"**Severity**: {sev_emoji} {self.severity}  |  **Confidence**: {conf_emoji} {self.confidence}",
            "",
            "## 📋 Summary",
            self.summary,
            "",
            "## 🔍 Root Cause",
            self.root_cause,
            "",
            "## ⏱️ Timeline",
        ]
        for ev in self.timeline:
            lines.append(f"- `{ev.timestamp}` — **{ev.source}** — {ev.event}")
        lines += [
            "",
            "## 🏗️ Affected Services",
            ", ".join(f"`{s}`" for s in self.affected_services),
            "",
            "## 🛠️ Recommended Fix",
            self.recommended_fix,
            "",
            "## 🔄 Rollback Steps",
        ]
        for i, step in enumerate(self.rollback_steps, 1):
            lines.append(f"{i}. {step}")
        lines += [
            "",
            "## 🛡️ Prevention",
            self.prevention,
            "",
            "## 📎 Evidence",
        ]
        for ev in self.evidence:
            lines.append(f"### [{ev.source.upper()}] {ev.doc_id} (score: {ev.relevance_score:.1f})")
            lines.append(f"> {ev.excerpt[:300]}")
            lines.append("")
        return "\n".join(lines)

