# Validation Report — what was actually run and what it showed

**Generated:** 2026-10-25 · **Environment:** local venv (Python 3.12, `backend/.venv`),
no external network dependencies; every simulated surface labeled. This report
contains only executed commands and their real outputs — no invented numbers.

## 1. Commands executed and results

| Command | Result |
| :--- | :--- |
| `make test` (→ `tests/test_core.py`, `tests/test_financial.py`, `tests/test_roi.py`) | **79 tests, all pass** (23 + 41 + 15) |
| `tests/test_step3.py` | **18 tests pass** |
| `tests/test_step4.py` | **9 tests pass** (incl. KSA corridor end-to-end; asserts the fixed SAR currency bug) |
| `make smoke` (`tests/test_smoke.py`) | **5 tests pass** |
| `make scenarios` (`evals/eval_scenarios.py`) | **8/8 scenarios pass** → `docs/evaluation_report.json` |
| `make eval-sanctions` | recall 14/14 (100%), near-variant recall 14/14 (100%), block precision 100%, single-token hard-blocks 0, policy table satisfied |
| `make eval-rag` | hit@2 8/8 (100%), all citations resolve to allowed domains |
| `npx tsc --noEmit` (frontend) | clean |
| `npm run build` (frontend) | success — routes `/` (94.8 kB) and `/roi` (90.1 kB first-load) |
| Live API verification (uvicorn + curl) | `/api/ready` ok · `X-Request-ID` present · quote→bound execute uses quoted numbers · idempotent replay returns original receipt · consumed quote → `quote_already_used` · unconfirmed → `confirmation_required` · missing API key → 401 · burst over limit → 429 · health/ready stay 200 under throttle |
| `make ablation` / `make train-gnn` | **not re-run this session** (requires full PyG stack hours; prior artifacts `ml/eval.json` AUC 0.9038 + `ml/ablation.md` stand as the recorded results, honestly caveated as synthetic-benchmark) |

Total test count: **111 tests across 6 suites, all passing.**

## 2. Evaluation dataset(s)

- Scenario suite: 8 scenarios (A–H) defined in `backend/evals/eval_scenarios.py`,
  each recording expected vs actual vs pass vs `data_type` per run.
- Intent: 49 curated utterances (`data/intent_eval.json`) — measured 100%.
- Sanctions: curated benchmark (14 true hits, 14 near-variants, 21 clear names)
  — small, labeled, in-repo.
- Property-style invariant: 200 seeded random amounts asserting "winner = max-EV
  eligible route; unpriced routes never win" (`test_financial.py`).
- ROI: 15 hand-computed checks (`tests/test_roi.py`).

## 3. Measured KPIs (from `GET /metrics`, computed 2026-10-25)

| KPI | Measured | Basis |
| :--- | ---: | :--- |
| Net-receive uplift vs SWIFT | +3.26% | corridor math, AED 1,000 (৳33,488.80 vs ৳32,432.40) |
| Intent accuracy (en/bn/ar) | 100% | 49-utterance curated benchmark |
| p95 quote latency (engine) | 9.6 ms | 20 timed in-process quote runs |
| Compliance false-positive hold rate | 0.0% | curated clear-name benchmark |
| OFAC screening recall | 100% | curated true-positive benchmark |

All benchmarks are small, curated, and in-repo — useful regression gates, not
production claims.

## 4. Failed tests / fixed during this pass (honest list)

Everything below **failed at least once while building** and now passes:

1. Decimal engine initially crashed on the config-supplied incentive rate (float × Decimal).
2. Quote created mid-run was mistaken for a caller-bound quote → every execute hit `confirmation_required`.
3. Orchestrator log line crashed comparing against an unpriced route (`None` net).
4. Explainer templates crashed rendering `None` money figures (`.get(key, 0)` trap).
5. `to_pacs_008` crashed on incomplete pricing → now raises a clear error, and the orchestrator refuses to settle unpriced routes at all.
6. ROI break-even algebra was wrong (fee and customer costs both drag — they add).
7. Rate limiter initially throttled `/api/health` despite the stated ops-exemption policy → fixed and re-verified.

## 5. Bugs found in the EXISTING code and fixed

1. **KSA receipts mislabeled currency** — SAR→BDT transactions were recorded with `currency_source: "AED"` (hardcoded); the old test asserted the bug. Fixed; test now asserts SAR.
2. **Bare recipient names dropped from screening** — "send to Jahangir Alam via bkash" silently screened the demo persona instead. Parser now extracts bare proper-noun recipients (49-utterance benchmark still 100%).

## 6. Unverified capabilities & limitations (explicit)

- **Settlement is simulated by design** — no funded Stellar testnet credentials; the uncertain-outcome path is code + tests, never exercised against a real ledger.
- **bKash/Nagad payout is a mock registry**; no real payout integration exists.
- **FX/fee data are fixture snapshots** with `sourced_at` labels; no live feed.
- **Sanctions list is a 10-entry local sample** — not an official SDN export; the matcher is not a legal screening system.
- **Risk model** trained on synthetic data (AUC 0.9038, documented ceiling ≈0.94); stand-in inference is default; not calibrated; not integrated as a legal determination.
- **RAG corpus** contains demo excerpts referencing real organizations — verify against original documents before production.
- **Rate limiting, idempotency store, quote store** are in-memory/SQLite per process — a multi-node deployment needs shared state.
- **LLM fallback untested against a real LLM** (no API key configured; stub-tested).
- **Bengali/Arabic currency nuance:** Banglish "1500 taka" parses amount+payout correctly but labels the source currency BDT (ambiguous input — documented, not silently converted).

## 7. Next validation steps

1. Shadow-mode pilot with one operator (recommendations logged vs their choices) — validates the ROI model's adoption/cost assumptions.
2. Licensed sanctions list + real-name evaluation set for the matcher.
3. Funded Stellar testnet demo per REAL_VS_SIMULATED.md, flipping one surface to REAL.
4. Reviewer-decision API (sign-off records with timestamps) to complete the audit loop.
5. Load/deployment hardening: shared rate-limit + idempotency store, structured logging, dependency scanning.
