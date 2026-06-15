# syntax=docker/dockerfile:1
# ── Builder ─────────────────────────────────────────────────────
# Queries the Semantic Scholar HTTP API — no browser engine needed, so chromium
# and playwright are gone. All remaining deps ship as wheels (no compiler).
FROM python:3.11-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
CMD ["python", "-m", "app.main"]
