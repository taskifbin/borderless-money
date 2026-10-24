# Borderless Money — one-command verification targets
# Judges: `make smoke` runs the whole gate on a fresh venv in <60s.

PY      := python3
VENV    := backend/.venv
VPY     := $(VENV)/bin/python

.PHONY: help setup smoke test eval-sanctions eval-rag ablation train-gnn run-backend run-frontend docker-build docker-up ci-local

help:
	@echo "make setup          - create venv + install lite requirements (fastapi layer)"
	@echo "make smoke          - fresh-venv import + end-to-end pipeline gate (Step 0)"
	@echo "make test           - stdlib unit tests (backend/tests/test_core.py)"
	@echo "make eval-sanctions - sanctions matcher benchmark: precision/recall/FPR/FNR (Step 1)"
	@echo "make eval-rag       - regulatory retrieval hit@k benchmark (Step 3)"
	@echo "make ablation       - risk-model ablation: rule vs logistic vs boosted vs GCN (Step 2)"
	@echo "make train-gnn      - retrain the GNN checkpoint (writes ml/model.pt + eval.json)"
	@echo "make run-backend    - uvicorn on :8000"
	@echo "make run-frontend   - next dev on :3000"
	@echo "make docker-build   - build the full-system image (Step 6)"
	@echo "make docker-up      - docker compose up (backend + frontend)"
	@echo "make ci-local       - everything CI runs: smoke + test + eval-sanctions + eval-rag"

setup:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --quiet -r backend/requirements-lite.txt

$(VENV)/.lite-installed:
	$(VENV)/bin/pip install --quiet -r backend/requirements-lite.txt && touch $@

smoke: $(VENV)/.lite-installed
	$(VPY) backend/tests/test_smoke.py

test:
	$(PY) backend/tests/test_core.py

eval-sanctions:
	$(PY) backend/evals/eval_sanctions.py

eval-rag:
	$(PY) backend/evals/eval_rag.py

ablation: $(VENV)/.lite-installed
	$(VPY) backend/ml/ablation.py

train-gnn: $(VENV)/.full-installed
	$(VPY) backend/ml/train_gnn.py

$(VENV)/.full-installed:
	$(VENV)/bin/pip install --quiet -r backend/requirements-full.txt && touch $@

run-backend:
	cd backend && .venv/bin/uvicorn app.main:app --port 8000

run-frontend:
	cd frontend && npm run dev

docker-build:
	docker build -t borderless-money-backend -f backend/Dockerfile backend

docker-up:
	docker compose up --build

ci-local: smoke test eval-sanctions eval-rag
	@echo "CI-equivalent local run: ALL GREEN"
