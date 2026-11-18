# multi-agent-ecommerce-support

## What this project does
Prototype of an e-commerce support system that combines chat orchestration, product lookup, simple calculations, conversation memory, and quality metrics. The intended experience is a Streamlit frontend backed by FastAPI and Google ADK agents using Gemini.

Observed maturity: `prototype`.

## Main architecture
The repo is split into a backend and frontend:
- `backend/` provides chat, products, and metrics APIs.
- `frontend/` provides Streamlit pages for chat, product browsing, and quality dashboards.
- Chat state is persisted in local SQLite files.
- Agent execution happens in-process using Google ADK and Gemini.

The product and metrics routes expect a local product catalog JSON file, but that file is missing from the observed repo contents.

## Main components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| App bootstrap | `backend/main.py` | 93 | FastAPI lifespan, CORS, router registration |
| Chat orchestration | `backend/routers/chat.py` | 326 | Agent runtime, memory injection, quality tracking |
| Products API | `backend/routers/products.py` | 166 | Catalog CRUD, search/filter, stock check |
| Metrics API | `backend/routers/metrics.py` | 135 | Overview, top products, agent performance |
| Pydantic schemas | `backend/models/schemas.py` | 95 | ChatRequest/Response, Product, QualityMetrics |
| Chat memory | `backend/database/chat_memory.py` | 215 | SQLite: sessions, messages, preferences |
| Quality tracker | `backend/database/quality_tracker.py` | 175 | Metric collection, trend analysis, Pandas analytics |
| Support agent | `backend/agents/customer_support_agent.py` | 78 | ADK LlmAgent + general sub-agent |
| Product agent | `backend/agents/product_catalog_agent.py` | 154 | Product tools: search, info, inventory |
| Backend Dockerfile | `backend/Dockerfile` | 51 | Multi-stage build, Gunicorn + Uvicorn |
| Landing page | `frontend/Home.py` | 152 | Feature showcase |
| Chat UI | `frontend/pages/1_💬_Chat.py` | 207 | Interactive chat with session persistence |
| Products UI | `frontend/pages/2_🛒_Products.py` | 193 | Catalog browser with filters |
| Metrics UI | `frontend/pages/3_📊_Metrics.py` | 347 | Quality dashboard with Plotly |
| API client | `frontend/utils/api_client.py` | 151 | Singleton pattern, retry/timeout handling |
| DevContainer | `.devcontainer/devcontainer.json` | 50 | VS Code environment config |

**Total:** ~3,656 lines across 24 Python files.

## Inputs / outputs
- Inputs:
- Chat payloads with `message`, `user_id`, and optional `session_id`.
- Preference payloads for user profile state.
- Product filters and metrics query parameters.
- Outputs:
- Chat responses and session history.
- Quality summaries and trend data.
- Product catalog results when the catalog file exists.

## Dependencies
- **Backend:** FastAPI, Gunicorn, Uvicorn, Pydantic, python-dotenv
- **AI:** `google-genai`, `google-cloud-aiplatform`, `google-adk` (installed from GitHub HEAD — no version pin)
- **Data:** Pandas, NumPy, protobuf (pinned for Streamlit compat), watchdog
- **Frontend:** Streamlit, Requests, Plotly, Pandas
- **Test:** pytest, httpx (listed but no test files exist)
- **Local files:** `my_agent_data.db` (sessions), `ecommerce_agent.db` (quality metrics)
- **Missing:** `backend/database/products.json` referenced by code but absent from repo
- **Env vars:** `GOOGLE_API_KEY` (required), `AGENT_MODEL` (optional, default `gemini-2.0-flash-exp`), `PORT`, `API_URL`, `PROJECT_ID`, `DATABASE_URL`

## AI/LLM details
- Model: Gemini 2.0 Flash (experimental) via Google ADK
- Agent pattern: Hierarchical — coordinator routes to general/product/calculation sub-agents
- Retry: 5 attempts, exponential backoff (base 7), handles 429/500/503/504
- Calculation agent uses ADK's `BuiltInCodeExecutor()` for arbitrary Python execution
- Token estimation: heuristic (1 token ≈ 4 characters)
- Context injection: last 10 messages loaded per request (~1000 tokens)

## Database schema (SQLite)
- `chat_sessions`: session_id, user_id, created_at, last_active, metadata (JSON)
- `chat_messages`: id, session_id (FK), role, content, timestamp
- `user_preferences`: user_id, preferences (JSON), updated_at
- `quality_metrics`: id, conversation_id, response_time, tokens_used, steps_count, agent_used, success, user_rating, error_occurred, timestamp

## Risks / tradeoffs
- `backend/database/products.json` is required by `products.py` and `metrics.py` but is not present.
- README install/run instructions do not match the file layout. There is no root `requirements.txt`, and import style in `backend/main.py` conflicts with the documented `uvicorn backend.main:app` command.
- Frontend and backend endpoint conventions do not line up consistently, especially for product APIs.
- Some frontend code uses hardcoded deployed URLs while other parts assume localhost.
- No tests or checked-in CI workflows were found.
- SQLite and in-process ADK execution limit concurrency and operational robustness.
- The agent path includes web search and built-in code execution without an observed access-control layer.

## Suggested next steps
1. Add `products.json` seed data (or document how to create it)
2. Migrate to Cloud SQL (PostgreSQL) for production persistence
3. Pin `google-adk` to a specific commit or release tag
4. Add pytest suite — at minimum test agent routing and product tools
5. Add `.env.example` documenting all required/optional env vars
6. Normalize endpoint paths and frontend API client URLs
7. Pick a single package/import strategy and update run commands
8. Add JWT authentication + RBAC
9. Make SQLite calls async (aiosqlite) or switch to async PG
10. Decide canonical agent location: `backend/agents/*` vs inline in `backend/routers/chat.py`
11. Implement sliding window or summarization for long conversations
12. Add rate limiting (Redis-backed or SlowAPI)
