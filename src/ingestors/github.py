"""
src/ingestors/github.py — Ingestor for GitHub PRs and commits.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class GitHubIngestor(BaseIngestor):
    """
    Ingests GitHub pull requests and commits.
    Creates chunks for: PR overview, PR diff/files, PR commits, standalone commits.
    """

    source_name = Source.GITHUB

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "github_prs.json")
        docs: list[SourceDocument] = []

        # Pull requests
        for pr in data.get("pull_requests", []):
            pr_id = f"PR-{pr['number']}"

            # PR overview chunk
            overview = self._pr_overview(pr)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=pr_id,
                    text=overview,
                    metadata={
                        "pr_number": pr["number"],
                        "title": pr.get("title", ""),
                        "author": pr.get("author", ""),
                        "state": pr.get("state", ""),
                        "merged_at": pr.get("merged_at", ""),
                        "jira_ticket": pr.get("jira_ticket", ""),
                    },
                    chunk_index=0,
                )
            )

            # Files changed / diff chunk
            files_changed = pr.get("files_changed", [])
            if files_changed:
                diff_lines = [f"[GitHub PR #{pr['number']} — Files Changed]"]
                for fc in files_changed:
                    diff_lines.append(
                        f"File: {fc['filename']} (+{fc['additions']} -{fc['deletions']})"
                    )
                    if fc.get("diff"):
                        diff_lines.append(f"Diff:\n{fc['diff']}")
                docs.append(
                    SourceDocument(
                        source=self.source_name,
                        doc_id=pr_id,
                        text="\n".join(diff_lines),
                        metadata={
                            "pr_number": pr["number"],
                            "type": "diff",
                            "files": [f["filename"] for f in files_changed],
                        },
                        chunk_index=1,
                    )
                )

            # Commits chunk
            commits = pr.get("commits", [])
            if commits:
                commit_lines = [f"[GitHub PR #{pr['number']} — Commits]"]
                for c in commits:
                    commit_lines.append(
                        f"{c['sha'][:8]} | {c['timestamp']} | {c['author']}: {c['message']}"
                    )
                docs.append(
                    SourceDocument(
                        source=self.source_name,
                        doc_id=pr_id,
                        text="\n".join(commit_lines),
                        metadata={
                            "pr_number": pr["number"],
                            "type": "commits",
                            "commit_count": len(commits),
                        },
                        chunk_index=2,
                    )
                )

        # Standalone commits
        for commit in data.get("commits", []):
            sha = commit["sha"][:8]
            text = (
                f"[GitHub Commit | {sha}]\n"
                f"SHA: {commit['sha']}\n"
                f"Message: {commit['message']}\n"
                f"Author: {commit['author']} | Timestamp: {commit['timestamp']}\n"
                f"Branch: {commit.get('branch', 'unknown')}"
            )
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=f"commit-{sha}",
                    text=text,
                    metadata={
                        "sha": commit["sha"],
                        "author": commit["author"],
                        "timestamp": commit["timestamp"],
                        "branch": commit.get("branch", ""),
                    },
                    chunk_index=0,
                )
            )

        return docs

    def _pr_overview(self, pr: dict) -> str:
        return (
            f"[GitHub Pull Request #{pr['number']}]\n"
            f"Title: {pr['title']}\n"
            f"Author: {pr.get('author', '')} | Reviewer: {pr.get('reviewer', '')}\n"
            f"State: {pr.get('state', '')} | Branch: {pr.get('head_branch', '')} → {pr.get('base_branch', '')}\n"
            f"Created: {pr.get('created_at', '')} | Merged: {pr.get('merged_at', '')}\n"
            f"Labels: {', '.join(pr.get('labels', []))}\n"
            f"Linked Jira: {pr.get('jira_ticket', 'N/A')}\n\n"
            f"Description:\n{pr.get('body', '')}"
        )

