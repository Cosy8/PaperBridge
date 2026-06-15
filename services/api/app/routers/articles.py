"""Article CRUD and ingestion endpoints."""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()


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
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Trigger async article ingestion.
    Kicks off a Celery task to scrape → process → index.
    """
    from app.worker.tasks import ingest_article_task
    task = ingest_article_task.delay(request.model_dump())
    return {"task_id": task.id, "status": "queued"}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Poll Celery task status for async ingestion jobs."""
    from app.worker.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result}
