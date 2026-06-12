from fastapi import APIRouter
from sqlalchemy import text
from app.db.session import SessionLocal
from app.config import settings
import redis

router = APIRouter()


@router.get("/health")
async def health():
    status = {"api": "ok", "postgres": "unknown", "redis": "unknown", "elasticsearch": "unknown"}

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = str(e)

    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = str(e)

    return status
