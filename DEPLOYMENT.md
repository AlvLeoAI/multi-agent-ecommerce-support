# 🚀 Deployment Guide

**Production deployment guide for Multi-Agent E-Commerce Support System**

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Option 1: Cloud Run Deployment](#option-1-cloud-run-deployment-recommended)
- [Option 2: Vertex AI Agent Engine](#option-2-vertex-ai-agent-engine)
- [CI/CD Pipeline Setup](#cicd-pipeline-setup)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Observability](#monitoring--observability)
- [Scaling Strategy](#scaling-strategy)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

---

## Prerequisites

### Required Tools

```bash
# Google Cloud SDK
gcloud --version  # Must be >= 400.0.0

# Docker (for Cloud Run)
docker --version  # Must be >= 20.10.0

# Python
python --version  # Must be >= 3.10
```

### Google Cloud Project Setup

```bash
# 1. Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com

# 3. Create service account for deployment
gcloud iam service-accounts create ecommerce-agent-sa \
    --display-name="E-Commerce Agent Service Account"

# 4. Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:ecommerce-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:ecommerce-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

### Secrets Management

```bash
# Store Google API key securely
echo -n "your-google-api-key" | \
gcloud secrets create GOOGLE_API_KEY \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to service account
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
    --member="serviceAccount:ecommerce-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

---

## Deployment Options

### Comparison Matrix

| Feature | Cloud Run | Vertex AI Agent Engine |
|---------|-----------|------------------------|
| **Setup Complexity** | Low | Medium |
| **Customization** | High | Medium |
| **Auto-scaling** | ✅ Yes | ✅ Yes |
| **Cold Start** | ~2-3s | ~1-2s |
| **Cost** | Pay-per-use | Pay-per-use + storage |
| **Monitoring** | Cloud Logging | Built-in + Cloud Logging |
| **State Management** | Custom (SQLite/Cloud SQL) | Built-in sessions |
| **Best For** | Full control, custom backend | Quick deployment, managed |

---

## Option 1: Cloud Run Deployment (Recommended)

### Architecture

```
User Request → Cloud Load Balancer → Cloud Run Service
                                          ↓
                                     FastAPI Backend
                                          ↓
                                    Agent Coordinator
                                          ↓
                              ┌───────────┼───────────┐
                              ↓           ↓           ↓
                         General     Product    Calculation
                          Agent       Agent        Agent
                              ↓           ↓           ↓
                              └───────────┴───────────┘
                                          ↓
                                    SQLite / Cloud SQL
```

### Step 1: Prepare Application

**Create `Dockerfile`:**

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Create necessary directories
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Update `requirements.txt` (production):**

```txt
# Core framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Google AI
google-cloud-aiplatform==1.38.1
google-generativeai==0.3.1
google-adk==0.1.0

# Database
sqlalchemy==2.0.23

# Monitoring
google-cloud-logging==3.8.0
google-cloud-trace==1.11.3

# Security
python-dotenv==1.0.0

# Performance
gunicorn==21.2.0
```

### Step 2: Build and Test Locally

```bash
# Build Docker image
docker build -t ecommerce-agent:latest .

# Test locally
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="your-api-key" \
  ecommerce-agent:latest

# Test endpoint
curl http://localhost:8080/health
# Expected: {"status": "healthy", "version": "1.0.0"}
```

### Step 3: Deploy to Cloud Run

**Manual deployment:**

```bash
# Set region
export REGION="us-central1"

# Deploy service
gcloud run deploy ecommerce-agent-backend \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --service-account ecommerce-agent-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "PROJECT_ID=$PROJECT_ID" \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300 \
  --concurrency 80

# Get service URL
gcloud run services describe ecommerce-agent-backend \
  --region $REGION \
  --format 'value(status.url)'
```

**Configuration options explained:**

- `--memory 2Gi`: Sufficient for agent + embeddings
- `--cpu 2`: Better performance for LLM calls
- `--min-instances 1`: Eliminates cold starts (costs ~$10/month)
- `--max-instances 10`: Handles ~200 concurrent users
- `--timeout 300`: 5 min timeout for complex queries
- `--concurrency 80`: Requests per instance

### Step 4: Deploy Frontend (Streamlit)

**Create `frontend/Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend code
COPY frontend/ .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Deploy frontend:**

```bash
gcloud run deploy ecommerce-agent-frontend \
  --source ./frontend \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "BACKEND_URL=https://ecommerce-agent-backend-xyz.run.app" \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5
```

---

## Option 2: Vertex AI Agent Engine

### Step 1: Prepare Agent for Deployment

**Create deployment script:**

```python
# deploy_to_agent_engine.py
from vertexai.preview import reasoning_engines
from google.adk.agents import Agent
import vertexai

# Initialize Vertex AI
vertexai.init(
    project="your-project-id",
    location="us-central1"
)

# Define your agent (simplified for deployment)
coordinator = Agent(
    name="customer_support_coordinator",
    instruction="""You are a helpful customer support agent for an e-commerce platform.
    Assist users with product inquiries, order tracking, and general questions.""",
    # ... rest of agent config
)

# Deploy to Agent Engine
deployed_agent = reasoning_engines.ReasoningEngine.create(
    coordinator,
    requirements=["google-adk==0.1.0", "google-generativeai==0.3.1"],
    display_name="ecommerce-support-agent-prod",
    description="Production customer support agent",
    sys_version="3.11"
)

print(f"Agent deployed successfully!")
print(f"Resource name: {deployed_agent.resource_name}")
print(f"Endpoint: {deployed_agent.gca_resource.deployed_model_endpoint}")
```

### Step 2: Execute Deployment

```bash
# Install required packages
pip install google-cloud-aiplatform google-adk

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Deploy
python deploy_to_agent_engine.py
```

### Step 3: Query Deployed Agent

```python
from vertexai.preview import reasoning_engines

# Load deployed agent
agent = reasoning_engines.ReasoningEngine(
    "projects/PROJECT_ID/locations/us-central1/reasoningEngines/AGENT_ID"
)

# Query agent
response = agent.query(
    input="I need help finding a laptop under $1000"
)

print(response['output'])
```

---

## CI/CD Pipeline Setup

### GitHub Actions Workflow

**Create `.github/workflows/deploy.yml`:**

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1
  SERVICE_NAME: ecommerce-agent-backend

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: pytest tests/ -v --cov=backend
      
      - name: Run agent evaluation
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          python scripts/evaluate_agent.py --dataset data/golden_dataset.json

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --source . \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
      
      - name: Run smoke tests
        run: |
          SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
            --region $REGION --format 'value(status.url)')
          
          # Health check
          curl -f $SERVICE_URL/health || exit 1
          
          # Basic functionality test
          curl -f -X POST $SERVICE_URL/api/chat \
            -H "Content-Type: application/json" \
            -d '{"message": "Hello", "session_id": "test-123"}' || exit 1
```

### Cloud Build (Google Cloud Native)

**Create `cloudbuild.yaml`:**

```yaml
steps:
  # Step 1: Run tests
  - name: 'python:3.11'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        pip install pytest
        pytest tests/ -v

  # Step 2: Build container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ecommerce-agent:$COMMIT_SHA', '.']

  # Step 3: Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ecommerce-agent:$COMMIT_SHA']

  # Step 4: Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'ecommerce-agent-backend'
      - '--image=gcr.io/$PROJECT_ID/ecommerce-agent:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/ecommerce-agent:$COMMIT_SHA'

options:
  machineType: 'N1_HIGHCPU_8'
  
timeout: '1200s'
```

**Trigger build:**

```bash
# Create trigger
gcloud builds triggers create github \
  --repo-name=multi-agent-ecommerce \
  --repo-owner=your-github-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## Environment Configuration

### Environment Variables

**Production `.env` (use Secret Manager):**

```bash
# API Keys
GOOGLE_API_KEY=secret:///projects/PROJECT_ID/secrets/GOOGLE_API_KEY

# Project Config
PROJECT_ID=your-project-id
REGION=us-central1
ENVIRONMENT=production

# Database
DATABASE_URL=sqlite:///data/ecommerce.db  # Local
# DATABASE_URL=postgresql://user:pass@host/db  # Cloud SQL

# Agent Configuration
AGENT_MODEL=gemini-2.0-flash-exp
MAX_TOKENS=8192
TEMPERATURE=0.7

# Performance
MAX_CONCURRENT_SESSIONS=100
SESSION_TIMEOUT=3600  # 1 hour

# Monitoring
ENABLE_TRACING=true
LOG_LEVEL=INFO
```

### Load from Secret Manager (Recommended)

```python
# backend/config.py
from google.cloud import secretmanager
import os

def get_secret(secret_id: str) -> str:
    """Fetch secret from Secret Manager"""
    project_id = os.getenv("PROJECT_ID")
    client = secretmanager.SecretManagerServiceClient()
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    
    return response.payload.data.decode("UTF-8")

# Usage
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")
```

---

## Monitoring & Observability

### Cloud Logging Setup

```python
# backend/logging_config.py
import google.cloud.logging
import logging

# Initialize Cloud Logging
client = google.cloud.logging.Client()
client.setup_logging()

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Usage
logger.info("Agent query processed", extra={
    "session_id": session_id,
    "response_time": response_time,
    "agent_used": "product_agent"
})
```

### Custom Metrics Dashboard

```bash
# Create custom dashboard for monitoring
gcloud monitoring dashboards create --config-from-file=- <<EOF
{
  "displayName": "E-Commerce Agent Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Response Latency (P95)",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_DELTA",
                    "crossSeriesReducer": "REDUCE_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
```

### Alerts Configuration

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate Alert" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"'
```

---

## Scaling Strategy

### Autoscaling Configuration

**Cloud Run autoscaling behavior:**

```
┌─────────────────────────────────────────────────────┐
│  Traffic Pattern  │  Instances  │  Response Time    │
├───────────────────┼─────────────┼───────────────────┤
│  0-80 req/min     │  1 (min)    │  2-4s             │
│  80-800 req/min   │  2-10       │  2-5s             │
│  800-1600 req/min │  10-20      │  3-6s             │
│  1600+ req/min    │  20+ (max)  │  Scale or queue   │
└─────────────────────────────────────────────────────┘
```

**Optimize for cost:**

```bash
# Low traffic (< 100 users/day)
--min-instances 0  # Cold starts acceptable
--max-instances 3

# Medium traffic (100-1000 users/day)
--min-instances 1  # Eliminate cold starts
--max-instances 10

# High traffic (1000+ users/day)
--min-instances 2  # Redundancy
--max-instances 50
--cpu-throttling  # Reduce costs during idle
```

### Database Scaling

**Migration path:**

1. **Development**: SQLite (file-based)
2. **Production < 1000 users**: SQLite on persistent disk
3. **Production > 1000 users**: Cloud SQL (PostgreSQL)

**Cloud SQL setup:**

```bash
# Create Cloud SQL instance
gcloud sql instances create ecommerce-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --backup \
  --availability-type=regional

# Create database
gcloud sql databases create ecommerce \
  --instance=ecommerce-db

# Update Cloud Run to use Cloud SQL
gcloud run services update ecommerce-agent-backend \
  --add-cloudsql-instances=PROJECT_ID:us-central1:ecommerce-db \
  --set-env-vars="DATABASE_URL=postgresql+psycopg2://user:pass@/ecommerce?host=/cloudsql/PROJECT_ID:us-central1:ecommerce-db"
```

---

## Troubleshooting

### Common Issues

#### 1. Cold Start Latency

**Symptom**: First request takes 10-15 seconds

**Solution:**
```bash
# Set min-instances to 1
gcloud run services update ecommerce-agent-backend \
  --min-instances 1 \
  --region us-central1
```

#### 2. Memory Exceeded

**Symptom**: Container crashes with "OOMKilled"

**Solution:**
```bash
# Increase memory allocation
gcloud run services update ecommerce-agent-backend \
  --memory 4Gi \
  --region us-central1
```

#### 3. Timeout Errors

**Symptom**: 504 Gateway Timeout after 60s

**Solution:**
```bash
# Increase timeout (max 3600s for Cloud Run)
gcloud run services update ecommerce-agent-backend \
  --timeout 300 \
  --region us-central1
```

#### 4. API Key Not Found

**Symptom**: "GOOGLE_API_KEY environment variable not set"

**Solution:**
```bash
# Verify secret exists
gcloud secrets describe GOOGLE_API_KEY

# Update Cloud Run binding
gcloud run services update ecommerce-agent-backend \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --region us-central1
```

### Debug Commands

```bash
# View logs in real-time
gcloud run services logs tail ecommerce-agent-backend \
  --region us-central1

# Get service details
gcloud run services describe ecommerce-agent-backend \
  --region us-central1

# List all revisions
gcloud run revisions list \
  --service ecommerce-agent-backend \
  --region us-central1

# Rollback to previous revision
gcloud run services update-traffic ecommerce-agent-backend \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

---

## Cost Optimization

### Estimated Monthly Costs (Cloud Run)

```
Low Traffic (< 1000 requests/day):
- Cloud Run: $5-10/month
- Gemini API: $10-20/month
- Total: ~$20/month

Medium Traffic (1000-10000 requests/day):
- Cloud Run: $20-50/month
- Gemini API: $50-150/month
- Cloud SQL: $25/month
- Total: ~$120/month

High Traffic (10000+ requests/day):
- Cloud Run: $100-200/month
- Gemini API: $200-500/month
- Cloud SQL: $50/month
- Total: ~$400/month
```

### Cost Reduction Strategies

```bash
# 1. Use CPU throttling
gcloud run services update ecommerce-agent-backend \
  --cpu-throttling \
  --region us-central1

# 2. Reduce min-instances during off-hours
# Use Cloud Scheduler to scale down at night

# 3. Enable request/response caching
# Implement Redis or Memorystore

# 4. Use cheaper models for simple queries
# Route to gemini-pro-flash instead of gemini-pro
```

---

## Next Steps

### Post-Deployment Checklist

- [ ] Verify health endpoint: `curl https://your-service.run.app/health`
- [ ] Test chat functionality via Postman/cURL
- [ ] Configure custom domain (optional)
- [ ] Set up alerting policies
- [ ] Create monitoring dashboard
- [ ] Document API endpoints
- [ ] Set up backup strategy
- [ ] Configure CORS for frontend
- [ ] Implement rate limiting
- [ ] Enable Cloud Armor (DDoS protection)

### Production Hardening

```bash
# 1. Enable Cloud Armor
gcloud compute security-policies create ecommerce-agent-policy \
  --description="DDoS and bot protection"

# 2. Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy=ecommerce-agent-policy \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60

# 3. Apply to Cloud Run service (via Load Balancer)
# Requires setting up HTTPS Load Balancer
```

---

## Support & Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Agent Engine](https://cloud.google.com/agent-builder/docs/agent-engine)
- [Google ADK GitHub](https://github.com/googleapis/adk-python)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)

---

**Deployment Version**: 1.0.0  
**Last Updated**: November 2024  
**Maintained by**: Alvaro - AI Solutions Engineer