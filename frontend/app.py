"""
E-Commerce Multi-Agent Support System
Landing Page - Streamlit Frontend
"""

import streamlit as st
import sys
from pathlib import Path

# Add utils to path for imports
sys.path.append(str(Path(__file__).parent))

from utils.api_client import api_client

# Page configuration
st.set_page_config(
    page_title="E-Commerce Support System",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
# Custom CSS
st.markdown("""
    <style>
    /* 1. Encabezado principal */
    .main-header {
        font-size: 3.5rem; /* Más grande */
        font-weight: 800; /* Más audaz */
        text-align: center;
        color: #4CAF50; /* Verde vibrante (o un azul como #2196F3) */
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px #000000; /* Sombra sutil */
    }
    .sub-header {
        font-size: 1.6rem;
        text-align: center;
        color: #BBBBBB; /* Gris claro para buen contraste en tema oscuro */
        margin-bottom: 2rem;
    }
    
    /* 2. Cajas de características (Feature Boxes) */
    .feature-box {
        background-color: #262730; /* Un gris oscuro, ligeramente más claro que el fondo principal de Streamlit */
        padding: 1.5rem;
        border-radius: 12px; /* Esquinas más redondeadas */
        margin-bottom: 1.5rem;
        box-shadow: 4px 4px 8px rgba(0, 0, 0, 0.4); /* Sombra para profundidad */
        border-left: 5px solid #4CAF50; /* Línea de color a la izquierda para destacar */
        transition: transform 0.2s; /* Efecto hover */
    }
    .feature-box:hover {
        transform: translateY(-5px); /* Se levanta un poco al pasar el mouse */
        box-shadow: 6px 6px 12px rgba(0, 0, 0, 0.6);
    }
    .feature-box h3 {
        color: #4CAF50; /* Título de la caja en color primario */
        font-weight: 700;
        margin-top: 0;
    }
    .feature-box ul {
        padding-left: 20px;
        list-style-type: '👉'; /* Icono moderno para las listas */
    }
    .feature-box li {
        margin-bottom: 5px;
    }

    /* 3. Badges de Tecnología */
    .tech-badge {
        background-color: #383842; /* Fondo de badge más oscuro */
        color: #90CAF9; /* Texto en un azul claro */
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.4rem 0.2rem;
        font-weight: 600;
        border: 1px solid #4CAF50; /* Borde sutil del color primario */
    }

    /* Ajustar el éxito y el error para que se vean bien */
    .stSuccess {
        background-color: #1E4620 !important;
        border-left: 5px solid #4CAF50 !important;
        padding: 10px;
        border-radius: 5px;
    }
    .stError {
        background-color: #4B2727 !important;
        border-left: 5px solid #F44336 !important;
        padding: 10px;
        border-radius: 5px;
    }
    
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🛒 E-Commerce Support System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent Customer Support powered by Google ADK</div>', unsafe_allow_html=True)

# Backend health check
with st.spinner("Checking backend connection..."):
    backend_healthy = api_client.health_check()

if backend_healthy:
    st.success("✅ Backend API is running and healthy!")
else:
    st.error("❌ Cannot connect to backend API. Make sure it's running on http://localhost:8000")
    st.info("Start the backend with: `python -m uvicorn ecommerce_support.backend.main:app --reload`")

st.markdown("---")

# Project Overview
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-box">
        <h3>🤖 Multi-Agent System</h3>
        <p>Powered by Google ADK with intelligent agent orchestration</p>
        <ul>
            <li>Customer Support Agent</li>
            <li>Product Catalog Agent</li>
            <li>Sub-agent communication</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-box">
        <h3>⚡ Real-time Support</h3>
        <p>Instant responses with context-aware conversations</p>
        <ul>
            <li>Product recommendations</li>
            <li>Inventory management</li>
            <li>Session memory</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-box">
        <h3>📊 Analytics Dashboard</h3>
        <p>Track performance and user interactions</p>
        <ul>
            <li>Conversation metrics</li>
            <li>Product queries</li>
            <li>Real-time stats</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Technology Stack
st.subheader("🔧 Technology Stack")

tech_stack = {
    "Backend": ["FastAPI", "Google ADK", "Python", "Gemini 2.5 Flash"],
    "Frontend": ["Streamlit", "Plotly", "Pandas"],
    "AI/ML": ["Google Gemini API", "Multi-Agent Orchestration", "Session Management"]
}

for category, techs in tech_stack.items():
    st.markdown(f"**{category}:**")
    tech_html = "".join([f'<span class="tech-badge">{tech}</span>' for tech in techs])
    st.markdown(tech_html, unsafe_allow_html=True)
    st.markdown("")

st.markdown("---")

# Quick Start Guide
st.subheader("🚀 Quick Start")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 💬 Try the Chat
    1. Navigate to **Chat** in the sidebar
    2. Ask about products (e.g., "I need a laptop for video editing")
    3. Get instant AI-powered recommendations
    """)

with col2:
    st.markdown("""
    ### 📦 Browse Products
    1. Navigate to **Products** in the sidebar
    2. Explore the product catalog
    3. Filter by category, price, or availability
    """)

st.markdown("---")

# Project Info
with st.expander("ℹ️ About This Project"):
    st.markdown("""
    **E-Commerce Multi-Agent Support System** is a portfolio project demonstrating:
    
    - 🎯 **Google ADK Integration**: Multi-agent architecture with intelligent orchestration
    - 🔄 **Agent Communication**: Sub-agent delegation for specialized tasks
    - 💾 **Session Management**: Context-aware conversations with memory
    - 🏗️ **Production-Ready**: FastAPI backend with proper error handling
    - 🎨 **Modern UI**: Streamlit interface with real-time updates
    
    **Built by:** Alvaro - AI Solutions Engineer
    
    **Tech Highlights:**
    - Google Agent Development Kit (ADK)
    - Gemini 2.5 Flash Lite
    - FastAPI + Pydantic
    - Streamlit Multi-Page Apps
    - RESTful API Design
    """)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p>Built with ❤️ using Google ADK, FastAPI, and Streamlit</p>
        <p>© 2024 - Portfolio Project</p>
    </div>
""", unsafe_allow_html=True)