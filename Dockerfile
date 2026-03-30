# Lazy-Bird v2.0 API and Worker Image
# =====================================
# Multi-stage build for optimized production image

# Build stage
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source and install package
COPY pyproject.toml .
COPY README.md .
COPY lazy_bird/ ./lazy_bird/
RUN pip install --no-cache-dir --no-deps .

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY lazy_bird/ ./lazy_bird/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash lazy_bird && \
    chown -R lazy_bird:lazy_bird /app && \
    mkdir -p /var/lib/lazy_bird/repos && \
    chown -R lazy_bird:lazy_bird /var/lib/lazy_bird

# Switch to non-root user
USER lazy_bird

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/lazy_bird/.local/bin:$PATH"

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command (can be overridden)
CMD ["uvicorn", "lazy_bird.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
