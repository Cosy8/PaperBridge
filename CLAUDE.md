# PaperBridge — Developer Reference

PaperBridge takes a query (free-text topic or an existing article ID) and returns ranked recommendations for related papers. Article metadata is sourced from the **Semantic Scholar Graph API** (not by scraping Google Scholar). It uses a hybrid ranking system combining BERT-based semantic embeddings (FAISS ANN) with full-text keyword search (Elasticsearch), fused via Reciprocal Rank Fusion (RRF). Results are displayed in an interactive D3.js citation graph.

---

## Project Structure

```
PaperBridge/
├── services/
│   ├── scraper/        Python — Semantic Scholar API → Kafka
│   ├── processor/      Python — NLP pipeline → FAISS + Elasticsearch + Postgres
│   ├── api/            Python — FastAPI REST + Strawberry GraphQL + Redis cache
│   └── worker/         Python — Celery async ingestion tasks
├── frontend/           TypeScript — Next.js 14 + D3.js + TailwindCSS
├── airflow/dags/       Python — daily scheduled scraping DAG
├── mlflow/             Python — embedding model evaluation experiments
├── infrastructure/
│   ├── postgres/       init.sql schema (articles, recommendations, search_queries)
│   └── monitoring/     prometheus.yml, otel-collector.yml
├── .github/workflows/  GitHub Actions CI (per-service ruff lint + pytest; mypy soft)
├── docker-compose.yml  All services; optional profiles: airflow, mlflow, monitoring
├── Makefile            Common dev commands
├── pyproject.toml      ruff + mypy + pytest config
└── .env.example        All required environment variables
```

---

## Services

### scraper (`services/scraper/`)
- Queries the **Semantic Scholar Graph API** (`/graph/v1/paper/search`) over HTTP — official, documented API; no browser engine, no Google Scholar scraping, no proxy/Tor
- Publishes raw article dicts to Kafka topic `raw-articles`
- Paginates via the API cursor up to `MAX_RESULTS_PER_QUERY`, sleeping `REQUEST_DELAY_SECONDS` between pages; optional `SEMANTIC_SCHOLAR_API_KEY` lifts the rate limit
- Entry point: `app/main.py` — reads queries from the `SEED_QUERIES` env var (comma-separated; **empty by default** — no baked-in seed data), calls `fetch_articles()`, publishes via `publish_raw_article()`. Exits with a warning if no queries are configured
- Key files: `semantic_scholar.py` (API client), `producer.py` (Kafka), `config.py`

### processor (`services/processor/`)
- Kafka consumer: reads `raw-articles`, runs NLP pipeline, writes to ES + FAISS + Postgres
- NLP pipeline (`nlp_pipeline.py`):
  - `extract_keywords()` — KeyBERT with MMR diversity, top-10 keyphrases
  - `extract_entities()` — spaCy `en_core_web_sm` NER
  - `generate_embedding()` — `all-MiniLM-L6-v2` via sentence-transformers, 384-dim normalized float32
  - `process_article()` — runs all three, returns augmented dict
- FAISS index (`vector_index.py`): `IndexIVFFlat` with `n_list=100`, `nprobe=10`; persisted to `/data/faiss/articles.index`
- ES indexer (`es_indexer.py`): creates `articles` index with English analyzer; excludes embedding vectors from ES docs
- Key files: `main.py`, `nlp_pipeline.py`, `vector_index.py`, `es_indexer.py`, `config.py`

### api (`services/api/`)
- FastAPI app with CORS, Prometheus instrumentation via `prometheus-fastapi-instrumentator`
- Routers mounted at `/api/v1/`:
  - `GET /health` — checks Postgres, Redis connectivity
  - `POST /articles/ingest` — queues a Celery ingestion task, returns `{task_id}`
  - `GET /articles/task/{task_id}` — polls Celery task status
  - `POST /recommendations/` — main endpoint; params: `top_k` (1–50), `method` (hybrid|semantic|keyword)
  - `GET /recommendations/article/{article_id}` — recommendations by existing article ID
  - `GET /search/` — ES full-text search; params: `q`, `size`, `year_from`, `year_to`
- `GET /graphql` — Strawberry GraphQL playground; `recommend` query mirrors REST endpoint
- Recommender (`services/recommender.py`):
  - Semantic: embeds query with `all-MiniLM-L6-v2`, searches FAISS
  - Keyword: multi-match ES query on title^3, abstract^2, keywords^2
  - Hybrid: RRF fusion with `k=60`; score formula: `Σ 1/(60 + rank)`
- Redis cache: key = `MD5(request_json + top_k + method)`, TTL = 1 hour
- DB models (`models/article.py`): `Article`, `Recommendation`, `SearchQuery` — SQLAlchemy ORM, UUID PKs
- Key files: `main.py`, `services/recommender.py`, `routers/recommendations.py`, `vector_index.py`

