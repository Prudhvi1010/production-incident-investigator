"""
src/pipeline/reranker.py — Gemini-powered LLM reranker.

Sends each retrieved chunk to gemini-3.7-flash and asks it to score
relevance on a 0–10 scale relative to the incident query. Chunks below
RERANKER_THRESHOLD are filtered out. Survivors are sorted descending by score.
"""
import json
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google import genai
from config import RERANKER_MODEL, RERANKER_THRESHOLD, TOP_K_FINAL


_SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "number",
            "description": "Relevance score from 0 (irrelevant) to 10 (critical evidence)",
        },
        "reason": {
            "type": "string",
            "description": "One-sentence explanation for the score",
        },
    },
    "required": ["score", "reason"],
}

_SYSTEM_PROMPT = (
    "You are an expert SRE triaging a production incident. "
    "Score the relevance of the provided document chunk to the incident query. "
    "A score of 10 means the chunk is direct evidence (e.g. exact error log, root-cause commit, active alert). "
    "A score of 0 means completely unrelated. "
    "Return ONLY valid JSON."
)


class Reranker:
    """
    LLM-based reranker using gemini-3.7-flash.

    For each candidate chunk:
    - Prompts the model for a JSON score + reason
    - Filters chunks below RERANKER_THRESHOLD
    - Returns top TOP_K_FINAL chunks sorted by score descending
    """

    def __init__(self, client: genai.Client, inter_call_delay: float = 0.1):
        self.client = client
        self.delay = inter_call_delay

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """Score all candidates and return the highest-scoring ones."""
        scored: list[dict] = []
        for candidate in candidates:
            score, reason = self._score(query, candidate)
            if score >= RERANKER_THRESHOLD:
                candidate = {**candidate, "reranker_score": score, "reranker_reason": reason}
                scored.append(candidate)
            if self.delay > 0:
                time.sleep(self.delay)

        scored.sort(key=lambda x: x["reranker_score"], reverse=True)
        return scored[:TOP_K_FINAL]

    def _score(self, query: str, candidate: dict) -> tuple[float, str]:
        meta = candidate.get("metadata", {})
        source = meta.get("source", "unknown").upper()
        doc_id = meta.get("doc_id", "")
        text = candidate["text"]

        user_prompt = (
            f"## Incident Query\n{query}\n\n"
            f"## Document Chunk\n"
            f"Source: {source} | ID: {doc_id}\n\n"
            f"{text[:1500]}"  # truncate very long chunks
        )

        try:
            response = self.client.interactions.create(
                model=RERANKER_MODEL,
                input=user_prompt,
                system_instruction=_SYSTEM_PROMPT,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": _SCORE_SCHEMA,
                },
            )
            data = json.loads(response.output_text)
            return float(data.get("score", 0.0)), str(data.get("reason", ""))
        except Exception as e:
            return 0.0, f"scoring error: {e}"

