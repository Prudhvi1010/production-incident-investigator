"""
app.py — Streamlit UI for the Production Incident Investigator RAG.

Run: streamlit run app.py
"""
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from config import ALL_SOURCES, SOURCE_ICONS, SOURCE_COLORS
from src.investigator import Investigator
from src.models.incident_report import IncidentReport

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Production Incident Investigator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .source-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 2px;
    color: white;
  }
  .severity-p1 { background: #DC3545; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; }
  .severity-p2 { background: #FD7E14; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; }
  .severity-p3 { background: #FFC107; color: black; padding: 4px 12px; border-radius: 4px; font-weight: bold; }
  .severity-p4 { background: #28A745; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; }
  .confidence-high { color: #28A745; font-weight: bold; }
  .confidence-medium { color: #FD7E14; font-weight: bold; }
  .confidence-low { color: #DC3545; font-weight: bold; }
  .evidence-card {
    background: #1E1E2E;
    border-left: 4px solid #6F42C1;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 6px 0;
    font-size: 0.85rem;
  }
  .timeline-item {
    border-left: 3px solid #0D6EFD;
    padding: 6px 12px;
    margin: 4px 0;
  }
  .metric-card {
    background: #262730;
    padding: 16px;
    border-radius: 8px;
    text-align: center;
  }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "investigator" not in st.session_state:
    st.session_state.investigator = None
if "report" not in st.session_state:
    st.session_state.report = None
if "pipeline_meta" not in st.session_state:
    st.session_state.pipeline_meta = None
if "api_key_set" not in st.session_state:
    st.session_state.api_key_set = False


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")

    # API Key
    st.subheader("🔑 Gemini API Key")
    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="AIza...",
        help="Get your key at ai.google.dev",
    )

    st.divider()

    # Source toggles
    st.subheader("📡 Data Sources")
    enabled_sources = []
    for source in ALL_SOURCES:
        icon = SOURCE_ICONS.get(source, "•")
        color = SOURCE_COLORS.get(source, "#888")
        checked = st.checkbox(
            f"{icon} {source.capitalize()}",
            value=True,
            key=f"src_{source}",
        )
        if checked:
            enabled_sources.append(source)

    st.divider()

    # Index management
    st.subheader("🗃️ Vector Store")

    col1, col2 = st.columns(2)
    with col1:
        ingest_btn = st.button("📥 Ingest All", use_container_width=True, type="primary")
    with col2:
        reset_btn = st.button("🗑️ Reset", use_container_width=True)

    # Show store stats
    if st.session_state.investigator:
        stats = st.session_state.investigator.store_stats()
        if stats["total_chunks"] > 0:
            st.caption(f"**{stats['total_chunks']}** chunks indexed")
            for src, cnt in stats["sources"].items():
                icon = SOURCE_ICONS.get(src, "•")
                st.caption(f"{icon} {src}: {cnt}")

    st.divider()
    st.caption("Built with Gemini 2.5 Pro + gemini-embedding-001 + ChromaDB")


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("🔍 Production Incident Investigator")
st.markdown(
    "Investigate production incidents using RAG across **CloudWatch logs**, **Jira tickets**, "
    "**GitHub PRs**, **deployments**, **architecture docs**, **runbooks**, and **monitoring alerts**."
)

# ── Initialize / Ingest ───────────────────────────────────────────────────────
if api_key and not st.session_state.api_key_set:
    try:
        st.session_state.investigator = Investigator(
            enabled_sources=enabled_sources or ALL_SOURCES,
            api_key=api_key,
        )
        st.session_state.api_key_set = True
    except Exception as e:
        st.error(f"Failed to initialize: {e}")

if ingest_btn:
    if not api_key:
        st.error("Please enter your Gemini API key first.")
    else:
        try:
            investigator = Investigator(enabled_sources=enabled_sources or ALL_SOURCES, api_key=api_key)
            st.session_state.investigator = investigator
            st.session_state.api_key_set = True

            with st.status("📥 Ingesting all sources into vector store...", expanded=True) as status:
                from src.ingestors import get_all_ingestors
                ingestors = get_all_ingestors()
                for ing in ingestors:
                    icon = SOURCE_ICONS.get(ing.source_name, "•")
                    st.write(f"{icon} Ingesting **{ing.source_name}**...")
                    investigator.ingest_source(ing, verbose=False)
                status.update(label="✅ Ingestion complete!", state="complete")

            st.success(f"✅ Indexed {investigator.store_stats()['total_chunks']} chunks across {len(ALL_SOURCES)} sources")
            st.rerun()
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

if reset_btn and st.session_state.investigator:
    st.session_state.investigator.vector_store.reset()
    st.success("Vector store reset.")
    st.rerun()

# ── Query input ───────────────────────────────────────────────────────────────
st.divider()

# Sample queries
st.markdown("**💡 Sample queries:**")
sample_queries = [
    "Payment service returning 500 errors after the 14:02 deployment — what happened?",
    "Why did the DB connection pool get exhausted on postgres-primary?",
    "What code change caused the payment outage and how do we fix it?",
    "Give me a complete timeline of the March 15 payment incident",
]
cols = st.columns(2)
selected_sample = None
for i, sq in enumerate(sample_queries):
    if cols[i % 2].button(sq, use_container_width=True, key=f"sample_{i}"):
        selected_sample = sq

query_input = st.text_area(
    "🔎 Describe the incident",
    value=selected_sample or "",
    placeholder="e.g. Payment service returning 500 errors after 2pm deployment — what is the root cause?",
    height=90,
)

investigate_btn = st.button(
    "🚀 Investigate Incident",
    type="primary",
    use_container_width=True,
    disabled=not (api_key and query_input.strip()),
)

# ── Investigation ─────────────────────────────────────────────────────────────
if investigate_btn and query_input.strip():
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not st.session_state.investigator:
        st.error("Please ingest sources first (click '📥 Ingest All' in the sidebar).")
    elif not st.session_state.investigator.is_indexed():
        st.warning("⚠️ Vector store is empty. Click '📥 Ingest All' in the sidebar first.")
    else:
        investigator = Investigator(enabled_sources=enabled_sources or ALL_SOURCES, api_key=api_key)

        with st.spinner("🔍 Retrieving evidence..."):
            candidates = investigator.retriever.retrieve(query_input)

        with st.spinner(f"📊 Reranking {len(candidates)} candidates with Gemini Flash..."):
            ranked = investigator.reranker.rerank(query_input, candidates)

        with st.spinner("🤖 Generating incident report with Gemini 2.5 Pro..."):
            report = investigator.generator.generate(query_input, ranked)

        st.session_state.report = report
        st.session_state.pipeline_meta = {
            "candidates_count": len(candidates),
            "ranked_count": len(ranked),
            "sources_in_context": list({c["metadata"].get("source", "") for c in ranked}),
        }

# ── Report display ────────────────────────────────────────────────────────────
if st.session_state.report:
    report: IncidentReport = st.session_state.report
    meta = st.session_state.pipeline_meta or {}

    st.divider()
    st.subheader("📋 Incident Report")

    # Header metrics
    sev_colors = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}
    conf_colors = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❓"}

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Incident", report.incident_id)
    m2.metric("Severity", f"{sev_colors.get(report.severity, '')} {report.severity}")
    m3.metric("Confidence", f"{conf_colors.get(report.confidence, '')} {report.confidence}")
    m4.metric("Candidates", meta.get("candidates_count", "?"))
    m5.metric("After Rerank", meta.get("ranked_count", "?"))

    # Tabs
    tab_summary, tab_timeline, tab_evidence, tab_fix, tab_raw = st.tabs([
        "📋 Summary & Root Cause",
        "⏱️ Timeline",
        "🔎 Evidence",
        "🛠️ Fix & Prevention",
        "📄 Raw JSON",
    ])

    with tab_summary:
        st.markdown("### Summary")
        st.info(report.summary)

        st.markdown("### 🔍 Root Cause")
        st.error(report.root_cause)

        st.markdown("### 🏗️ Affected Services")
        for svc in report.affected_services:
            st.markdown(f"- `{svc}`")

    with tab_timeline:
        st.markdown("### ⏱️ Incident Timeline")
        if report.timeline:
            for event in report.timeline:
                icon = SOURCE_ICONS.get(event.source.lower(), "•")
                color = SOURCE_COLORS.get(event.source.lower(), "#6F42C1")
                with st.container():
                    col_time, col_event = st.columns([1, 3])
                    col_time.markdown(f"**`{event.timestamp}`**")
                    col_event.markdown(
                        f"<span class='source-badge' style='background:{color}'>{icon} {event.source.upper()}</span> {event.event}",
                        unsafe_allow_html=True,
                    )
        else:
            st.write("No timeline events found.")

    with tab_evidence:
        st.markdown(f"### 🔎 Evidence ({len(report.evidence)} items)")
        sources_present = list({e.source for e in report.evidence})
        source_filter = st.multiselect(
            "Filter by source",
            options=sources_present,
            default=sources_present,
            key="evidence_filter",
        )
        for ev in report.evidence:
            if ev.source not in source_filter:
                continue
            color = SOURCE_COLORS.get(ev.source.lower(), "#6F42C1")
            icon = SOURCE_ICONS.get(ev.source.lower(), "•")
            with st.expander(
                f"{icon} [{ev.source.upper()}] {ev.doc_id} — Score: {ev.relevance_score:.1f}/10",
                expanded=ev.relevance_score >= 8,
            ):
                st.markdown(
                    f"<span class='source-badge' style='background:{color}'>{ev.source.upper()}</span>",
                    unsafe_allow_html=True,
                )
                st.code(ev.excerpt, language=None)

    with tab_fix:
        col_fix, col_prev = st.columns(2)
        with col_fix:
            st.markdown("### 🛠️ Recommended Fix")
            st.success(report.recommended_fix)

            st.markdown("### 🔄 Rollback Steps")
            for i, step in enumerate(report.rollback_steps, 1):
                st.markdown(f"**{i}.** {step}")

        with col_prev:
            st.markdown("### 🛡️ Prevention")
            st.warning(report.prevention)

    with tab_raw:
        st.markdown("### Raw JSON Report")
        st.json(json.loads(report.model_dump_json()))

        # Download button
        st.download_button(
            label="⬇️ Download Report JSON",
            data=report.model_dump_json(indent=2),
            file_name=f"incident_report_{report.incident_id}.json",
            mime="application/json",
        )

elif not api_key:
    st.info("👈 Enter your Gemini API key in the sidebar to get started.")
elif not (st.session_state.investigator and st.session_state.investigator.is_indexed()):
    st.info("👈 Click **📥 Ingest All** in the sidebar to index all 7 data sources, then enter your incident query.")

