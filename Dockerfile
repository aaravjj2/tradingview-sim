# Multi-stage Dockerfile for Supergraph Pro
# Builds both API (Python) and Frontend (React) services

# ==================== FRONTEND BUILD ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY frontend/ ./

# Build for production
RUN npm run build

# ==================== API IMAGE ====================
FROM python:3.12-slim AS api

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy API requirements
COPY api/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source
COPY api/ ./

# Copy frontend build for static serving (optional)
COPY --from=frontend-builder /app/frontend/dist ./static

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

# Start API server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
