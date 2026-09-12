"""
src/ingestors/deployment.py — Ingestor for deployment history records.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class DeploymentIngestor(BaseIngestor):
    """
    Ingests deployment history events.
    Each deployment becomes a richly-described text chunk.
    Config changes are highlighted as they are often root causes.
    """

    source_name = Source.DEPLOYMENT

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "deployment_history.json")
        deployments: list[dict] = data.get("deployments", [])
        docs: list[SourceDocument] = []

        for deploy in deployments:
            deploy_id = deploy.get("id", "unknown")
            text = self._deploy_to_text(deploy)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=deploy_id,
                    text=text,
                    metadata={
                        "deploy_id": deploy_id,
                        "service": deploy.get("service", ""),
                        "version": deploy.get("version", ""),
                        "previous_version": deploy.get("previous_version", ""),
                        "status": deploy.get("status", ""),
                        "environment": deploy.get("environment", ""),
                        "started_at": deploy.get("started_at", ""),
                        "initiated_by": deploy.get("initiated_by", ""),
                        "has_config_changes": bool(deploy.get("config_changes")),
                    },
                    chunk_index=0,
                )
            )

        return docs

    def _deploy_to_text(self, deploy: dict) -> str:
        lines = [
            f"[Deployment | {deploy.get('id', '')}]",
            f"Service: {deploy.get('service', '')} | Version: {deploy.get('previous_version', 'N/A')} → {deploy.get('version', '')}",
            f"Environment: {deploy.get('environment', '')} | Region: {deploy.get('region', '')}",
            f"Status: {deploy.get('status', '').upper()}",
            f"Initiated by: {deploy.get('initiated_by', '')} | Approved by: {deploy.get('approved_by', '')}",
            f"Started: {deploy.get('started_at', '')} | Completed: {deploy.get('completed_at', '')}",
            f"Strategy: {deploy.get('strategy', '')}",
        ]

        if deploy.get("rollback_at"):
            lines.append(
                f"ROLLED BACK at: {deploy['rollback_at']} | Completed: {deploy.get('rollback_completed_at', '')}"
            )

        artifacts = deploy.get("artifacts", {})
        if artifacts:
            lines.append(
                f"Artifact: {artifacts.get('image', '')} | "
                f"Commit: {artifacts.get('commit_sha', '')[:8] if artifacts.get('commit_sha') else ''} | "
                f"PR: #{artifacts.get('pull_request', 'N/A')}"
            )

        config_changes = deploy.get("config_changes", {})
        if config_changes:
            lines.append("\n⚠️  CONFIG CHANGES IN THIS DEPLOYMENT:")
            for key, change in config_changes.items():
                lines.append(f"  {key}: {change.get('old', '?')} → {change.get('new', '?')}")

        if deploy.get("notes"):
            lines.append(f"\nNotes: {deploy['notes']}")

        return "\n".join(lines)

