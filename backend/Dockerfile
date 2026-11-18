# ---------------------------
# Stage 1: Builder (Compilation)
# ---------------------------
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---------------------------
# Stage 2: Runner (Light Running)
# ---------------------------
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV SQLITE_DB_PATH=/app/my_agent_data.db
ENV QUALITY_DB_PATH=/app/ecommerce_agent.db

# Security: Create non-root user with writable /app ownership for SQLite WAL/journal files
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0"]
