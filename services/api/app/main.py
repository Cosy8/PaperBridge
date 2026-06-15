"""
PaperBridge FastAPI application.
Provides REST and GraphQL endpoints for article recommendations.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.db import models
from app.db.session import engine
from app.graphql_schema import graphql_router
from app.routers import articles, health, recommendations, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PaperBridge API...")
    models.Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down PaperBridge API...")


app = FastAPI(
    title="PaperBridge API",
    description="Ranked academic paper recommendations from Google Scholar",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(articles.router, prefix="/api/v1/articles", tags=["articles"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(graphql_router, prefix="/graphql")


@app.get("/")
async def root():
    return {"service": "PaperBridge API", "version": "1.0.0", "docs": "/docs"}
