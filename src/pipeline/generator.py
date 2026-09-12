"""
src/pipeline/generator.py — Structured incident report generator using Gemini 2.5 Pro.

Builds a rich prompt from the reranked chunks and calls gemini-2.5-pro with a
JSON schema to produce a fully structured IncidentReport.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google import genai
from config import LLM_MODEL
from src.models.incident_report import IncidentReport


# ── JSON schema for structured output ────────────────────────────────────────
_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "incident_id":        {"type": "string"},
        "severity":           {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
        "summary":            {"type": "string"},
        "root_cause":         {"type": "string"},
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "event":     {"type": "string"},
                    "source":    {"type": "string"},
                },
                "required": ["timestamp", "event", "source"],
            },
        },
        "affected_services":  {"type": "array", "items": {"type": "string"}},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source":           {"type": "string"},
                    "doc_id":           {"type": "string"},
                    "excerpt":          {"type": "string"},
                    "relevance_score":  {"type": "number"},
                },
                "required": ["source", "doc_id", "excerpt", "relevance_score"],
            },
        },
        "recommended_fix":    {"type": "string"},
        "rollback_steps":     {"type": "array", "items": {"type": "string"}},
        "prevention":         {"type": "string"},
        "confidence":         {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
    },
    "required": [
        "incident_id", "severity", "summary", "root_cause", "timeline",
        "affected_services", "evidence", "recommended_fix", "rollback_steps",
        "prevention", "confidence",
    ],
}

_SYSTEM_PROMPT = """You are a Principal Site Reliability Engineer (SRE) with 15 years of experience in incident response and root cause analysis.

You receive evidence from 7 operational sources:
- CloudWatch: Application logs with timestamps, error codes, stack traces
- Jira: Incident tickets with comments and investigation notes  
- GitHub: Pull requests, code diffs, commit history
- Deployment: Deployment records with config changes, rollbacks
- Architecture: Service dependency maps, connection pool configs, SLOs
- Runbook: Step-by-step remediation procedures
- Monitoring: Alert definitions with thresholds and actual values

Your task: Produce a comprehensive, evidence-based incident report.

Rules:
1. Always cite specific evidence (log lines, commit SHAs, ticket IDs, alert names)
2. Build a precise chronological timeline with exact timestamps
3. Root cause must be specific and traceable — not "possible network issue"
4. Fix recommendations must be actionable with specific commands/configs
5. Rollback steps should be ordered and precise
6. Prevention must address the systemic gap, not just the symptom
7. Set confidence HIGH only if you have direct evidence (logs + code + deployment), MEDIUM if inferred from 2+ sources, LOW if speculative"""


class Generator:
    """Generates structured IncidentReport from reranked evidence using Gemini 2.5 Pro."""

    def __init__(self, client: genai.Client):
        self.client = client

    def generate(self, query: str, ranked_chunks: list[dict]) -> IncidentReport:
        context = self._build_context(ranked_chunks)
        user_prompt = self._build_prompt(query, ranked_chunks, context)

        response = self.client.interactions.create(
            model=LLM_MODEL,
            input=user_prompt,
            system_instruction=_SYSTEM_PROMPT,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": _REPORT_SCHEMA,
            },
        )

        data = json.loads(response.output_text)
        return IncidentReport(**data)

    def _build_context(self, chunks: list[dict]) -> str:
        """Format ranked chunks into numbered evidence blocks."""
        parts: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            score = chunk.get("reranker_score", 0)
            reason = chunk.get("reranker_reason", "")
            header = (
                f"[{i}] SOURCE={meta.get('source', '').upper()} "
                f"| ID={meta.get('doc_id', '')} "
                f"| RELEVANCE={score:.1f}/10",
            )
            if reason:
                header += f" | WHY={reason}"
            parts.append(f"{header}\n{chunk['text']}")
        return "\n\n{'─' * 60}\n\n".join(parts)

    def _build_prompt(
        self, query: str, chunks: list[dict], context: str
    ) -> str:
        sources_present = list({c["metadata"].get("source", "") for c in chunks})
        return (
            f"## Incident Investigation Request\n\n"
            f"**Query**: {query}\n\n"
            f"**Evidence Summary**: {len(chunks)} chunks from sources: "
            f"{', '.join(s.upper() for s in sources_present)}\n\n"
            f"{'═' * 60}\n\n"
            f"## Evidence\n\n"
            f"{context}\n\n"
            f"{'═' * 60}\n\n"
            f"Generate a complete, evidence-based incident report in the required JSON format."
        )

