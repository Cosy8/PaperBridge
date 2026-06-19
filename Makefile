.PHONY: up down build logs test lint format clean

# ── Docker ──────────────────────────────────────────────────────
up:
	docker compose up -d

up-full:
	docker compose --profile airflow --profile mlflow --profile monitoring up -d

down:
	docker compose --profile airflow --profile mlflow --profile monitoring down

build:
	docker compose build --parallel

logs:
	docker compose logs -f $(service)

ps:
	docker compose ps

# ── Development ─────────────────────────────────────────────────
install:
	pip install -r services/api/requirements.txt
	pip install -r services/processor/requirements.txt
	pip install -r services/scraper/requirements.txt
	pip install -r services/worker/requirements.txt

test:
	pytest services/ -v --tb=short

test-cov:
	pytest services/ --cov --cov-report=html
	open htmlcov/index.html

lint:
	ruff check services/

format:
	ruff format services/

typecheck:
	mypy services/api/app services/processor/app --ignore-missing-imports

# ── Data ────────────────────────────────────────────────────────
ingest:
	curl -s -X POST http://localhost:8000/api/v1/articles/ingest \
	  -H 'Content-Type: application/json' \
	  -d '{"query": "$(query)"}'

search:
	curl -s "http://localhost:8000/api/v1/search/?q=$(q)" | python -m json.tool

recommend:
	curl -s -X POST http://localhost:8000/api/v1/recommendations/ \
	  -H 'Content-Type: application/json' \
	  -d '{"query_text": "$(query)"}' | python -m json.tool

# ── MLflow ──────────────────────────────────────────────────────
mlflow-experiments:
	docker compose --profile mlflow up -d mlflow
	docker compose exec mlflow python /mlflow/run_experiments.py

# ── Cleanup ─────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
