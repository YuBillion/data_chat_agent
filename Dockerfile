# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.11.18 AS uv

FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app

FROM base AS dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM base AS runtime
RUN groupadd --system app && useradd --system --gid app --home /app app
COPY --from=dependencies /app/.venv /app/.venv
COPY main.py alembic.ini ./
COPY app ./app
COPY conf ./conf
COPY prompts ./prompts
COPY migrations ./migrations
RUN mkdir -p /tmp/app && chown -R app:app /app /tmp/app
USER app
ENV HOME=/tmp/app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips=*"]

FROM runtime AS api

FROM runtime AS worker
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -m app.healthcheck
CMD ["python", "-m", "app.worker_main"]

FROM runtime AS migrate
USER app
HEALTHCHECK NONE
CMD ["python", "-m", "app.scripts.migrate"]
