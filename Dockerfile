# Multi-stage build for NotebookLM API server
# Optimized for Railway deployment

# Stage 1: Build stage
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files (including SKILL.md and AGENTS.md required by build)
WORKDIR /app
COPY pyproject.toml README.md SKILL.md AGENTS.md ./
COPY src/ src/

# Install dependencies
# Use regular install (not editable) for production
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[web]"

# Stage 2: Runtime stage
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN useradd -m -u 1000 appuser
WORKDIR /app
RUN chown appuser:appuser /app
USER appuser

# Expose port (Railway auto-detects this)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Start server
# Railway sets PORT environment variable
CMD uvicorn notebooklm.server:app --host 0.0.0.0 --port ${PORT:-8000}
