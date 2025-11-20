# ---------------------------
# Stage 1: Builder (Compilation)
# ---------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# We installed git and the necessary compilation tools (gcc) for some libraries.
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# We copy and compile the dependencies
COPY requirements.txt .
# We installed it in a local path (--user) to make copying easier later
RUN pip install --user --no-cache-dir -r requirements.txt

# ---------------------------
# Stage 2: Runner (Light Running)
# ---------------------------
FROM python:3.11-slim

WORKDIR /app

# We copy the libraries installed from the 'builder' stage
# This leaves behind 'git', 'gcc', and all the compilation junk
COPY --from=builder /root/.local /root/.local

# We ensure that Python finds the libraries
ENV PATH=/root/.local/bin:$PATH

# We copy the source code
COPY . .

# Environment Configuration
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Security: Create a non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# We are showcasing the port
EXPOSE 8080

# Professional startup command (Gunicorn + Uvicorn)
# We use main:app because the Dockerfile is inside backend/
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0"]
