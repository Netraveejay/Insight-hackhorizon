# ── Stage 1: React production build ──────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin API — backend serves /api/*
ENV VITE_API_URL=
RUN npm run build

# ── Stage 2: Python API + static assets ────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

COPY rules /app/rules
COPY --from=frontend-build /app/dist ./static

RUN mkdir -p /app/data/reports /app/data/inbound

ENV PYTHONPATH=/app/backend
ENV RULES_PATH=/app/rules/rules.v1.yaml
ENV DATABASE_URL=sqlite:////app/data/insight.db
ENV REPORTS_DIR=/app/data/reports
ENV FEEDBACK_FILE_PATH=
ENV AUTO_SEED=true
ENV ENABLE_SCHEDULER=true
ENV CORS_ORIGINS=http://localhost:8080
ENV AUTH_SECRET=change-me-in-production

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
