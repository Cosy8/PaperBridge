"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doi = Column(String, unique=True, nullable=True, index=True)
    scholar_id = Column(String, unique=True, nullable=True, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    authors = Column(JSON, default=list)
    keywords = Column(JSON, default=list)
    entities = Column(JSON, default=list)
    year = Column(Integer, nullable=True)
    venue = Column(String, nullable=True)
    citations = Column(Integer, default=0)
    url = Column(String, nullable=True)
    embedding_path = Column(String, nullable=True)  # MinIO path
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recommendation_sources = relationship("Recommendation", foreign_keys="Recommendation.source_id", back_populates="source")
    recommendation_targets = relationship("Recommendation", foreign_keys="Recommendation.target_id", back_populates="target")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    score = Column(Float, nullable=False)
    method = Column(String, default="semantic")  # semantic | keyword | hybrid
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Article", foreign_keys=[source_id], back_populates="recommendation_sources")
    target = relationship("Article", foreign_keys=[target_id], back_populates="recommendation_targets")


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    result_count = Column(Integer, default=0)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
