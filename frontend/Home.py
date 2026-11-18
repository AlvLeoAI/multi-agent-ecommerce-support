"""
E-Commerce Support System - Home
Multi-Agent Customer Support powered by Google ADK
"""

import streamlit as st

# Page config
st.set_page_config(
    page_title="E-Commerce Support System",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Main header
st.title("🛍️ E-Commerce Support System")
st.markdown("### Multi-Agent Customer Support powered by Google ADK")

st.markdown("---")

# Introduction
st.markdown("""
Welcome to the **E-Commerce Support System** - an intelligent customer support platform 
powered by multiple AI agents working together to provide the best customer experience.
""")

# Features
st.markdown("## 🌟 Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 💬 Intelligent Chat
    
    - Multi-agent coordination
    - Product recommendations
    - Math calculations
    - Human escalation support
    - Persistent conversation memory
    """)

with col2:
    st.markdown("""
    ### 📦 Product Catalog
    
    - Browse products
    - Search functionality
    - Real-time inventory
    - Detailed product info
    - Smart recommendations
    """)

with col3:
    st.markdown("""
    ### 📊 Quality Metrics
    
    - Real-time performance tracking
    - Response time monitoring
    - Success rate analytics
    - Token usage insights
    - Agent performance breakdown
    """)

st.markdown("---")

# System Architecture
st.markdown("## 🏗️ System Architecture")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### Backend Components
    
    - **FastAPI** - High-performance API
    - **Google ADK** - Agent Development Kit
    - **SQLite** - Persistent storage
    - **Gemini 2.0 Flash** - LLM model
    - **Quality Tracker** - Performance monitoring
    """)

with col2:
    st.markdown("""
    ### AI Agents
    
    - **Coordinator Agent** - Routes messages
    - **General Agent** - Greetings & general queries
    - **Product Agent** - Product searches (Google Search)
    - **Calculation Agent** - Math operations
    - **Human Escalation** - Complex cases
    """)

st.markdown("---")

# Quick Start
st.markdown("## 🚀 Quick Start")

st.markdown("""
1. **💬 Chat** - Start a conversation with our AI support agent
2. **📦 Products** - Browse our product catalog
3. **📊 Metrics** - View system performance and quality metrics
""")

st.info("👈 Use the sidebar to navigate between pages")

st.markdown("---")

# Technical Details
with st.expander("🔧 Technical Details"):
    st.markdown("""
    ### Technologies Used
    
    **Frontend:**
    - Streamlit
    - Plotly (visualizations)
    - Pandas (data processing)
    
    **Backend:**
    - FastAPI
    - Google ADK (Agent Development Kit)
    - SQLite
    - Uvicorn
    
    **AI/ML:**
    - Gemini 2.0 Flash
    - Google Search integration
    - Built-in code executor
    
    **Features:**
    - Multi-agent architecture
    - Persistent conversation memory
    - Quality tracking system
    - Real-time metrics dashboard
    """)

# Footer
st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: gray;'>
    <p>Built with ❤️ using Google ADK, FastAPI, and Streamlit</p>
    <p>© 2025 E-Commerce Support System</p>
</div>
""",
    unsafe_allow_html=True,
)
