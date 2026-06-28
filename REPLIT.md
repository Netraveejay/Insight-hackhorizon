# Deploy Insight on Replit

## 1. Import from GitHub

1. Open [replit.com](https://replit.com) → **Create Repl** → **Import from GitHub**
2. Paste your repo URL (e.g. `https://github.com/YOUR_USER/guest-feedback-analysis`)
3. Set the **root directory** to the repo root (the folder containing `Makefile`, `Dockerfile`, `frontend/`, `backend/`)

## 2. Replit Secrets (Tools → Secrets)

| Secret | Value |
|--------|--------|
| `AUTH_SECRET` | Long random string (required for production) |
| `OPENAI_API_KEY` | Optional — enables AI chatbot |
| `TEAMS_WEBHOOK_URL` | Optional — Teams alerts |

Replit sets `REPLIT_DEV_DOMAIN` automatically; the start script uses it for CORS.

## 3. Run

Click **Run** (or use the **Start Insight** workflow). Replit will:

1. `pip install` backend dependencies  
2. `npm ci && npm run build` frontend  
3. Copy `frontend/dist` → `backend/static`  
4. Start FastAPI on port **8080** (mapped to the public URL)

## 4. First login

- **HQ:** `admin` / `insight2026`  
- **Site manager:** `harbourview` / `site2026`

Demo data seeds automatically on first start (`AUTO_SEED=true`).

## 5. Deploy (always-on URL)

1. Open the **Deployment** tab in Replit  
2. Choose **Autoscale** or **Reserved VM**  
3. Build command: `sh scripts/replit-build.sh`  
4. Run command: `sh scripts/replit-run.sh`  

After deploy, open the `.replit.app` URL — API and UI are same-origin (`/api/*`).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Blank page | Re-run `sh scripts/replit-build.sh` |
| 401 on login | Set `AUTH_SECRET` in Secrets and restart |
| No issues/data | Wait for seed (~30s) or run pipeline from Agent Network |
| Chat always offline | Add `OPENAI_API_KEY` in Secrets |

## Local vs Replit

| | Local (`make dev`) | Replit |
|--|-------------------|--------|
| Frontend | `:5173` (Vite proxy) | Served by FastAPI `/` |
| Backend | `:8000` | `:8080` |
| Database | `backend/*.db` | `data/insight.db` in Repl |
