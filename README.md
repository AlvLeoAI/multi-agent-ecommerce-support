# 🛍️ Multi-Agent E-Commerce Support System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/AI-Google_Gemini_2.0-8E75B2?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> **An intelligent customer support platform orchestrated by Google's Agent Development Kit (ADK).**

---

## 🎯 Problem Statement

**The Challenge:** E-commerce businesses face significant hurdles in scaling support:
* **High Costs:** Human teams are expensive to maintain 24/7.
* **Slow Response:** Customers abandon carts while waiting for answers.
* **Information Silos:** Agents lack instant access to real-time inventory or complex math capabilities.

**The Solution:** A **Multi-Agent Architecture** where specialized AI workers collaborate to handle inquiries, execute code, and manage inventory data instantly, with persistent memory and quality tracking.

---

## 🤖 Why Multi-Agent?

Traditional chatbots use a single LLM prompt, leading to hallucinations and generic answers. **This system uses a swarm of specialized agents:**

```mermaid
graph TD
    User[👤 Customer] --> Coordinator[📡 Coordinator Agent]
    
    Coordinator -->|Greeting/General| General[💬 General Agent]
    Coordinator -->|Product Search| Product[📦 Product Agent]
    Coordinator -->|Price/Math| Calc[🧮 Calculation Agent]
    Coordinator -->|Complex Issue| Human[🆘 Human Escalation]
    
    General --> Response
    Product --> Response
    Calc --> Response
    Human --> Response
    
    Response[⚡ Final Response] --> Memory[💾 SQLite Memory]
    Memory --> Quality[📊 Quality Tracker]
Specialization: The Product Agent has access to search tools, while the Calculation Agent runs Python code for math.

Reliability: Separation of concerns prevents logic conflicts.

Scalability: New agents (e.g., "Shipping Agent") can be added without breaking existing logic.

🏗️ System Architecture
The project follows a clean Monorepo structure separating the reactive frontend from the logic-heavy backend.

📂 Project Structure
Bash

multi-agent-ecommerce/
├── 🐳 .devcontainer/       # Standardized Development Environment
├── 📂 backend/             # FastAPI Application
│   ├── 📂 agents/          # Google ADK Agent Logic
│   ├── 📂 database/        # SQLite & Memory Persistence
│   ├── 📂 routers/         # API Endpoints (Chat, Metrics)
│   └── 📄 main.py          # Entry Point
├── 📂 frontend/            # Streamlit Application
│   ├── 📂 pages/           # UI Pages (Chat, Dashboard)
│   └── 📄 Home.py          # Landing Page
├── 📄 ARCHITECTURE.md      # Deep dive into system design
└── 📄 DEPLOYMENT.md        # Production deployment guide
✨ Key Features
1. Intelligent Orchestration
Uses Google ADK to route queries. If a user asks "How much is the iPhone 15 plus 20% tax?", the Coordinator invokes the Product Agent to get the price and then the Calculation Agent to compute the total.

2. Persistent Memory (Stateful)
Unlike basic RAG bots, this system remembers.

Session Management: Unique session IDs track conversations.

Context Injection: Past interactions are injected into the agent's context window.

3. Real-Time Quality Engineering
Includes a custom QualityTracker class that monitors:

⏱️ Latency: Response time per turn.

🎫 Success Rate: Automated conversation scoring.

🪙 Token Usage: Cost monitoring.

🚀 Setup Instructions
Prerequisites
Python 3.10+

Google Cloud API Key (Gemini)

Installation
Clone the repository

Bash

git clone [https://github.com/AlvLeoAl/multi-agent-ecommerce-support.git](https://github.com/AlvLeoAl/multi-agent-ecommerce-support.git)
cd multi-agent-ecommerce-support
Create Virtual Environment

Bash

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
Install Dependencies

Bash

pip install -r requirements.txt
Configure Environment Create a .env file in the root:

Code snippet

GOOGLE_API_KEY=your_api_key_here
Run the System Terminal 1 (Backend):

Bash

uvicorn backend.main:app --reload --port 8000
Terminal 2 (Frontend):

Bash

cd frontend
streamlit run Home.py
🛠️ Technology Stack
LLM Orchestration: Google Agent Development Kit (ADK), Gemini 2.0 Flash

Backend: FastAPI, Pydantic, SQLite

Frontend: Streamlit, Plotly

DevOps: Docker, DevContainers

📬 Contact
Alvaro - AI Solutions Engineer

Building scalable AI architectures bridging business logic and software engineering.

Built with ❤️ using Google ADK & Python.
