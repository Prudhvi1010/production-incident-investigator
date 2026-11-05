# 🔍 Production Incident Investigator RAG

A multi-source RAG system for automated production incident investigation. Ingests **7 operational data sources**, retrieves relevant evidence, reranks with Gemini Flash, and generates structured incident reports with Root Cause, Timeline, Evidence, and Fix by **Gemini 2.5 Pro**.

---

## Pipeline

```
CloudWatch Logs ─┐
GitHub PRs        ├──► Retriever ──► Reranker ──► LLM (Gemini 2.5 Pro)
Jira Tickets      │  (Embedding)   (Gemini Flash)         │
Runbooks          │                                        ▼
Deployment Hist. ─┘                              ┌──────────────────┐
Architecture Docs                                │  Incident Report  │
Monitoring Alerts                                │  ─ Root Cause     │
                                                 │  ─ Timeline       │
                                                 │  ─ Evidence       │
                                                 │  ─ Fix            │
                                                 └──────────────────┘
```

## Tech Stack

| Component    | Technology                          |
|-------------|-------------------------------------|
| Embeddings  | `gemini-embedding-001`              |
| Reranker    | `gemini-3.7-flash` (LLM scoring)    |
| Generation  | `gemini-2.5-pro` (structured JSON)  |
| Vector Store| ChromaDB (local persistent)         |
| UI          | Streamlit                           |
| CLI         | Typer + Rich                        |
| Validation  | Pydantic v2                         |

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
```bash
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here
```

### 3. Ingest all sources
```bash
python main.py ingest
```

### 4. Investigate an incident (CLI)
```bash
python main.py query "Payment service 500 errors after the 2pm deployment — what is the root cause?"
```

### 5. Launch the Streamlit UI
```bash
streamlit run app.py
```

---

## CLI Commands

```bash
# Ingest all 7 sources into ChromaDB
python main.py ingest

# Re-index from scratch (wipe + re-ingest)
python main.py ingest --reset

# Investigate an incident
python main.py query "describe your incident here"

# Output raw JSON report
python main.py query "incident description" --json

# Save report to file
python main.py query "incident description" --save report.json

# Use specific sources only
python main.py query "incident" --sources cloudwatch,jira,github

# Show vector store statistics
python main.py stats
```

---

## Project Structure

```
production-incident-investigator/
├── config.py                    # Models, paths, thresholds, source names
├── main.py                      # CLI (Typer + Rich)
├── app.py                       # Streamlit UI
├── requirements.txt
├── .env.example
│
├── data/mock/                   # Realistic mock data (payment outage scenario)
│   ├── cloudwatch_logs.json
│   ├── jira_incidents.json
│   ├── github_prs.json
│   ├── deployment_history.json
│   ├── architecture_docs.json
│   ├── runbooks.json
│   └── monitoring_alerts.json
│
└── src/
    ├── models/
    │   ├── document.py          # SourceDocument dataclass
    │   └── incident_report.py   # IncidentReport Pydantic model
    ├── ingestors/
    │   ├── base.py              # BaseIngestor ABC
    │   ├── cloudwatch.py        # Log event + sliding window chunks
    │   ├── jira.py              # Ticket + per-comment chunks
    │   ├── github.py            # PR overview + diff + commit chunks
    │   ├── deployment.py        # Deployment records with config diffs
    │   ├── architecture.py      # Service + dependency + SLO chunks
    │   ├── runbook.py           # Runbook header + per-step chunks
    │   └── monitoring.py        # Alert + dashboard chunks
    ├── pipeline/
    │   ├── embedder.py          # gemini-embedding-001 with caching
    │   ├── vector_store.py      # ChromaDB persistent store
    │   ├── retriever.py         # Multi-source hybrid retrieval
    │   ├── reranker.py          # Gemini Flash LLM reranker
    │   └── generator.py         # Gemini 2.5 Pro structured output
    └── investigator.py          # Orchestrator (ingest + investigate)
```

---

## Mock Data Scenario

All mock data simulates a **realistic payment service outage**:

| Source | Content |
|--------|---------|
| CloudWatch | HikariCP pool exhaustion, 5xx errors, connection timeout logs |
| Jira | P1 incident INC-20240315-001, investigation comments |
| GitHub | PR #1847 changing `minimumIdle=0`, `maximumPoolSize=50` |
| Deployment | v2.4.2 deploy at 14:02 UTC, rollback at 14:15 |
| Architecture | postgres-primary max_connections=100, shared with 3 consumers |
| Runbook | RB-PAY-001 with exact rollback commands |
| Monitoring | 5 firing alerts: error rate 94.2%, p99 30s, pool exhausted |

---

## Incident Report Output

```json
{
  "incident_id": "INC-20240315-001",
  "severity": "P1",
  "confidence": "HIGH",
  "summary": "Payment service outage caused by DB connection pool exhaustion...",
  "root_cause": "PR #1847 set minimumIdle=0 on HikariCP pool (size 50)...",
  "timeline": [
    {"timestamp": "14:02 UTC", "event": "payment-service v2.4.2 deployed", "source": "deployment"},
    {"timestamp": "14:03 UTC", "event": "HikariCP pool exhausted (50/50)", "source": "cloudwatch"},
    ...
  ],
  "affected_services": ["payment-service", "postgres-primary"],
  "recommended_fix": "Revert minimumIdle to 10, reduce maximumPoolSize to 30...",
  "rollback_steps": ["Trigger rollback pipeline...", "Monitor connections..."],
  "prevention": "Add connection pool capacity planning to deploy checklist..."
}
```

---

## Connecting Real Sources

Each ingestor in `src/ingestors/` has a clear `ingest()` method. To connect real APIs:

- **CloudWatch** → replace `_load_json` with `boto3.client('logs').filter_log_events()`
- **Jira** → use `jira` Python library: `JIRA(server=url).search_issues(...)`
- **GitHub** → use `PyGithub`: `Github(token).get_repo(...).get_pulls()`
- **Deployment** → query your CI/CD system (Jenkins, GitHub Actions, ArgoCD)
- **Architecture** → load from Confluence, Backstage, or internal wiki API
- **Runbooks** → parse from Confluence pages or PagerDuty runbooks
- **Monitoring** → use boto3 CloudWatch Alarms or Datadog API

