"""
E-Commerce Support System - Home
Deterministic Multi-Agent Customer Support & Dispute Verification powered by Google ADK
"""

import streamlit as st

st.set_page_config(
    page_title="E-Commerce Support System",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Main header
st.title("🛍️ E-Commerce Support & Evidence Verification System")
st.markdown(
    "### Deterministic Multi-Agent Commerce & Dispute Verification powered by Google ADK (`google-adk==2.14.1`)"
)

st.markdown("---")

# Architectural Invariant Banner
st.info(
    "**Core Architectural Invariant:** Probabilistic LLM reasoning (**Gemini 3.8 Flash**) is "
    "strictly decoupled from financial arithmetic, inventory validation, state mutations, and "
    "x402 payment/fulfillment evidence verification."
)

# Features
st.markdown("## 🌟 Core Capabilities")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        ### 💬 Multi-Agent Chat
        - `CoordinatorAgent` routing via `InMemoryRunner.run_async`
        - Deterministic `Decimal` cart quotes (`amount_cents` & `sim_usdc_micros`)
        - x402 `PurchaseEvidence` / `GrantEvidence` claim verification
        - Persistent SQLite human escalation tickets
        - Per-turn specialist attribution badges
        """
    )

with col2:
    st.markdown(
        """
        ### 📦 Deterministic Product Catalog
        - SQLite-backed product & inventory catalog (`catalog_db.py`)
        - Category, price-range, stock & text filtering
        - Real-time stock status & restock dates
        - One-click **Quote / Ask Agent** handoff to Chat
        """
    )

with col3:
    st.markdown(
        """
        ### 📊 Quality & Telemetry Dashboard
        - Parameterized SQLite `QualityTracker` metrics
        - Dynamic multi-agent latency gauge & trends
        - Per-specialist attribution breakdown table
        - Token usage & success/error rate monitoring
        """
    )

st.markdown("---")

# System Architecture
st.markdown("## 🏗️ Production Architecture (Phases 1–4)")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        ### Runtime, Security & Evaluation
        - **Model & Runtime**: **Gemini 3.8 Flash** on **Google ADK (`google-adk==2.14.1`)** via `InMemoryRunner.run_async`
        - **Backend**: FastAPI, Pydantic v2, SQLite (`PRAGMA foreign_keys = ON`)
        - **Prompt Boundary Hardening**: Constant system instructions with `<user_query>` XML envelope & best-effort role-spoof sanitization
        - **Verification & Eval Rigor**: **Automated offline test suite** (`pytest`, run in CI) and **24/24 (100%)** offline golden evaluation suite (`eval/runner.py`)
        """
    )

with col2:
    st.markdown(
        """
        ### 4 Specialist Agents + Coordinator
        - **🧠 `CoordinatorAgent`**: Constant routing prompt delegating to specialist `AgentTool`s
        - **📦 `ProductAgent`**: Deterministic SQLite catalog search, specs & stock verification
        - **🧮 `CalculationAgent`**: Pure `Decimal` (`ROUND_HALF_UP`) + `amount_cents` / `sim_usdc_micros` ($10^6$) pricing engine — **zero LLM math**
        - **🧾 `OrderSupportAgent`**: Verifies x402 `PurchaseEvidence` & `GrantEvidence` dispute claims (`confirmed`, `contradicted`, `unverifiable`)
        - **💬 `GeneralAgent`**: General inquiries & durable SQLite human escalation tickets
        """
    )

st.markdown("---")

# Quick Start
st.markdown("## 🚀 Explore the System")

st.markdown(
    """
    1. **💬 Chat** — Try one-click showcase prompts for stock lookup, deterministic quotes, x402 evidence verification, and prompt-injection guardrails
    2. **🛒 Products** — Browse the SQLite catalog and launch a prefilled quote directly in Chat
    3. **📊 Metrics** — Inspect live latency gauges, historical trends, and per-specialist telemetry
    """
)

st.info("👈 Use the sidebar to navigate between pages")

st.markdown("---")

with st.expander("🔧 Technical Stack & Portfolio Alignment"):
    st.markdown(
        """
        **Orchestration & AI:**
        - Google ADK (`google-adk==2.14.1`) with `InMemoryRunner.run_async`
        - Gemini 3.8 Flash (`google-genai`)
        - JSON-safe `FunctionTool` wrappers over deterministic domain services

        **Backend & Persistence:**
        - FastAPI + Uvicorn / Gunicorn
        - Pydantic v2 strict contracts (`OrderRecordContract`, `PurchaseEvidence`, `GrantEvidence`, `ClaimVerificationResult`, `SupportTicketContract`)
        - SQLite (`chat_memory.py`, `catalog_db.py`, `orders_db.py`, `quality_tracker.py`)

        **Frontend:**
        - Streamlit native `st.chat_message`, theme-adaptive containers & Plotly dashboards
        """
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p>Built with Google ADK, Gemini 3.8 Flash, FastAPI, SQLite, and Streamlit</p>
        <p>© 2026 E-Commerce Support & Evidence Verification System</p>
    </div>
    """,
    unsafe_allow_html=True,
)
