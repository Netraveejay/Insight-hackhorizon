#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."

echo "==> Installing Python dependencies"
cd backend
pip install -e . --quiet
cd ..

echo "==> Building frontend"
cd frontend
npm ci --silent
npm run build
cd ..

echo "==> Copying static assets into backend"
mkdir -p backend/static
cp -r frontend/dist/* backend/static/

echo "==> Replit build complete"
