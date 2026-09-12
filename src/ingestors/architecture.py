"""
src/ingestors/architecture.py — Ingestor for architecture & service dependency docs.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, Source
from src.models.document import SourceDocument
from src.ingestors.base import BaseIngestor


class ArchitectureIngestor(BaseIngestor):
    """
    Ingests architecture documents.
    Creates per-service chunks with dependency, SLO, and config details.
    """

    source_name = Source.ARCHITECTURE

    def ingest(self) -> list[SourceDocument]:
        data = self._load_json(DATA_DIR / "architecture_docs.json")
        docs: list[SourceDocument] = []

        for svc in data.get("services", []):
            svc_name = svc.get("name", "unknown")

            # Service overview chunk
            overview = self._service_to_text(svc)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id=f"service-{svc_name}",
                    text=overview,
                    metadata={
                        "service": svc_name,
                        "tier": svc.get("tier", ""),
                        "owner": svc.get("owner", ""),
                        "type": "service_overview",
                    },
                    chunk_index=0,
                )
            )

            # Per-dependency chunks (especially useful for DB connection analysis)
            for di, dep in enumerate(svc.get("dependencies", [])):
                if not isinstance(dep, dict):
                    continue  # skip plain-string dependency references
                dep_text = (
                    f"[Architecture | {svc_name} → {dep.get('service', '')}]\n"
                    f"Dependency: {svc_name} depends on {dep.get('service', '')}\n"
                    f"Type: {dep.get('type', '')} | Criticality: {dep.get('criticality', '')}\n"
                    f"Description: {dep.get('description', '')}\n"
                )
                if dep.get("connection_pool"):
                    pool = dep["connection_pool"]
                    dep_text += (
                        f"Connection Pool ({pool.get('library', '')}):\n"
                        f"  max_size={pool.get('default_max_size')}\n"
                        f"  min_idle={pool.get('default_min_idle')}\n"
                        f"  connection_timeout_ms={pool.get('connection_timeout_ms')}\n"
                        f"  max_lifetime_ms={pool.get('max_lifetime_ms')}\n"
                    )
                if dep.get("timeout_ms"):
                    dep_text += f"Timeout: {dep['timeout_ms']}ms\n"
                docs.append(
                    SourceDocument(
                        source=self.source_name,
                        doc_id=f"service-{svc_name}",
                        text=dep_text,
                        metadata={
                            "service": svc_name,
                            "dependency": dep.get("service", ""),
                            "dep_type": dep.get("type", ""),
                            "criticality": dep.get("criticality", ""),
                            "type": "dependency",
                        },
                        chunk_index=di + 1,
                    )
                )

        # Infrastructure chunk
        infra = data.get("infrastructure", {})
        if infra:
            infra_text = "[Architecture | Infrastructure Overview]\n" + self._dict_to_text(infra)
            docs.append(
                SourceDocument(
                    source=self.source_name,
                    doc_id="infrastructure",
                    text=infra_text,
                    metadata={"type": "infrastructure"},
                    chunk_index=0,
                )
            )

        return docs

    def _service_to_text(self, svc: dict) -> str:
        deps = svc.get("dependencies", [])
        dep_names = [
            d.get("service", "") if isinstance(d, dict) else str(d)
            for d in deps
        ]
        slo = svc.get("slo", {})
        scaling = svc.get("scaling", {})
        lines = [
            f"[Architecture | Service: {svc.get('name', '')}]",
            f"Description: {svc.get('description', '')}",
            f"Owner: {svc.get('owner', '')} | Tier: {svc.get('tier', '')}",
            f"Language: {svc.get('language', '')} | Framework: {svc.get('framework', '')}",
            f"Deployment: {svc.get('deployment', '')}",
            f"Repository: {svc.get('repository', '')}",
            f"Endpoints: {', '.join(svc.get('endpoints', []))}",
            f"Dependencies: {', '.join(dep_names)}",
        ]
        if slo:
            lines.append(
                f"SLO: availability={slo.get('availability')}, "
                f"p99_latency={slo.get('p99_latency_ms')}ms, "
                f"error_rate<{slo.get('error_rate_pct')}%"
            )
        if scaling:
            lines.append(
                f"Scaling: min={scaling.get('min_instances')}, "
                f"max={scaling.get('max_instances')}, "
                f"target_cpu={scaling.get('target_cpu_pct')}%"
            )
        if svc.get("note"):
            lines.append(f"\n⚠️  Note: {svc['note']}")
        return "\n".join(lines)
