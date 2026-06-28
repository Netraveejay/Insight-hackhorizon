.PHONY: dev seed test backend frontend docker-up docker-down install deploy build-prod docker-prod logs-prod

dev:
	@echo "Starting backend and frontend..."
	$(MAKE) -j2 backend frontend

backend:
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

seed:
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/python -m app.seed.generate
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/python -m app.seed.load

test:
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/pytest -v

test-unit:
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/pytest -v -m "not integration and not e2e"

test-integration:
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/pytest -v -m integration

test-e2e:
	cd backend && RULES_PATH=../rules/rules.v1.yaml .venv/bin/pytest -v -m e2e

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

build-prod:
	cd frontend && npm run build
	cp -r frontend/dist backend/static 2>/dev/null || mkdir -p backend/static && cp -r frontend/dist/* backend/static/

deploy: docker-prod

docker-prod:
	@test -f .env || cp .env.example .env
	docker compose -f docker-compose.prod.yml up -d --build
	@echo ""
	@echo "Insight is starting at http://localhost:$${PORT:-8080}"
	@echo "Login: admin / insight2026"
	@echo "Logs: make logs-prod"

logs-prod:
	docker compose -f docker-compose.prod.yml logs -f insight

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-prod-down:
	docker compose -f docker-compose.prod.yml down
