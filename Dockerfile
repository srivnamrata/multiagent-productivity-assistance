# ============================================================
# Stage 1 — Builder
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================
# Stage 2 — Runtime
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Runtime OS packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Cloud Run best practice)
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --chown=appuser:appuser --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser backend/ ./backend/
USER appuser

# Environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app:/app/backend

# Cloud Run uses dynamic $PORT — default = 8080
EXPOSE 8080
ENV PORT=8080
ENV ENVIRONMENT=production

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import os,urllib.request; port=os.getenv('PORT','8080'); urllib.request.urlopen('http://localhost:'+port+'/health')" || exit 1

# ============================================================
# ✅ Correct Cloud Run startup command using Docker's shell form
# This guarantees $PORT is expanded correctly by the shell
# ============================================================
CMD exec python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port "${PORT:-8080}" --workers 1 --timeout-keep-alive 30 --access-log