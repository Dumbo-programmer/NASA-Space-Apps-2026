# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered output for live logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    IGNIS_ALLOWED_ORIGINS="*"

# Install runtime system dependencies (libgomp1 for scikit-learn OpenMP support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create unprivileged system user and group
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/sh -m appuser

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy required application modules and data
COPY api/ ./api/
COPY models/ ./models/
COPY data/ ./data/
COPY tests/ ./tests/

# Set ownership to unprivileged user
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Health check using Python's standard library (no curl/wget dependency)
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the AstraFlame prediction API
CMD ["python", "api/server.py", "--host", "0.0.0.0", "--port", "8000"]

