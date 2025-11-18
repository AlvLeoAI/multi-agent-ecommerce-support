# Use Python 3.11 (more stable than 3.13 for Google ADK)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Google ADK first - let it resolve its own dependencies
RUN pip install --no-cache-dir git+https://github.com/google/adk-python.git

# Install remaining dependencies, allowing pip to resolve conflicts
RUN pip install --no-cache-dir \
    python-dotenv==1.0.1 \
    google-genai \
    google-cloud-aiplatform \
    pandas \
    numpy

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the application with uvicorn (already installed by google-adk)
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}