"""Article CRUD and ingestion endpoints."""
import os

from celery import Celery
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Celery client — the api only *sends* tasks by name; the worker service owns
# the implementations. Broker/backend and routing must match worker/celery_app.py.
celery_client = Celery(
    "paperbridge",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
)
celery_client.conf.task_routes = {
    "app.tasks.ingest_article_task": {"queue": "ingestion"},
    "app.tasks.reindex_all_task": {"queue": "maintenance"},
}


class IngestRequest(BaseModel):
    url: str | None = None
    doi: str | None = None
    query: str | None = None


class ArticleOut(BaseModel):
    id: str
    title: str
    abstract: str | None = None
    authors: list[str] = []
    keywords: list[str] = []
    year: int | None = None
    venue: str | None = None
    citations: int = 0
    url: str | None = None


@router.post("/ingest")
async def ingest(request: IngestRequest):
    """
    Trigger async article ingestion.
    Kicks off a Celery task to scrape → process → index.
    """
    task = celery_client.send_task(
        "app.tasks.ingest_article_task",
        args=[request.model_dump()],
        queue="ingestion",
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Poll Celery task status for async ingestion jobs."""
    result = celery_client.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result}
