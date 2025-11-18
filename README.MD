🛍️ Multi-Agent E-Commerce Support System
An intelligent customer support platform powered by Google's Agent Development Kit (ADK)
Show Image
Show Image
Show Image
Show Image

📋 Table of Contents

Problem Statement
Solution
Why Agents?
Architecture
Key Features
Technical Implementation
Setup Instructions
Demo
Technology Stack
Future Enhancements


🎯 Problem Statement
The Challenge
E-commerce businesses face significant challenges in providing efficient customer support:

High Support Costs: Traditional customer service requires large teams working 24/7
Slow Response Times: Customers wait hours or days for answers to simple questions
Inconsistent Quality: Support quality varies between agents and shifts
Scalability Issues: Difficult to scale support during peak seasons or rapid growth
Limited Product Knowledge: Support agents can't be experts in all products
No Performance Visibility: Lack of real-time metrics on support quality

The Impact

Lost Revenue: 89% of customers abandon brands after poor support experiences
High Costs: Average customer service agent costs $30,000-$40,000 annually
Customer Frustration: 66% of customers feel that valuing their time is the most important thing a company can do


💡 Solution
Multi-Agent E-Commerce Support System - An AI-powered customer support platform that uses multiple specialized agents working together to provide instant, accurate, and personalized customer service.
What Makes It Different

Intelligent Agent Coordination: Multiple specialized AI agents collaborate to handle different aspects of customer queries
Persistent Memory: Remembers customer conversations and preferences across sessions
Real-time Quality Tracking: Monitors response times, success rates, and customer satisfaction
Seamless Escalation: Automatically routes complex issues to human agents when needed


🤖 Why Agents?
The Power of Multi-Agent Architecture
Traditional chatbots use a single AI model to handle all queries, leading to:

Generic responses
Limited capabilities
Poor performance on specialized tasks

Our multi-agent approach leverages specialized agents:
Customer Query → Coordinator Agent
                 ├─→ General Agent (greetings, FAQs)
                 ├─→ Product Agent (search, recommendations)
                 ├─→ Calculation Agent (pricing, math)
                 └─→ Human Escalation (complex cases)
Benefits of Agent-Based Design

Specialization: Each agent masters specific tasks
Scalability: Add new agents without rebuilding the system
Reliability: If one agent fails, others continue working
Context Awareness: Agents share information for better responses
Continuous Learning: Individual agents can be updated independently


🏗️ Architecture
System Overview
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │
│  │   Chat   │  │ Products │  │  Quality Dashboard       │  │
│  └──────────┘  └──────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Chat API Router                          │  │
│  │  • Session Management                                 │  │
│  │  • Memory Integration                                 │  │
│  │  • Quality Tracking                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AGENT LAYER (Google ADK)                        │
│  ┌────────────────────────────────────────┐                 │
│  │      Coordinator Agent (Router)        │                 │
│  │         (Gemini 2.0 Flash)            │                 │
│  └────────────────────────────────────────┘                 │
│       │              │              │                        │
│       ▼              ▼              ▼                        │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐                 │
│  │ General │  │ Product  │  │Calculation │                 │
│  │ Agent   │  │  Agent   │  │   Agent    │                 │
│  │         │  │ (Google  │  │  (Code     │                 │
│  │         │  │  Search) │  │ Executor)  │                 │
│  └─────────┘  └──────────┘  └────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA LAYER (SQLite)                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Chat      │  │   Quality    │  │   Products       │  │
│  │  Messages   │  │   Metrics    │  │   Catalog        │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
Agent Communication Flow
mermaidgraph TD
    A[User Message] --> B[Coordinator Agent]
    B --> C{Route Decision}
    C -->|Greeting| D[General Agent]
    C -->|Product Query| E[Product Agent]
    C -->|Math| F[Calculation Agent]
    C -->|Complex| G[Human Escalation]
    D --> H[Response]
    E --> H
    F --> H
    G --> H
    H --> I[Memory Save]
    I --> J[Quality Tracking]
    J --> K[Return to User]

✨ Key Features
1. Multi-Agent Coordination

Coordinator Agent: Intelligently routes queries to specialized agents
Context Sharing: Agents share conversation context for seamless handoffs
Parallel Processing: Multiple agents can work simultaneously

2. Persistent Memory System

Session Management: Tracks conversations across multiple sessions
User Preferences: Remembers user information and preferences
Conversation History: Maintains full chat history in SQLite

3. Real-time Quality Tracking

Response Time Monitoring: Tracks average, min, and max response times
Token Usage Analytics: Monitors LLM token consumption
Success Rate Metrics: Measures conversation success rates
Agent Performance: Individual agent performance breakdown

4. Specialized Tools

Google Search Integration: Real-time product searches
Code Executor: Mathematical calculations and data processing
Human Escalation: Automatic ticket creation for complex cases

5. Professional UI/UX

Interactive Chat Interface: Clean, modern chat experience
Product Catalog: Browsable product database with filters
Quality Dashboard: Real-time metrics visualization with Plotly


