"""
src/ingestors/__init__.py — Ingestor registry.
"""
from .base import BaseIngestor
from .cloudwatch import CloudWatchIngestor
from .jira import JiraIngestor
from .github import GitHubIngestor
from .deployment import DeploymentIngestor
from .architecture import ArchitectureIngestor
from .runbook import RunbookIngestor
from .monitoring import MonitoringIngestor


def get_all_ingestors() -> list[BaseIngestor]:
    """Return one instance of every registered ingestor."""
    return [
        CloudWatchIngestor(),
        JiraIngestor(),
        GitHubIngestor(),
        DeploymentIngestor(),
        ArchitectureIngestor(),
        RunbookIngestor(),
        MonitoringIngestor(),
    ]


__all__ = [
    "BaseIngestor",
    "CloudWatchIngestor",
    "JiraIngestor",
    "GitHubIngestor",
    "DeploymentIngestor",
    "ArchitectureIngestor",
    "RunbookIngestor",
    "MonitoringIngestor",
    "get_all_ingestors",
]

