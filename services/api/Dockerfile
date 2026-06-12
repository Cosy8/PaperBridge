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
# Install CPU-only torch FIRST so sentence-transformers doesn't pull the
# default CUDA build (~5GB of nvidia-* wheels). pip cache lives in a BuildKit
# cache mount (not in the image) so rebuilds are fast but the layer stays slim.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

# ── Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
