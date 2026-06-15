# PaperBridge

> Paste a Google Scholar article or topic — get ranked recommendations for related papers, shown as a ranked list and an interactive citation graph.

PaperBridge combines **BERT-based semantic embeddings** (FAISS approximate nearest neighbor) with **full-text keyword search** (Elasticsearch), fused via **Reciprocal Rank Fusion (RRF)**. Results render in a D3.js force-directed citation graph alongside a ranked list.

---

## How it works

```
User submits a Scholar URL or query text
        │
        ▼
[API: POST /recommendations/]
        │
        ├─► Redis cache hit?  → return cached results
        │
        └─► Cache miss:
              ├─► Embed query (sentence-transformers)
              ├─► FAISS search        → semantic ranked list
              ├─► Elasticsearch search → keyword ranked list
              └─► RRF fusion (k=60)   → top-K results
                                            │
                                            ▼
                              [Frontend: ranked list + citation graph]

Background ingestion (POST /articles/ingest or the Airflow DAG):
[Semantic Scholar API] → [Kafka raw-articles] → [processor: NLP + embed] → [Elasticsearch + FAISS + Postgres]
```

**Why RRF?** FAISS inner-product distances and Elasticsearch BM25 scores live on incomparable scales. RRF ranks rather than scores, so no normalization is needed, and it naturally boosts papers that appear in both result sets.

---

## Architecture

```
PaperBridge/
├── services/
│   ├── scraper/    Python — Semantic Scholar API → Kafka
│   ├── processor/  Python — NLP pipeline → FAISS + Elasticsearch + Postgres
│   ├── api/        Python — FastAPI REST + Strawberry GraphQL + Redis cache
│   └── worker/     Python — Celery async ingestion tasks
├── frontend/       TypeScript — Next.js 14 + D3.js + TailwindCSS
├── airflow/dags/   Python — daily scheduled scraping DAG
├── mlflow/         Python — embedding model evaluation experiments
├── infrastructure/ Postgres schema, Prometheus/OTel config, k8s/Helm
├── docker-compose.yml   All services; optional profiles: airflow, mlflow, monitoring
└── .env.example
```

| Layer | Technology |
|---|---|
| Scraping | Semantic Scholar API (`requests`, `tenacity`) |
| Messaging | Apache Kafka |
| NLP / Embeddings | `sentence-transformers` (all-MiniLM-L6-v2), KeyBERT, spaCy |
| Vector search | FAISS IVFFlat (384-dim, inner product) |
| Full-text search | Elasticsearch 8.13 (BM25) |
| Metadata store | PostgreSQL 16 (SQLAlchemy + Alembic) |
| Object store | MinIO (S3-compatible) |
| API | FastAPI + Strawberry GraphQL |
| Cache | Redis 7 (1h TTL) |
| Async tasks | Celery 5.4 |
| Frontend | Next.js 14, D3.js, TailwindCSS, TanStack Query |
| Observability | Prometheus, Grafana, OpenTelemetry → Jaeger |

---

## Quick start

**Prerequisites:** Docker + Docker Compose. (Frontend-only dev also needs Node 18+.)

```bash
cp .env.example .env          # fill in the required secrets (see below)
docker compose up -d          # postgres, redis, kafka, elasticsearch, api, processor, worker, frontend
docker compose exec api alembic upgrade head   # or: make migrate

# Ingest some articles
make ingest query="attention mechanism transformer"

# Query the API
make recommend query="contrastive learning self-supervised"
```

Then open:

- **Frontend** — http://localhost:3000
- **API docs** — http://localhost:8000/docs
- **GraphQL playground** — http://localhost:8000/graphql

Optional stacks (Docker Compose profiles):

```bash
docker compose --profile airflow up -d      # Airflow at :8080
docker compose --profile mlflow up -d       # MLflow at :5000
docker compose --profile monitoring up -d   # Grafana at :3001
```

### Frontend-only development

The fastest loop for UI work. Needs a reachable API (run `docker compose up -d api postgres redis elasticsearch`, or work against the empty/loading states with no backend).

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000, hot reload
```

Point the frontend at a non-default API with `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> First `npm run dev`/`build` fetches the Inter font from Google Fonts (`next/font`) and needs network access. It's cached afterward.

---

## API reference

```http
POST /api/v1/recommendations/
  Body:   {"query_text": "...", "article_id": "..."}   (one or both)
  Params: ?method=hybrid|semantic|keyword  &top_k=10   (1–50)

GET  /api/v1/recommendations/article/{article_id}

GET  /api/v1/search/?q=transformer&year_from=2020&size=20

POST /api/v1/articles/ingest
  Body: {"url": "...", "doi": "...", "query": "..."}     → {task_id}

GET  /api/v1/articles/task/{task_id}                     # poll Celery task

GET  /api/v1/health                                      # Postgres + Redis check
```

GraphQL (`/graphql`):

```graphql
query {
  recommend(queryText: "contrastive learning", topK: 10, method: "hybrid") {
    article { title authors year keywords citations url }
    score
  }
}
```

---

## Configuration

Copy `.env.example` to `.env` and set values. Required secrets:

| Variable | Notes |
|---|---|
| `POSTGRES_URL` | Full DSN; used by api + processor |
| `API_SECRET_KEY` | JWT signing key — `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Object store credentials |
| `AIRFLOW_FERNET_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `AIRFLOW_SECRET_KEY` | Airflow webserver session key |

Common tunables (with defaults):

| Variable | Default | Notes |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | API cache |
| `ELASTICSEARCH_URL` | `http://elasticsearch:9200` | Full-text search |
| `FAISS_INDEX_PATH` | `/data/faiss/articles.index` | Shared Docker volume |
| `FAISS_DIMENSION` | `384` | Must match embedding model output |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Scraper → processor |
| `SEMANTIC_SCHOLAR_API_KEY` | *(optional)* | Lifts Semantic Scholar rate limit |
| `REQUEST_DELAY_SECONDS` | `1` | Delay between API pages |
| `API_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

See `.env.example` for the full list.

---

## Development

```bash
make test          # pytest all services
make lint          # ruff check
make format        # ruff format
make typecheck     # mypy api + processor
make migrate       # alembic upgrade head (inside api container)
make build         # docker compose build --parallel
make clean         # docker compose down -v + clean pycache
```

Frontend:

```bash
cd frontend
npm run lint
npm run type-check
npm run build
```

For deeper architecture notes, per-service internals, and design decisions, see [CLAUDE.md](CLAUDE.md). Product/design intent lives in [PRODUCT.md](PRODUCT.md).

---

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md). Never commit a real `.env` — only `.env.example` is tracked.

---

## License

See [LICENSE](LICENSE) if present; otherwise the project is currently unlicensed (all rights reserved).
```

