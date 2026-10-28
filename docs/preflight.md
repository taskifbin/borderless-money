# Phase 0 preflight — repo map and baseline (2026-10-28)

- Baseline commit at preflight: `13599c8` (docs(readme): congress link + team GitHub links)
- `git status`: clean
- Branch: `main` (19+ commits ahead of origin/main; nothing pushed)

## Required-path verification

| Required by action list | Actual | Status |
| :--- | :--- | :--- |
| `routing_score.py` | `backend/app/services/routing_scorer.py` (contains `def score_routes`) | PRESENT — name differs from the action list (`routing_score.py` does not exist; recorded, proceeding) |
| `tests/` | `backend/tests/` (6 stdlib suites) | PRESENT |
| `rag/` | `backend/rag/corpus/` | PRESENT |
| `scripts/simulate_1000.py` | — | PRESENT |
| `score_routes` function | `backend/app/services/routing_scorer.py:30` | PRESENT |
| RouteCard component | `frontend/app/page.tsx` (`function RouteCard`) | PRESENT |
| `i18n.ts` | `frontend/lib/i18n.ts` | PRESENT |
| `render.yaml` | `deploy/render.yaml` | PRESENT |
| `manus-routes.json` | `frontend/public/manus-routes.json` | PRESENT (scheduled for deletion in F9) |
| `review_volume.py` | `scripts/review_volume.py` | PRESENT |

## Baseline map (maxdepth 3, condensed)

- `backend/app/services/`: compliance, corridor, explainer, fx, gnn_risk, horizon,
  incentive, intent_parser, llm, metrics, money, quotes, regulatory_rag, roi,
  routing_scorer, stellar, store
- `backend/app/agent/orchestrator.py`; `backend/config/corridors/{uae_bd,ksa_bd,my_bd}.json`
- `backend/data/`: fx_rates, ofac_sample, sanctions_eval, intent_eval, compliance_eval
- `backend/evals/`: eval_scenarios, eval_sanctions, eval_rag
- `frontend/app/`: layout.tsx, page.tsx, globals.css, roi/page.tsx;
  `frontend/lib/`: api.ts, i18n.ts, types.ts; `frontend/components/`: ChainTrail, FlowDiagram, MicButton
- `scripts/`: simulate_1000, stellar_sensitivity, review_volume, load_test_p95
- `reports/`: simulation_1000.json, review_volume.json, load_test.txt
- `deploy/render.yaml`; `.github/workflows/ci.yml`; `Makefile`; `docker-compose.yml`
