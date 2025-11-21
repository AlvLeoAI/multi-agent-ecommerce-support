"""
Quality Metrics Dashboard
Streamlit dashboard for visualizing agent performance metrics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Agent Quality Dashboard",
    page_icon="📊",
    layout="wide"
)

# API Configuration
API_BASE_URL = "https://ecommerce-agent-backend-89106065348.southamerica-east1.run.app"

def fetch_quality_metrics(days=7):
    """Fetch quality metrics from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/chat/quality-metrics?days={days}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching metrics: {str(e)}")
        return None

def main():
    # Header
    st.title("🤖 Agent Quality Dashboard")
    st.markdown("Real-time performance metrics for the Multi-Agent E-Commerce Support System")
    
    # Sidebar
    st.sidebar.title("Settings")
    days_filter = st.sidebar.slider("Days to analyze", 1, 30, 7)
    refresh_button = st.sidebar.button("🔄 Refresh Data")
    
    # Fetch data
    data = fetch_quality_metrics(days_filter)
    
    if not data:
        st.warning("No data available. Make sure the API is running.")
        return
    
    summary = data.get("summary", {})
    by_agent = data.get("by_agent", [])
    trends = data.get("trends", [])
    
    # Overview Cards
    st.markdown("### 📊 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Conversations",
            value=summary.get("total_conversations", 0),
            delta=None
        )
    
    with col2:
        avg_time = summary.get("avg_response_time") or 0.0
        st.metric(
            label="Avg Response Time",
            value=f"{avg_time:.2f}s",
            delta=None
        )
    
    with col3:
        success_rate = summary.get("success_rate") or 0.0
        st.metric(
            label="Success Rate",
            value=f"{success_rate:.1f}%",
            delta=None
        )
    
    with col4:
        avg_tokens = summary.get("avg_tokens") or 0.0
        st.metric(
            label="Avg Tokens/Conv",
            value=f"{avg_tokens:.0f}",
            delta=None
        )
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        # Response Time Gauge
        st.markdown("### ⏱️ Response Time Performance")
        
        avg_time = summary.get("avg_response_time", 0)
        min_time = summary.get("min_response_time", 0)
        max_time = summary.get("max_response_time", 0)
        
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=avg_time,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Average Response Time (seconds)"},
            delta={'reference': 3.0, 'increasing': {'color': "red"}},
            gauge={
                'axis': {'range': [None, 10]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 2], 'color': "lightgreen"},
                    {'range': [2, 5], 'color': "yellow"},
                    {'range': [5, 10], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 5
                }
            }
        ))
        
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.info(f"📉 Min: {min_time:.2f}s | 📈 Max: {max_time:.2f}s")
    
    with col2:
        # Success Rate Gauge
        st.markdown("### ✅ Success Rate")
        
        success_rate = summary.get("success_rate", 0)
        error_rate = summary.get("error_rate", 0)
        
        fig_success = go.Figure(go.Indicator(
            mode="gauge+number",
            value=success_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Success Rate (%)"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "green"},
                'steps': [
                    {'range': [0, 70], 'color': "lightcoral"},
                    {'range': [70, 90], 'color': "yellow"},
                    {'range': [90, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 95
                }
            }
        ))
        
        fig_success.update_layout(height=300)
        st.plotly_chart(fig_success, use_container_width=True)
        
        st.info(f"❌ Error Rate: {error_rate:.1f}%")
    
    st.markdown("---")
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        # Token Usage
        st.markdown("### 🔢 Token Usage")
        
        token_data = {
            'Metric': ['Total Tokens', 'Avg Tokens/Conv'],
            'Value': [
                summary.get("total_tokens", 0),
                summary.get("avg_tokens", 0)
            ]
        }
        
        df_tokens = pd.DataFrame(token_data)
        
        fig_tokens = px.bar(
            df_tokens,
            x='Metric',
            y='Value',
            color='Metric',
            text='Value',
            title="Token Consumption"
        )
        
        fig_tokens.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig_tokens.update_layout(showlegend=False, height=300)
        
        st.plotly_chart(fig_tokens, use_container_width=True)
    
    with col2:
        # Agent Performance
        st.markdown("### 🤖 Agent Performance")
        
        if by_agent:
            df_agents = pd.DataFrame(by_agent)
            
            fig_agents = px.bar(
                df_agents,
                x='agent_used',
                y='conversations',
                color='avg_response_time',
                text='conversations',
                title="Conversations by Agent",
                labels={
                    'agent_used': 'Agent',
                    'conversations': 'Conversations',
                    'avg_response_time': 'Avg Response Time (s)'
                },
                color_continuous_scale='Blues'
            )
            
            fig_agents.update_traces(texttemplate='%{text}', textposition='outside')
            fig_agents.update_layout(height=300)
            
            st.plotly_chart(fig_agents, use_container_width=True)
        else:
            st.info("No agent data available yet.")
    
    st.markdown("---")
    
    # Trends Chart
    st.markdown("### 📈 Historical Trends")
    
    if trends and len(trends) > 0:
        df_trends = pd.DataFrame(trends)
        
        # Two separate charts side by side
        col1, col2 = st.columns(2)
        
        with col1:
            # Response Time Trend
            fig_time = px.line(
                df_trends,
                x='date',
                y='avg_response_time',
                title='Average Response Time Over Time',
                markers=True,
                labels={'date': 'Date', 'avg_response_time': 'Avg Response Time (s)'}
            )
            fig_time.update_traces(line=dict(color='#3b82f6', width=3), marker=dict(size=8))
            fig_time.update_layout(height=350)
            st.plotly_chart(fig_time, use_container_width=True)
        
        with col2:
            # Conversations Trend
            fig_conv = px.bar(
                df_trends,
                x='date',
                y='conversations',
                title='Conversations Over Time',
                labels={'date': 'Date', 'conversations': 'Conversations'}
            )
            fig_conv.update_traces(marker=dict(color='#10b981'))
            fig_conv.update_layout(height=350)
            st.plotly_chart(fig_conv, use_container_width=True)
        
        # Token usage trend
        st.markdown("#### 🔢 Token Usage Trend")
        fig_tokens = px.line(
            df_trends,
            x='date',
            y='avg_tokens',
            title='Average Tokens per Conversation',
            markers=True,
            labels={'date': 'Date', 'avg_tokens': 'Avg Tokens'}
        )
        fig_tokens.update_traces(line=dict(color='#f59e0b', width=3), marker=dict(size=8))
        fig_tokens.update_layout(height=300)
        st.plotly_chart(fig_tokens, use_container_width=True)
        
    else:
        st.info("📊 No trend data available yet. Start more conversations to see trends over time!")
    
    st.markdown("---")
    
    # Detailed Metrics Table
    st.markdown("### 📋 Detailed Metrics")
    
    # Summary metrics
    summary_data = {
        'Metric': [
            'Total Conversations',
            'Average Response Time',
            'Min Response Time',
            'Max Response Time',
            'Total Tokens',
            'Average Tokens',
            'Average Steps',
            'Success Rate',
            'Error Rate'
        ],
        'Value': [
            summary.get('total_conversations', 0),
            f"{summary.get('avg_response_time', 0):.3f}s",
            f"{summary.get('min_response_time', 0):.3f}s",
            f"{summary.get('max_response_time', 0):.3f}s",
            summary.get('total_tokens', 0),
            f"{summary.get('avg_tokens', 0):.1f}",
            f"{summary.get('avg_steps', 0):.1f}",
            f"{summary.get('success_rate', 0):.2f}%",
            f"{summary.get('error_rate', 0):.2f}%"
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    # Agent breakdown
    if by_agent:
        st.markdown("#### Agent Breakdown")
        df_agents_table = pd.DataFrame(by_agent)
        st.dataframe(df_agents_table, use_container_width=True, hide_index=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"📊 Analyzing last {days_filter} days"
    )

if __name__ == "__main__":
    main()



















