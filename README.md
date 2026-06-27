# Insight — Guest Feedback Intelligence

Multi-site cinema operations feedback intelligence. **Inform, not act** — internal recommendations only. Fictional site names for demo.

## Deploy in 2 minutes (production)

```bash
cd insight
cp .env.example .env          # edit AUTH_SECRET before public deploy
make deploy                   # builds Docker image, starts on :8080
```

Open **http://localhost:8080** → login **admin** / **insight2026**

| Role | Username | Password |
|------|----------|----------|
| HQ (all sites) | `admin` | `insight2026` |
| Harbourview manager | `harbourview` | `site2026` |
| Northgate manager | `northgate` | `site2026` |

Data persists in Docker volume `insight-data` (SQLite DB + reports).

### Production checklist

1. Set `AUTH_SECRET` in `.env` (long random string)
2. Set `AUTO_SEED=false` when using real data
3. Place feedback JSON at `FEEDBACK_FILE_PATH` (see Pipeline page → go-live notes)
4. Optional: `TEAMS_WEBHOOK_URL`, `OPENAI_API_KEY`
5. `make deploy`

```bash
make logs-prod      # follow logs
make docker-prod-down
```

---

## Local development

```bash
make install
make seed
make dev
```

- **Frontend:** http://localhost:5173 (proxies `/api` → backend)
- **API docs:** http://localhost:8000/docs

---

## Product features

| View | Purpose |
|------|---------|
| **Pipeline Run** | Trigger full agent chain + explainability narrative |
| **Overview** | National command centre, hero issue, ranked actions |
| **Live Feed** | All feedback with pipeline funnel stats |
| **Issues** | P1–P3 issues with full evidence & audit trail |
| **Manager Reports** | Download HTML site + executive digest |
| **Teams Alerts** | Operations alert inbox (Teams webhook optional) |
| **Rules Engine** | Adjust weights, rescore |
| **Ask Insight** | Natural language Q&A over processed data |

## Pipeline

```
ingest → translate → score → cluster → detect → insight → output → explain
```

| Agent | Type |
|-------|------|
| Ingestion | Deterministic — dedupe, spam, PII |
| Translation | Model-backed — multilingual → English |
| Scoring | Deterministic — themes, sentiment |
| Clustering | Deterministic — site × theme × week |
| Detection | Deterministic — spike, compounding, cross-source |
| Insight | LLM or template — draft recommendations |
| Output | Reports, Teams alerts, digests |
| Explainability | Plain-language pipeline narrative |

## Real data (not mock)

1. Export feedback as JSON (same schema as `backend/app/seed/data/feedback.json`)
2. In `.env`: `FEEDBACK_FILE_PATH=/app/data/inbound/feedback.json`
3. Copy file into Docker volume or mount
4. `AUTO_SEED=false` → re-run pipeline

M365 inbox / Google reviews connectors are stubbed for phase 2.

## Commands

| Command | Description |
|---------|-------------|
| `make deploy` | Production Docker deploy (:8080) |
| `make dev` | Local backend + frontend |
| `make seed` | Regenerate synthetic data + pipeline |
| `make test` | Run pytest (15 tests) |
| `make build-prod` | Build frontend into `backend/static` |

## Architecture

- **Backend:** FastAPI, SQLAlchemy, SQLite (or Postgres)
- **Frontend:** React, Vite, Tailwind
- **Rules:** `rules/rules.v1.yaml` (business-owned)
- **Auth:** Session tokens (demo users in `app/auth.py`)

## 21 fictional sites

Harbourview, Northgate, Riverside, Eastfield, Parkland, Westgate, Lakeside, Hillcrest, Southbank, Cityplaza, Greenwood, Baytown, Fairmont, Oakridge, Sunset, Meadowbrook, Kingsway, Pinehurst, Crestwood, Maplewood, Brookside

## Demo narrative (seed data)

- **Hero:** Harbourview projection quality — P1 cross-source compounding
- **Secondary:** Northgate ticketing queue
- **Multilingual:** ES, ZH, FR, HI, AR reviews translated
- **Spam:** Southbank review bomb filtered

## Principles

1. No guest-facing output
2. Deterministic scoring; LLM drafts insights only
3. Full audit lineage
4. Internal distribution only
