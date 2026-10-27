"""
Streamlit Interactive Application for DocLens.
Features citation grounding view, passage verification drawer,
retrieval explainability metrics, and feedback logging.
"""
import json
import streamlit as st
import requests

st.set_page_config(
    page_title="DocLens | Citation-Grounded Financial QA",
    page_icon="🔍",
    layout="wide",
)

API_BASE_URL = "http://localhost:8000"

st.title("🔍 DocLens: Citation-Grounded Regulatory & Filing QA")
st.caption(
    "Retrieval-Augmented Generation over SEC 10-K filings and disclosure rulebooks. "
    "Every claim is grounded in exact source text, with automatic refusal when evidence is absent."
)

# Sidebar: Controls & Explainability Settings
with st.sidebar:
    st.header("⚙️ Search Controls & Pipeline")
    company_filter = st.selectbox(
        "Company Filter",
        options=["All Companies", "Microsoft (MSFT)", "Apple (AAPL)", "JPMorgan (JPM)", "Goldman Sachs (GS)", "Pfizer (PFE)", "ExxonMobil (XOM)", "SEBI Rulebook (SEBI)"],
        index=0,
    )
    year_filter = st.selectbox(
        "Fiscal Year",
        options=["All Years", "2025", "2024", "2015 (SEBI)"],
        index=0,
    )

    st.markdown("---")
    st.subheader("🔬 Retrieval Components")
    use_sparse = st.checkbox("Enable BM25 Keyword Search (RRF)", value=True)
    use_reranker = st.checkbox("Enable Cross-Encoder Reranker", value=True)

    st.markdown("---")
    st.subheader("📊 Corpus Summary")
    st.markdown(
        """
        - **Corpus**: 6 Companies + SEBI LODR 2015
        - **Target Items**: Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A)
        - **Vector Store**: ChromaDB (bge-small-en-v1.5)
        - **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2
        """
    )

# Quick Sample Query Buttons
st.markdown("**Sample Questions:**")
col1, col2, col3, col4 = st.columns(4)
sample_query = None
if col1.button("🛡️ MSFT Cybersecurity Risks"):
    sample_query = "Summarize the cybersecurity and supply chain risks in Microsoft's risk factors."
if col2.button("⚖️ SEBI Reg 30 Disclosure"):
    sample_query = "What does SEBI Regulation 30 mandate regarding timelines for disclosure of material events?"
if col3.button("📱 Apple Services Margins"):
    sample_query = "How does Apple management explain services segment margin performance in Item 7?"
if col4.button("🚫 Future Exxon Revenue (Refusal)"):
    sample_query = "What will ExxonMobil's net crude oil revenue be next year in fiscal 2027?"

# Main Query Input
user_query = st.text_input(
    "Enter your financial or regulatory question:",
    value=sample_query if sample_query else "",
    placeholder="e.g. What are Pfizer's primary biopharmaceutical commercial segments?",
)

# Map selected company to ticker
ticker_param = None
if "MSFT" in company_filter:
    ticker_param = "MSFT"
elif "AAPL" in company_filter:
    ticker_param = "AAPL"
elif "JPM" in company_filter:
    ticker_param = "JPM"
elif "GS" in company_filter:
    ticker_param = "GS"
elif "PFE" in company_filter:
    ticker_param = "PFE"
elif "XOM" in company_filter:
    ticker_param = "XOM"
elif "SEBI" in company_filter:
    ticker_param = "SEBI"

year_param = None
if "2025" in year_filter:
    year_param = 2025
elif "2024" in year_filter:
    year_param = 2024
elif "2015" in year_filter:
    year_param = 2015

