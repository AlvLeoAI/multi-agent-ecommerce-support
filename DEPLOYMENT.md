# 🚀 Deployment Guide

> **Container & Cloud Run deployment guide for the Multi-Agent E-Commerce Support System.**

---

## 1. Prerequisites

* Docker `>= 24.0`
* Python `>= 3.11` and `uv`
* Google Cloud SDK (`gcloud`) for Cloud Run deployment

---

## 2. Local Container Build & Run (`backend/Dockerfile`)

The backend `Dockerfile` resides in `backend/Dockerfile` and uses `backend/` as its build context. It sets `ENV SQLITE_DB_PATH=/app/my_agent_data.db` and `ENV QUALITY_DB_PATH=/app/ecommerce_agent.db` with `/app` owned by non-root `appuser:appuser`.

```bash
# Build the backend container image from the repository root
docker build -f backend/Dockerfile -t ecommerce-agent:latest backend

# Run the backend container locally on port 8080
docker run --rm -p 8080:8080 \
  -e GOOGLE_API_KEY="your-gemini-api-key" \
  -e AGENT_MODEL="gemini-3.8-flash" \
  ecommerce-agent:latest
```

Verify container health:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/products/
```

---

## 3. Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | *(Required for live LLM calls)* | Google GenAI API key used by `google-adk` (`Gemini`). |
| `AGENT_MODEL` | `gemini-3.8-flash` | Gemini model identifier used by `CoordinatorAgent` and specialists. |
| `SQLITE_DB_PATH` | `<repo_root>/my_agent_data.db` (`/app/my_agent_data.db` in Docker) | Path to SQLite database for sessions, catalog, orders, and tickets. |
| `QUALITY_DB_PATH` | `<repo_root>/ecommerce_agent.db` (`/app/ecommerce_agent.db` in Docker) | Path to SQLite database for `QualityTracker` telemetry. |
| `API_BASE_URL` | `http://localhost:8000` | Backend base URL consumed by the Streamlit frontend. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8501,http://127.0.0.1:8501` | Comma-separated exact browser origins allowed by CORS. Wildcards are ignored. |

---

## 4. Google Cloud Run Deployment

> **Note on Persistence**: Cloud Run container filesystems are ephemeral across instance restarts, and each instance has its own SQLite files. Keep `--max-instances 1` until the persistence layer is backed by Cloud SQL (PostgreSQL).

> **Note on Access**: The API has no authentication or rate limiting, and every chat turn calls a paid model. Deploy with `--no-allow-unauthenticated` and grant `roles/run.invoker` only to the callers that need it (for example the frontend's service account). Do not expose the service publicly as-is, and delete it when the demo is over.

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Build and deploy backend from the backend/ directory
gcloud run deploy ecommerce-agent-backend \
  --source ./backend \
  --region "$REGION" \
  --platform managed \
  --no-allow-unauthenticated \
  --set-env-vars "AGENT_MODEL=gemini-3.8-flash,SQLITE_DB_PATH=/app/my_agent_data.db,QUALITY_DB_PATH=/app/ecommerce_agent.db" \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1
```
