"""
Chat Page - Customer Support Chat Interface
Real-time conversation with the Multi-Agent Support System
"""

import streamlit as st
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.api_client import api_client

# Page configuration
st.set_page_config(
    page_title="Chat - E-Commerce Support",
    page_icon="💬",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #1f77b4;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: #2d2d2d;
        margin-right: 20%;
    }
    .message-content {
        color: white;
        font-size: 1rem;
        line-height: 1.5;
    }
    .message-label {
        font-size: 0.8rem;
        color: #aaa;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Page header
st.title("💬 Customer Support Chat")
st.markdown("Ask me anything about our products! I'm here to help you find what you need.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"

# Sidebar with info
with st.sidebar:
    st.subheader("💡 Chat Info")
    st.info(f"**Session ID:** {st.session_state.session_id}")
    st.metric("Messages", len(st.session_state.messages))
    
    st.markdown("---")
    
    st.subheader("✨ Try asking:")
    st.markdown("""
    - *"I need a laptop for video editing under $1500"*
    - *"Do you have the iPhone 15 Pro?"*
    - *"Compare Dell XPS 15 vs MacBook Pro"*
    - *"What headphones do you recommend for work?"*
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        # Generate new session ID
        import uuid
        st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
        st.rerun()

# Display chat messages
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f"""
            <div class="chat-message user-message">
                <div class="message-label">👤 You</div>
                <div class="message-content">{content}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="chat-message assistant-message">
                <div class="message-label">🤖 Support Agent</div>
                <div class="message-content">{content}</div>
            </div>
        """, unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type your message here...", key="chat_input")

if user_input:
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Show user message immediately
    st.markdown(f"""
        <div class="chat-message user-message">
            <div class="message-label">👤 You</div>
            <div class="message-content">{user_input}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Show loading spinner while waiting for response
    with st.spinner("🤖 Support Agent is thinking..."):
        # Call backend API
        response = api_client.send_message(
            message=user_input,
            user_id="streamlit_user",
            session_id=st.session_state.session_id
        )
    
    # Check for errors
    if "error" in response and response["error"]:
        st.error(f"❌ Error: {response.get('message', 'Unknown error')}")
        st.info("💡 Make sure the backend is running on http://localhost:8000")
    else:
        # Add assistant response to chat history
        assistant_message = response.get("response", "I apologize, but I couldn't process your request.")
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Rerun to show the new message
        st.rerun()

# Show helpful message if no messages yet
if len(st.session_state.messages) == 0:
    st.info("👋 **Welcome!** Start a conversation by typing a message below. Ask me about products, pricing, availability, or anything else!")
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Start")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💻 Ask about laptops", use_container_width=True):
            st.session_state.temp_message = "I need a laptop for video editing under $1500"
            st.rerun()
    
    with col2:
        if st.button("📱 Ask about phones", use_container_width=True):
            st.session_state.temp_message = "Do you have the iPhone 15 Pro in stock?"
            st.rerun()

# Handle temp message from quick buttons
if "temp_message" in st.session_state:
    user_input = st.session_state.temp_message
    del st.session_state.temp_message
    
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Get response
    with st.spinner("🤖 Support Agent is thinking..."):
        response = api_client.send_message(
            message=user_input,
            user_id="streamlit_user",
            session_id=st.session_state.session_id
        )
    
    if "error" not in response or not response["error"]:
        assistant_message = response.get("response", "I apologize, but I couldn't process your request.")
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message
        })
    
    st.rerun()