### worker (`services/worker/`)
- Celery app backed by Redis broker (`redis://redis:6379/1`) and result backend (`redis://redis:6379/2`)
- Task routes: `ingest_article_task` → queue `ingestion`; `reindex_all_task` → queue `maintenance`
- `ingest_article_task`: fetch from Semantic Scholar (exact `/paper/DOI:<doi>` lookup if a `doi` is given, else first hit from `/paper/search` on `query`) → `process_article()` → ES index → FAISS add; retries 3×. **Note:** the `url` field of the ingest request is currently ignored — only `doi` and `query` are resolved
- `reindex_all_task`: stub for full FAISS rebuild from ES (scroll all docs, re-embed)
- Key files: `celery_app.py`, `tasks.py`, `semantic_scholar.py` (S2 API client), `config.py`

### frontend (`frontend/`)
- Next.js 14 App Router, TailwindCSS dark theme (`slate-950` background, `emerald-400` accent)
- `page.tsx`: search bar with method selector (Hybrid/Semantic/Keyword), results list, article detail panel
- `CitationGraph.tsx`: D3 force-directed graph; query node (amber) at center, paper nodes (emerald) sized by citation count, opacity ring scaled by similarity score; draggable nodes
- Data fetching: TanStack Query (`useQuery`) — caches per `[query, method]`
- API call: `POST /api/v1/recommendations/` with `{query_text}` + `?method=&top_k=15`

---

## Data Flow

```
User submits query text (or an existing article ID)
        │
        ▼
[API: POST /recommendations/]
        │
        ├─► Redis cache hit? → return cached results
        │
        └─► Cache miss:
              ├─► Embed query (sentence-transformers)
              ├─► FAISS search → semantic ranked list
              ├─► ES multi_match search → keyword ranked list
              └─► RRF fusion → fetch ES metadata → return top-K
                                                        │
                                                        ▼
                                              [Frontend: CitationGraph + Results list]

Background ingestion (triggered via POST /articles/ingest or Airflow DAG):
[Semantic Scholar API] → [Kafka raw-articles] → [processor: NLP + embed] → [ES + FAISS + Postgres]
```

---

## Quick Start

```bash
cp .env.example .env
docker compose up -d
# Postgres schema is auto-created on first boot from
# infrastructure/postgres/init.sql (mounted into docker-entrypoint-initdb.d).

# Ingest some articles
make ingest query="attention mechanism transformer"

# Query the API
make recommend query="contrastive learning self-supervised"

# Frontend
open http://localhost:3000
```

Optional stacks:
```bash
docker compose --profile airflow up -d      # Airflow at :8080
docker compose --profile mlflow up -d       # MLflow at :5000
docker compose --profile monitoring up -d   # Grafana at :3001
```

---

## Docker Image Optimization

The Python service images were ~9 GB each. They are now ~2.3–2.65 GB (scraper ~490 MB), a ~70% reduction. Measured `:opt` builds:

| Image | Before | After |
|---|---|---|
| worker | ~9 GB | 2.65 GB |
| processor | ~9 GB | 2.48 GB |
| api | ~9 GB | 2.31 GB |
| scraper | ~1.5 GB | 489 MB |