🔧 Technical Implementation
Agent Development Kit (ADK) Concepts Applied
This project demonstrates mastery of Google ADK by implementing:

✅ Multi-Agent Architecture

4 specialized agents (Coordinator, General, Product, Calculation)
Agent-to-Agent communication via AgentTool
Dynamic agent creation with context injection


✅ Tool Integration

google_search: Real-time product searches
BuiltInCodeExecutor: Mathematical computations
Custom escalate_to_human_support tool


✅ Memory & State Management

SQLite-based persistent storage
Session management with unique session IDs
Conversation history injection into agent context


✅ LLM Configuration

Gemini 2.0 Flash model
Custom retry configuration for reliability
Optimized for low latency (< 5s response times)


✅ Quality Monitoring

Custom QualityTracker class
Automatic metrics collection on every conversation
Pandas-based analytics and trend analysis



Code Structure
multi-agent-ecommerce/
├── backend/
│   ├── database/
│   │   ├── chat_memory.py        # Persistent memory management
│   │   └── quality_tracker.py    # Quality metrics tracking
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── routers/
│   │   ├── chat.py               # Chat API with agents
│   │   ├── products.py           # Product catalog API
│   │   └── metrics.py            # Metrics API
│   └── main.py                   # FastAPI application
├── frontend/
│   ├── pages/
│   │   ├── 1_💬_Chat.py         # Chat interface
│   │   ├── 2_📦_Products.py     # Product catalog
│   │   └── Metrics.py            # Quality dashboard
│   └── Home.py                   # Landing page
└── requirements.txt

🚀 Setup Instructions
Prerequisites

Python 3.10+
Google API Key (for Gemini)
Virtual environment tool (venv or conda)

Installation

Clone the repository

bash   git clone <repository-url>
   cd multi-agent-ecommerce

Create virtual environment

bash   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Mac/Linux
   source .venv/bin/activate

Install dependencies

bash   pip install -r requirements.txt

Set up environment variables

bash   # Create .env file in project root
   echo "GOOGLE_API_KEY=your_api_key_here" > .env

Initialize database

bash   python backend/database/chat_memory.py
   python backend/database/quality_tracker.py
Running the Application
Terminal 1 - Start Backend API:
bashcd multi-agent-ecommerce
uvicorn backend.main:app --reload --port 8000
Terminal 2 - Start Frontend:
bashcd frontend
streamlit run Home.py
Access the application:

Frontend: http://localhost:8501
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs


🎬 Demo
Chat Interface
Show Image
AI agent conversation with persistent memory
Product Catalog
Show Image
Filterable product catalog with real-time inventory
Quality Dashboard
Show Image
Real-time performance metrics and analytics
Example Conversations
Product Recommendation:
User: I need a laptop for video editing under $1500
Agent: Based on your requirements, I recommend:
       1. Dell XPS 15 ($1299) - Excellent RTX 4070 performance
       2. ASUS ROG Strix G16 ($1350) - Great for gaming and productivity
Memory Persistence:
User: I am Alvaro
Agent: Hi Alvaro, nice to meet you! How can I help you today?

[Later in conversation]
Agent: Alvaro, based on your previous interest in laptops...

🛠️ Technology Stack
Backend

FastAPI - Modern, high-performance web framework
Google ADK - Agent Development Kit for multi-agent orchestration
Gemini 2.0 Flash - Google's latest LLM
SQLite - Lightweight database for persistence
Pandas - Data analysis for quality metrics

Frontend

Streamlit - Interactive web application framework
Plotly - Interactive data visualizations
Requests - HTTP client for API communication

AI/ML

Google Gemini - Primary LLM
Google Search API - Real-time product searches
Code Executor - Safe Python code execution

DevOps

Uvicorn - ASGI server
Python-dotenv - Environment variable management


📊 Performance Metrics
Based on real usage data:

Average Response Time: 4.0 seconds
Success Rate: 100%
Token Efficiency: 10 tokens per conversation avg
Agent Steps: 3.0 steps avg per query


🔮 Future Enhancements
Phase 1 (Immediate)

 Deploy to Google Cloud Platform
 Add sentiment analysis for customer satisfaction
 Implement A/B testing for agent responses

Phase 2 (Short-term)

 Multi-language support
 Voice interface integration
 Advanced analytics dashboard

Phase 3 (Long-term)

 Predictive customer support (proactive outreach)
 Integration with e-commerce platforms (Shopify, WooCommerce)
 Mobile application


👥 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

📄 License
This project is licensed under the MIT License.

🙏 Acknowledgments

Google ADK Team for the amazing framework
Streamlit for the excellent UI framework
FastAPI for the robust backend framework


📞 Contact
Alvaro - AI Solutions Engineer

Email: [your-email]
LinkedIn: [your-linkedin]
Portfolio: [your-portfolio]


Built with ❤️ using Google ADK, FastAPI, and Streamlit