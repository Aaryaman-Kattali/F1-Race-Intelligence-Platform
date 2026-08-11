# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install dependencies into a virtual environment or user directory
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

# Install Java 17 (needed for PySpark) and curl (for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source
COPY . .

# Cloud Run injects PORT (8080 by default); locally this falls back to 8000
# so docker-compose's 8000:8000 mapping keeps working unchanged.
ENV PORT=8000
EXPOSE 8000

# Healthcheck hitting /api/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/api/health" || exit 1

# Shell form so ${PORT} is expanded at runtime; exec so uvicorn is PID 1 and
# receives Cloud Run's SIGTERM directly.
CMD exec uvicorn api.app:app --host 0.0.0.0 --port ${PORT}