**What changed (all four `services/*/Dockerfile`):**
- **Multi-stage build** — `build-essential` and pip downloads live only in the `builder` stage; the `runtime` stage copies just the `/opt/venv` virtualenv, so the compiler toolchain never ships.
- **CPU-only torch** — `sentence-transformers` (api, processor, worker) otherwise pulls the default CUDA `torch` (~5 GB of `nvidia-*` wheels). Each Dockerfile installs `torch==2.2.2` from `https://download.pytorch.org/whl/cpu` **before** `requirements.txt`, so the CUDA build is never fetched. This was the bulk of the bloat.
- **BuildKit pip cache mount** (`--mount=type=cache,target=/root/.cache/pip`) — caches downloads across rebuilds without adding to the image layer. Requires BuildKit (default in modern Docker Desktop and GitHub Actions).
- **Dead deps removed** — processor: `mlflow` (it's a standalone service, never imported); scraper: `playwright`, `scrapy`, `boto3`, `bdfparser`, apt `chromium`/`chromium-driver` (none imported — the Semantic Scholar API is a plain HTTP call); worker: `playwright`, `flower`.

**docker-compose.yml** — `model_cache` volume now mounted on `api` and `worker` (not just `processor`) so the `all-MiniLM-L6-v2` weights aren't re-downloaded on every container start; `worker` also gained the shared `faiss_data` volume so its FAISS writes land on the same index as `api`/`processor`.

> If a build fails with a `--mount` parse error, BuildKit is disabled — run with `DOCKER_BUILDKIT=1 docker build ...` (or use `docker buildx`).
> If a browser-based data source is ever needed (e.g. a `playwright`/Selenium scraper), restore the browser stack in `services/scraper/requirements.txt` and the Dockerfile.

---

## API Reference

```http
POST /api/v1/recommendations/
  Body: {"query_text": "...", "article_id": "..."}   (one or both)
  Params: ?method=hybrid|semantic|keyword  &top_k=10

GET  /api/v1/search/?q=transformer&year_from=2020&size=20

POST /api/v1/articles/ingest
  Body: {"doi": "...", "query": "..."}   (worker resolves by doi first, else query)
  Note: `url` is accepted by the API schema but ignored by the worker

GET  /api/v1/articles/task/{task_id}

GET  /api/v1/health
```

GraphQL playground at `/graphql`:
```graphql
query {
  recommend(queryText: "contrastive learning", topK: 10, method: "hybrid") {
    article { title authors year keywords citations url }
    score
  }
}
```

---

## Environment Variables (key ones)

| Variable | Default | Notes |
|---|---|---|
| `POSTGRES_URL` | *(required)* | Full DSN; used by api + processor via `SecretStr` |
| `API_SECRET_KEY` | *(required)* | JWT signing key; generate with `secrets.token_hex(32)` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | *(required)* | Object store credentials |
| `AIRFLOW_FERNET_KEY` | *(required)* | Generate with `Fernet.generate_key()` |
| `AIRFLOW_SECRET_KEY` | *(required)* | Airflow webserver session key |
| `REDIS_URL` | `redis://redis:6379/0` | API cache |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Worker task queue |
| `ELASTICSEARCH_URL` | `http://elasticsearch:9200` | Full-text search |
| `ELASTICSEARCH_INDEX` | `articles` | ES index name |
| `FAISS_INDEX_PATH` | `/data/faiss/articles.index` | Shared Docker volume |
| `FAISS_DIMENSION` | `384` | Must match embedding model output |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Scraper → processor |
| `SEMANTIC_SCHOLAR_API_KEY` | *(optional)* | Lifts Semantic Scholar rate limit |
| `MAX_RESULTS_PER_QUERY` | `20` | Max articles fetched per seed query |
| `REQUEST_DELAY_SECONDS` | `1` | Delay between Semantic Scholar API pages |
| `SEED_QUERIES` | *(empty)* | Comma-separated queries for scraper + Airflow DAG; empty = ingest nothing |
| `API_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

---

## Development Commands

```bash
make test          # pytest all services
make lint          # ruff check
make format        # ruff format
make typecheck     # mypy api + processor
make build         # docker compose build --parallel
make clean         # docker compose down -v + clean pycache
```

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Scraping | Semantic Scholar Graph API (`requests`, `tenacity`) |
| Messaging | Apache Kafka (Confluent 7.6) |
| Orchestration | Apache Airflow 2.9 |
| NLP / Embeddings | `sentence-transformers` (all-MiniLM-L6-v2), `KeyBERT`, `spaCy` |
| Vector search | FAISS IVFFlat (384-dim, inner product) |
| Full-text search | Elasticsearch 8.13 (BM25, English analyzer) |
| Metadata store | PostgreSQL 16 (SQLAlchemy ORM; schema from init.sql) |
| Object store | MinIO (S3-compatible; raw HTML, model artifacts) |
| Ranking | Reciprocal Rank Fusion (k=60) |
| API | FastAPI 0.111 + Strawberry GraphQL |
| Cache | Redis 7 (1hr TTL, MD5 cache keys) |
| Async tasks | Celery 5.4 |
| Experiment tracking | MLflow 2.12 |
| Frontend | Next.js 14, D3.js, TailwindCSS, TanStack Query |
| Observability | Prometheus, Grafana, OpenTelemetry (OTLP → Jaeger) |
| CI | GitHub Actions (per-service ruff + pytest) |

---

## Key Design Decisions

**Why RRF over score normalization?** FAISS returns inner-product distances and ES returns BM25 scores — these are incomparable scales. RRF operates on ranks rather than scores, so no normalization is needed. It also naturally boosts documents that appear in both result sets.

**Why FAISS IVFFlat over pgvector?** At 1M+ vectors, IVFFlat is 10–100× faster per query. pgvector is the right choice below ~100k vectors.

**Why Kafka between scraper and processor?** The scraper is I/O-bound (Semantic Scholar's keyless pool is ~1 req/sec, shared globally; an API key raises this). The processor can handle ~200 articles/second. Kafka decouples them and enables replayability — if the embedding model changes, re-process all messages from offset 0.

**Why Redis cache with MD5 key?** Recommendations are deterministic for a given (query, top_k, method) tuple. The corpus changes slowly, so a 1-hour TTL is appropriate. Cache invalidation on article deletion happens naturally via TTL expiry.

**FAISS index persistence:** The index is saved to a shared Docker volume (`faiss_data`) after every write. Multiple API replicas load the same file at startup. At larger scale, migrate to a dedicated vector DB (Milvus, Weaviate).
