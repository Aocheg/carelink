# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

LABEL maintainer="Aocheg <carelink-project>"
LABEL description="CareLink Clinical Continuity & Care Coordination Platform"

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install runtime system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged system user and group for security
RUN groupadd --system --gid 10001 carelink \
    && useradd --system --uid 10001 --gid carelink --shell /bin/bash --create-home carelink

# Set working directory
WORKDIR /app

# Install Python dependencies first to maximize build layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application source code and configuration
COPY . /app/

# Ensure entrypoint script is executable and set proper ownership
RUN chmod +x /app/docker-entrypoint.sh \
    && chown -R carelink:carelink /app

# Switch to non-root user
USER carelink

# Expose HTTP port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint manages DB readiness, migrations, and seeding
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default server startup command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
