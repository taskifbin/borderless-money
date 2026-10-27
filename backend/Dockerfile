# xPay — full backend (LangGraph + PyG risk model + RAG)
FROM python:3.12-slim

WORKDIR /app

COPY requirements-full.txt .
RUN pip install --no-cache-dir -r requirements-full.txt

COPY app ./app
COPY config ./config
COPY data ./data
COPY rag ./rag
COPY evals ./evals
COPY ml ./ml
COPY tests ./tests

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
