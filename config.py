"""
config.py — Central configuration for the Production Incident Investigator RAG.
"""
from pathlib import Path

# ── Directory layout ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "mock"
CHROMA_PERSIST_DIR = BASE_DIR / ".chroma_db"

# ── Gemini models ─────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "gemini-embedding-001"   # text embeddings
LLM_MODEL = "gemini-3.1-pro-preview"      # root-cause generation (deep reasoning)
RERANKER_MODEL = "gemini-3.7-flash"       # fast relevance scoring

# ── Retrieval settings ────────────────────────────────────────────────────────
TOP_K_PER_SOURCE = 6      # chunks fetched from ChromaDB per source
TOP_K_OVERSAMPLE = 40     # total candidates passed to reranker
TOP_K_FINAL = 20          # top-N chunks kept after reranking for the LLM
RERANKER_THRESHOLD = 4.0  # minimum score (0-10) to include a chunk
EMBED_BATCH_DELAY = 0.05  # seconds between embedding calls (rate-limit guard)

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_COLLECTION = "incident_investigator"
CHROMA_DISTANCE = "cosine"

# ── Sources ───────────────────────────────────────────────────────────────────
class Source:
    CLOUDWATCH   = "cloudwatch"
    JIRA         = "jira"
    GITHUB       = "github"
    DEPLOYMENT   = "deployment"
    ARCHITECTURE = "architecture"
    RUNBOOK      = "runbook"
    MONITORING   = "monitoring"

ALL_SOURCES: list[str] = [
    Source.CLOUDWATCH,
    Source.JIRA,
    Source.GITHUB,
    Source.DEPLOYMENT,
    Source.ARCHITECTURE,
    Source.RUNBOOK,
    Source.MONITORING,
]

SOURCE_ICONS: dict[str, str] = {
    Source.CLOUDWATCH:    "☁️",
    Source.JIRA:          "🎫",
    Source.GITHUB:        "🐙",
    Source.DEPLOYMENT:    "🚀",
    Source.ARCHITECTURE:  "🏗️",
    Source.RUNBOOK:       "📖",
    Source.MONITORING:    "📊",
}

SOURCE_COLORS: dict[str, str] = {
    Source.CLOUDWATCH:    "#FF9900",
    Source.JIRA:          "#0052CC",
    Source.GITHUB:        "#24292E",
    Source.DEPLOYMENT:    "#6F42C1",
    Source.ARCHITECTURE:  "#28A745",
    Source.RUNBOOK:       "#FD7E14",
    Source.MONITORING:    "#DC3545",
}

