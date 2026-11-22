# xPay Render/free-tier backend image.
# The deterministic heuristic-GNN and lexical-RAG fallbacks keep runtime memory
# within Render's 512 MiB free web-service limit. The optional full ML stack is
# preserved in requirements-full.txt for local or larger deployments.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

COPY app ./app
COPY config ./config
COPY data ./data
COPY rag ./rag
COPY evals ./evals
COPY ml ./ml
COPY tests ./tests
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD sh -c "alembic upgrade head || echo 'migrations skipped (no DB)'; python scripts/seed_db.py || true; python scripts/seed_docs.py || true; uvicorn app.main:app --host 0.0.0.0 --port 8000"
