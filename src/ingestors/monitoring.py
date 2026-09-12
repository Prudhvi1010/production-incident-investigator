"""
src/ingestors/monitoring.py — Ingestor for monitoring alerts.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class MonitoringIngestor(BaseIngestor):
    """
    Ingests monitoring alerts from alerting systems (CloudWatch Alarms,
    Datadog, PagerDuty, etc.).
    Each alert becomes one chunk.
    """

    source_name = Source.MONITORING

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "monitoring_alerts.json")
        docs: list[SourceDocument] = []

        for alert in data.get("alerts", []):
            alert_id = alert.get("id", "unknown")
            text = self._alert_to_text(alert)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=alert_id,
                    text=text,
                    metadata={
                        "alert_id": alert_id,
                        "name": alert.get("name", ""),
                        "service": alert.get("service", ""),
                        "severity": alert.get("severity", ""),
                        "status": alert.get("status", ""),
                        "started_at": alert.get("started_at", ""),
                        "resolved_at": alert.get("resolved_at", ""),
                        "metric": alert.get("metric", ""),
                    },
                    chunk_index=0,
                )
            )

        # Dashboard context chunk
        for dash in data.get("dashboards", []):
            dash_text = (
                f"[Monitoring Dashboard | {dash.get('name', '')}]\n"
                f"URL: {dash.get('url', '')}\n"
                f"Tracked Metrics: {', '.join(dash.get('metrics', []))}"
            )
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=f"dashboard-{dash.get('name', '').replace(' ', '-').lower()}",
                    text=dash_text,
                    metadata={"type": "dashboard", "name": dash.get("name", "")},
                    chunk_index=0,
                )
            )

        return docs

    def _alert_to_text(self, alert: dict) -> str:
        status_emoji = "🔴" if alert.get("status") == "FIRING" else "✅"
        sev_emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}.get(
            alert.get("severity", ""), ""
        )
        lines = [
            f"[Monitoring Alert | {alert.get('id', '')}] {status_emoji} {sev_emoji}",
            f"Name: {alert.get('name', '')}",
            f"Service: {alert.get('service', '')} | Metric: {alert.get('metric', '')}",
            f"Severity: {alert.get('severity', '')} | Status: {alert.get('status', '')}",
            f"Threshold: {alert.get('threshold', '')} | Actual: {alert.get('actual_value', '')}",
            f"Fired at: {alert.get('started_at', '')}",
        ]
        if alert.get("resolved_at"):
            lines.append(f"Resolved at: {alert['resolved_at']}")
        if alert.get("pagerduty_incident"):
            lines.append(f"PagerDuty: {alert['pagerduty_incident']}")
        lines += ["", f"Description: {alert.get('description', '')}"]
        return "\n".join(lines)

