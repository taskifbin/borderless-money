# REAL vs SIMULATED — the honest state of every claim (post-sprint)

This file is the contract between the README and the code. Every surface is
either **REAL** (works as described, reproducible) or **SIMULATED** (labeled in
the UI and API). Last reconciled: 2026-10-24, after Steps 0–8 of the code-review
sprint. If a claim is not in this table, it does not exist.

| Surface | State | Evidence / how to verify |
| :--- | :--- | :--- |
| True Net Receive math (incl. 2.5% BD incentive) | **REAL** | `make test` — exact numbers asserted (33,488.80 / 820.00 on AED 1,000) |
| Corridor configs (rules as data) | **REAL** | `backend/config/corridors/{uae_bd,ksa_bd}.json`; e2e test runs KSA corridor (`tests/test_step4.py`) |
| Incentive eligibility as routing logic | **REAL** | teaser-rate rail is incentive-ineligible and loses the top spot (`tests/test_step4.py::test_incentive_flag_flips_the_winner`) |
| Expected-value ranking + naive baseline | **REAL** | `GET /api/routes/compare` returns `baseline` + per-route `expected_value_bdt` |
| Sanctions matcher (normalized Jaro + coverage) | **REAL** | `make eval-sanctions` — 14/14 true hits BLOCKED, 14/14 near-misses REVIEW, 0/21 clear flagged, 0 single-token blocks |
| Sanctions list | **SIMULATED** | 10-entry local sample (`data/ofac_sample.json`), not the official SDN export |
| Risk model (default scorer) | **REAL code, honest label** | `heuristic-stand-in` — a deterministic tabular rule; `engine` field says so; explanations generated from the decision log (`make ablation` for the rule/LR/stumps/GCN comparison) |
| Risk model (trained checkpoint) | **REAL training, SIMULATED data** | `USE_TRAINED_GNN=true` + `make train-gnn`; AUC 0.9038 on a labeled **synthetic** benchmark (ceiling ≈0.94 at 2% label noise) — `ml/eval.json` |
| Graph structure in the risk model | **NOT YET** | GCN consumes identical node vectors → reduces to an MLP; positioned as "graph-ready tabular risk model" (`ml/ablation.md`) |
| Stellar settlement | **SIMULATED by design** | `simulate_settlement()` — deterministic hash, `network: "SIMULATED"`, UI-labeled. A TESTNET state has never appeared in any run (grep logs: only SIMULATED). Real-demo requirements below |
| Horizon connectivity | **REAL probe** | `GET /api/routes/compare` → `data_sources.stellar_horizon` (timestamped reachability, never settlement data) |
| FX rates & fees | **SIMULATED (labeled)** | static corridor snapshots with `fx_source` + `sourced_at` timestamps; no live FX feed is claimed |
| Regulatory RAG | **REAL retrieval, excerpt corpus** | `make eval-rag` — hit@2 = 100% on the labeled set; every chunk cites org + domain; embeddings optional (MiniLM when installable, lexical fallback otherwise — engine field reports which) |
| Regulatory sources | **SIMULATED excerpts** | corpus lines are demo excerpts referencing real organizations/domains (bb.org.bd, ofac.treasury.gov, iso20022.org) — verify against the original documents before production use |
| LLM intent fallback | **REAL mechanism, OFF by default** | schema-validated, stub-tested (`tests/test_step3.py`); activates only with `BORDERLESS_MONEY_LLM_API_KEY`; UI + `/api/health` show the state |
| Bangla/English explanations | **REAL (template)** | generated from the decision log; every number ground-checked (`tests/test_step3.py::test_number_guard_*`); LLM paraphrase rejected on any invented number |
| Intent parsing (en/bn/ar regex) | **REAL** | 100% on the curated 49-utterance benchmark (`data/intent_eval.json`) — labeled curated, not production |
| KPIs | **MEASURED, internally sourced** | `GET /metrics` computes from in-repo eval sets; targets are labeled internal; one external baseline (World Bank RPW) documented in `docs/kpis.md` |
| bKash/Nagad payout | **SIMULATED** | mock registry `data/recipients.json` |
| pacs.008 payload | **REAL mapping, subset-validated** | settlement amount = gross − fees (incentive excluded, paid separately); validated against the documented subset in `docs/pacs008-subset.md` |
| Held payments move no money | **REAL (tested)** | REVIEW/BLOCK → no `execution`, no ledger hash, status `COMPLIANCE_REVIEW`/`BLOCKED` (`test_smoke.py::test_held_payment_moves_no_money`) |
| Exact-decimal money math | **REAL (new Oct 25)** | all monetary arithmetic is `Decimal` (`services/money.py`, `incentive.py`); display floats are quantized half-up at the edge and exact `*_exact` strings travel with every breakdown (`tests/test_financial.py`) |
| Quote lifecycle (ID, TTL, binding, single use) | **REAL (new Oct 25)** | every quote persisted (`services/quotes.py`); execute refuses expired/consumed/mismatched/unconfirmed quotes; receipt uses quoted numbers verbatim (`tests/test_financial.py::TestExecuteBindingSafety`, scenario C) |
| Idempotent execution | **REAL (new Oct 25)** | `Idempotency-Key` first-response-wins (in-memory/SQLite per process); verified over HTTP + scenario F |
| Uncertain settlement honesty | **REAL (new Oct 25)** | injected `TIMEOUT` → `RECONCILIATION_REQUIRED`, no hash, no success claim (scenario F) |
| Missing-fee honesty | **REAL (new Oct 25)** | unpriced route → flagged ineligible, no net figures, refused at settlement; pacs.008 raises rather than invent an amount (`test_unpriced_route_refused_at_settlement`) |
| B2B ROI model | **REAL math, ASSUMPTION inputs** | `services/roi.py` + `/roi` page; hand-computed tests (`tests/test_roi.py`); every input labeled a user assumption, outputs labeled modeled estimates |
| API hardening (request ID, rate limit, optional API key, readiness) | **REAL (new Oct 25)** | verified over live HTTP: 401 without key, 429 over limit, `X-Request-ID` on responses, `/api/ready` checks |
| Recipient screening of bare names in free text | **REAL (fixed Oct 25)** | parser now extracts bare proper-noun recipients ("send to Jahangir Alam via bkash") so they are SCREENED instead of silently replaced by the demo persona (scenario G) |

## What a REAL Stellar testnet demo would require

1. Fund two accounts from the testnet friendbot (issuer + distributor).
2. Issuer creates AED-DEMO and BDT-DEMO credit assets; distributor establishes
   trustlines to both.
3. Distributor holds a sell offer for the path AED-DEMO → XLM → BDT-DEMO.
4. Sender account holds AED-DEMO and sends a path payment to a third-party
   account (NOT self) with distinct send-max and destination-amount.
5. Commit the returned hash + Horizon explorer link here and flip the
   `network` label to TESTNET in code.

Until all five steps are demonstrably done, the UI and API say SIMULATED.

## Environment limitations (this workspace)

- No Hugging Face access → MiniLM embeddings cannot download; the lexical
  retriever serves and the engine field reports it. The code path for real
  embeddings ships and activates wherever the model is installable.
- No LLM API key configured → `llm_fallback: false` everywhere; the schema,
  guard, and fallback logic are stub-tested (`tests/test_step3.py`).
- No funded testnet accounts → settlement stays SIMULATED (above).
