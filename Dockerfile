# Multi-stage dockerfile for Google Cloud Run
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY backend/ ./backend/

# Create non-root user for security (Cloud Run best practice)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Add local python packages to path
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (Cloud Run requires 8000 or a custom port via PORT env var)
EXPOSE 8000

# Set environment
ENV ENVIRONMENT=production

# Health check (Cloud Run best practice)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

# Run the application with graceful shutdown
CMD ["python", "-m", "uvicorn", \
     "backend.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "${PORT:-8000}", \
     "--workers", "4", \
     "--timeout-keep-alive", "30", \
     "--access-log"]

