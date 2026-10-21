# ShopAI backend: FastAPI + CrewAI. The Android app and every external service
# (Supabase, Mem0, Arize, Hugging Face) live outside this image.

FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer only rebuilds when pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=build --chown=app:app /app /app

# Generated images land here and are served at /static - mount a volume on it.
RUN mkdir -p /app/src/shopai/output && chown app:app /app/src/shopai/output

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"

# uvicorn directly: `run_api` turns on the dev reloader. One process only - the
# task ledger lives in memory, so this must not be scaled to several replicas.
CMD ["uvicorn", "shopai.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