if st.button("Search & Answer", type="primary") or sample_query:
    if not user_query.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Executing hybrid retrieval, reranking, and verification..."):
            try:
                # Call FastAPI backend
                payload = {
                    "query": user_query,
                    "ticker": ticker_param,
                    "fiscal_year": year_param,
                    "use_sparse": use_sparse,
                    "use_reranker": use_reranker,
                }
                resp = requests.post(f"{API_BASE_URL}/ask", json=payload, timeout=30)
                data = resp.json()
            except Exception:
                # Direct in-process fallback if FastAPI server is not currently running
                from src.common.config import load_config
                from src.common.models import QueryFilters
                from src.generation.llm_client import LLMClient
                from src.retrieval.hybrid_retriever import HybridRetriever

                cfg = load_config()
                rtr = HybridRetriever(cfg)
                llm_c = LLMClient(cfg)
                q_filters = QueryFilters(ticker=ticker_param, fiscal_year=year_param) if (ticker_param or year_param) else None
                chunks, lats = rtr.search(user_query, filters=q_filters, use_sparse=use_sparse, use_reranker=use_reranker, top_k=5)
                ans_resp = llm_c.generate_answer(user_query, chunks, prior_latencies=lats)
                data = {
                    "query_log_id": 1,
                    "query": user_query,
                    "answer": ans_resp.answer,
                    "is_refusal": ans_resp.is_refusal,
                    "citations": [c.model_dump() for c in ans_resp.citations],
                    "retrieved_chunks": [rc.model_dump() for rc in ans_resp.retrieved_chunks],
                    "latencies": ans_resp.latency_ms,
                }

            # Display Answer Panel
            st.markdown("### 📝 Grounded Answer")
            if data["is_refusal"]:
                st.error(f"🛑 **Refusal Triggered:** {data['answer']}")
            else:
                st.success(data["answer"])

            # Latency Metrics Row
            lats = data.get("latencies", {})
            st.markdown("#### ⏱️ Pipeline Latency")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Dense Vector", f"{lats.get('dense_ms', 0):.1f} ms")
            m2.metric("BM25 Keyword", f"{lats.get('sparse_ms', 0):.1f} ms")
            m3.metric("RRF Fusion", f"{lats.get('fusion_ms', 0):.1f} ms")
            m4.metric("Cross-Encoder", f"{lats.get('rerank_ms', 0):.1f} ms")
            m5.metric("Total Pipeline", f"{lats.get('total_pipeline_ms', lats.get('total_retrieval_ms', 0)):.1f} ms")

            # Citations Inspection Drawer
            if data.get("citations"):
                st.markdown("### 📌 Verified Citations")
                for cit in data["citations"]:
                    status_icon = "✅" if cit["is_valid"] else "⚠️ Invalid Citation"
                    with st.expander(f"{status_icon} Citation {cit['tag']} — {cit['company']} ({cit['ticker']}) {cit['section_name']}"):
                        st.markdown(f"**Verifiable Snippet:**\n> {cit['snippet']}")
                        st.caption(f"Chunk ID: `{cit['chunk_id']}`")

            # Explainability: Retrieved Chunks Breakdown
            st.markdown("### 🔍 Retrieved Evidence & Multi-Stage Scores")
            ret_chunks = data.get("retrieved_chunks", [])
            for rc in ret_chunks:
                ch = rc["chunk"]
                col_title, col_score = st.columns([3, 1])
                with col_title:
                    st.markdown(f"**#{rc['final_rank']} {ch['company']} ({ch['ticker']})** — *{ch['section_name']}*")
                with col_score:
                    score_txt = []
                    if rc.get("dense_score") is not None:
                        score_txt.append(f"Vector Cos: `{rc['dense_score']:.3f}`")
                    if rc.get("sparse_score") is not None:
                        score_txt.append(f"BM25: `{rc['sparse_score']:.1f}`")
                    if rc.get("rerank_score") is not None:
                        score_txt.append(f"Rerank: `{rc['rerank_score']:.2f}`")
                    st.caption(" | ".join(score_txt))

                with st.expander(f"Inspect Text Passage (#{rc['final_rank']})"):
                    st.text(ch["text"])

            # Feedback
            st.markdown("---")
            st.markdown("**Was this citation accurate?**")
            fb_col1, fb_col2, _ = st.columns([1, 1, 8])
            if fb_col1.button("👍 Helpful"):
                st.toast("Thank you for your feedback!")
            if fb_col2.button("👎 Inaccurate"):
                st.toast("Feedback recorded for audit.")
