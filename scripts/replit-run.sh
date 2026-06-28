#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."

# First run on a fresh Repl: build if static assets missing
if [ ! -f backend/static/index.html ]; then
  sh scripts/replit-build.sh
fi

mkdir -p data/reports data/inbound

export PORT="${PORT:-8080}"
export PYTHONPATH="${PWD}/backend"
export RULES_PATH="${RULES_PATH:-${PWD}/rules/rules.v1.yaml}"
export DATABASE_URL="${DATABASE_URL:-sqlite:////${PWD}/data/insight.db}"
export REPORTS_DIR="${REPORTS_DIR:-${PWD}/data/reports}"
export AUTO_SEED="${AUTO_SEED:-true}"
export ENABLE_SCHEDULER="${ENABLE_SCHEDULER:-true}"

# Replit public URL — set in Secrets if you use a custom domain
if [ -n "$REPLIT_DEV_DOMAIN" ]; then
  export CORS_ORIGINS="https://${REPLIT_DEV_DOMAIN}"
else
  export CORS_ORIGINS="${CORS_ORIGINS:-*}"
fi

echo "==> Starting Insight on port ${PORT}"
cd backend
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
