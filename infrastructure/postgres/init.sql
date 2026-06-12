-- PaperBridge Database Init
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- trigram similarity for fuzzy search

-- Articles table
CREATE TABLE IF NOT EXISTS articles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doi         VARCHAR(255) UNIQUE,
    scholar_id  VARCHAR(255) UNIQUE,
    title       TEXT NOT NULL,
    abstract    TEXT,
    authors     JSONB DEFAULT '[]',
    keywords    JSONB DEFAULT '[]',
    entities    JSONB DEFAULT '[]',
    year        INTEGER,
    venue       VARCHAR(500),
    citations   INTEGER DEFAULT 0,
    url         TEXT,
    embedding_path TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Full-text search index on title + abstract
CREATE INDEX IF NOT EXISTS articles_title_fts ON articles USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS articles_abstract_fts ON articles USING gin(to_tsvector('english', coalesce(abstract, '')));
CREATE INDEX IF NOT EXISTS articles_year ON articles(year);
CREATE INDEX IF NOT EXISTS articles_citations ON articles(citations DESC);

-- Recommendations cache table
CREATE TABLE IF NOT EXISTS recommendations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id   UUID REFERENCES articles(id) ON DELETE CASCADE,
    target_id   UUID REFERENCES articles(id) ON DELETE CASCADE,
    score       FLOAT NOT NULL,
    method      VARCHAR(50) DEFAULT 'hybrid',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, method)
);

CREATE INDEX IF NOT EXISTS recs_source ON recommendations(source_id);
CREATE INDEX IF NOT EXISTS recs_score ON recommendations(score DESC);

-- Search query audit log
CREATE TABLE IF NOT EXISTS search_queries (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query       TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    latency_ms  FLOAT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
