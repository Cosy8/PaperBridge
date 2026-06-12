# syntax=docker/dockerfile:1
# ── Builder ─────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
# CPU-only torch first (sentence-transformers/keybert pull torch); avoids the
# default CUDA build. The spaCy model installs into the venv as a wheel and is
# carried over by the venv copy below.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt \
    && python -m spacy download en_core_web_sm

# ── Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
CMD ["python", "-m", "app.main"]
