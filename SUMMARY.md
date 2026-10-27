# Upgrade summary — Oct 27, 2026 (xPay / Borderless Money rebrand + phases)

Every item below is committed on `main` (one commit per logical chunk; nothing
pushed). Verification: all 6 stdlib suites + `make eval-sanctions` +
`make eval-rag` + 8/8 scenarios green; `tsc --noEmit` clean; fresh clone
`make ci-local` ALL GREEN; fresh-clone `docker compose up --build` serves the
new numbers (best net ৳33,423.20, /metrics uplift 3.05, frontend title
"xPay — Send more home").

## Phase 0 — submission hygiene

| # | Item | What was done | Files |
| :- | :--- | :--- | :--- |
| 0.1 | Tracked-files audit + fresh-clone build | routing_scorer/tests/rag/configs all tracked; `.tmp_clone/` ignored; fresh clone `docker compose up --build` + `make ci-local` pass | `.gitignore` |
| 0.2 | Report scrub + regenerate | unknown-corridor error made machine-independent (leaked `/home/taskifbin/...` and a stale `mars_bd.json` path); report regenerated 8/8, leak grep = 0 | `backend/app/services/corridor.py`, `docs/evaluation_report.json` |
| 0.3 | Claim reconciliation | NetworkX (unused import claim) removed from docs + `/api/health` flags; "real-time FX" → snapshot; stale "1.3 ms" → live `GET /metrics`; testnet claims → simulated-by-design wording; "10 labeled" KPIs → actual 54-case benchmark; "holds-not-blocks" → holds near-matches, blocks exact | `README.md`, `docs/one-pager.md`, `docs/competition-analysis.md`, `docs/api-contracts.md`, `backend/app/main.py` |

## Phase 1 — numbers that survive scrutiny

| # | Item | What was done | Files |
| :- | :--- | :--- | :--- |
| 1.4 | Sourced corridor data | `_sources` provenance block in both corridor configs (all economic fields UNVERIFIED with SOURCE NEEDED pointers); `data/sources.md` field→source→date table + replacement workflow | corridor JSONs, `data/sources.md` |
| 1.5 | Platform fee AED 2 | Engine gains `platform_fee_source`; scorer reports `fee_source_components`; headline recomputed **33,488.80 → 33,423.20, uplift +3.26% → +3.05%** (vs legacy SWIFT counterfactual); regression tests assert the fee is subtracted exactly once; UI shows "— of which xPay sender fee"; all docs/payloads updated | `incentive.py`, `routing_scorer.py`, `metrics.py`, corridor JSONs, tests, `README.md`, docs, `page.tsx`, `types.ts` |
| 1.6 | Stellar sensitivity | Script-generated table 0.5/1.0/1.5% anchor spreads; **pessimistic row (+2.59%) FAILS the 3% target and is published, not hidden**; one-pager carries the row | `scripts/stellar_sensitivity.py`, `docs/stellar-sensitivity.md`, `docs/one-pager.md` |
| 1.7 | Kill the contrived rail | Teaser FX 33.6 (> mid-market 33.15 — illegal quote) → 33.1; hard invariant tests: no rail above mid-market, sane fees/rates/hours for EVERY corridor | `uae_bd.json`, `tests/test_financial.py`, `tests/test_step4.py` |
| 1.8 | 1,000-transfer simulation | Deterministic sim vs 3 baselines: xPay EV +3.53% mean vs current channel; fee-only +2.26% (the gap IS the incentive-aware ranking); ranking differs on 100% of transfers (interpretation embedded) | `scripts/simulate_1000.py`, `reports/simulation_1000.json` |
| 1.9 | Field naming | `fee_aed` → `fee_total_source`, `spread_bdt_per_aed` → `spread_per_source_unit` (route-level `fee_source` deliberately avoided — collision with `breakdown.fee_source`); third corridor `my_bd.json` (MYR) loads with zero code changes; config-only test + corridor-agnostic-name test | scorer, `main.py`, frontend, tests, docs, `my_bd.json` |

## Phase 2 — technical depth (partial — see TODOs)

| # | Item | What was done | Files |
| :- | :--- | :--- | :--- |
| 2.11 | Failure model | `expected_value_bdt` renamed `reliability_adjusted_net` with the honest definition written next to it (failures modeled as TOTAL loss; no refund/retry modeled — that is future work that would change the ranking) | scorer, `main.py`, frontend, tests, evals, `docs/FINANCIAL_MODEL.md`, `docs/api-contracts.md`, `docs/architecture.md` |
| 2.12 | deadline_hours end-to-end | Utterance → parser (urgent→3h, tomorrow→24h, tonight→12h, "within N h" exact) → scorer filter → API field → UI select (en/bn); tests: "by tomorrow" filters the 28h SWIFT route end-to-end; 3h API check returns only 1–2h routes | `intent_parser.py`, `orchestrator.py`, `main.py`, `api.ts`, `page.tsx`, `i18n.ts`, `tests/test_step4.py` |
| 2.15/16/13 | Timing advisor, LLM-on, calibration, GNN real-data | **NOT DONE — blocked on externals**, stubs only: LLM-on needs a real `XPAY_LLM_API_KEY` + deployment; calibration/real-data metric needs the Kaggle fraud set; timing advisor needs managed-taka data. No fake backtests were committed. | — |

## Phase 3 — compliance & ethics

| # | Item | What was done | Files |
| :- | :--- | :--- | :--- |
| 3.hard | Screening hardening | Fixed 2 bypasses found by adversarial testing: leet glyphs normalize to letters (`F@rh@n Ahmed` now BLOCKS); empty-normalized names go to REVIEW instead of vacuous CLEAR | `compliance.py`, `sanctions_eval.json`, `eval_sanctions.py`, `metrics.py` |
| 3.17 | Alias-only downgrade | `Md/Mohammed/Muhammad → Mohammad` equality is HELD for review, never auto-blocked (no second identifier collected); corporate suffixes exempt; benchmark v4 (58 cases), eval asserts 0 alias-only blocks; counts updated everywhere | `compliance.py`, `sanctions_eval.json`, `eval_sanctions.py`, `metrics.py`, `tests/test_step4.py`, README/kpis/REAL_VS_SIMULATED/SECURITY docs |
| 3.18 | Review volume | 500 seeded synthetic transfers: **8 reviews / 1,000** (0.8%); flagged examples show the load driver (shared-"Mohammad" prefix Jaro ~0.90); re-measure vs official SDN required | `scripts/review_volume.py`, `reports/review_volume.json` |
| 3.19 | Responsible AI | `docs/responsible-ai.md`: what the safety path does, measured metrics, appeals path + 24h SLA, explicit "what this project does NOT claim", before-production list; linked from README | `docs/responsible-ai.md`, `README.md` |

## Phase 4 — unit economics & deployment (partial)

| # | Item | What was done | Files |
| :- | :--- | :--- | :--- |
| 4.20 | Unit economics | All cost lines itemized (settlement/audit writes were missing) → **95.4% margin, not ≈96%**; 0.15% payer stated (partner; final incidence SOURCE NEEDED); take-rate + CAC-payback sensitivity tables; 6-month figures recomputed; one-pager synced | `docs/unit-economics.md`, `docs/one-pager.md` |
| 4.22 | Third corridor live | `my_bd.json` (MYR) loads config-only; SAR display already covered by `tests/test_step4.py`; covered by 1.9 commit | `my_bd.json`, `tests/test_financial.py` |
| 4.23 | Deploy + latency | `deploy/render.yaml` blueprint with **VERIFY** block (repo holds no credentials — human must connect Render, rename GitHub repo, patch API URL); measured end-to-end p95 **21.2 ms** (300 loopback requests; first attempt hit the 240/min limiter at request ~241 — proof the limiter works); README/kpis cite the measured number | `deploy/render.yaml`, `scripts/load_test_p95.py`, `reports/load_test.txt`, README, kpis |

## Phase 5 — non-code (stubs only, nothing faked)

| # | Item | What was done | Files |
| :- | :--- | :--- | :--- |
| 5.24 | Survey | 9-question instrument; results table EMPTY; `TODO(collect N responses)` | `docs/validation/survey.md` |
| 5.25 | NRB note | Decision record: note by Oct 30 or the claim is dropped; `TODO(decision by Oct 30)` | `docs/nrb/README.md` |
| 5.26 | "No other app" | Softened to "the only one we found" everywhere; competitive-scan protocol (5 alternatives, dated screenshots) with TODO | `docs/competitive-scan.md`, `docs/demo-script.md`, `docs/one-pager.md` |
| 5.27 | Pitch docs | `docs/pitch/script-3min.md` (current numbers + pre-recording checklist) and `docs/pitch/hard-questions.md` (8 questions, 20-second answers, grounded; #2/#7 TODO: survey, #5 TODO: scan) | `docs/pitch/` |

## Remaining TODO / SOURCE NEEDED markers

- `data/sources.md`: every corridor economic field UNVERIFIED (World Bank RPW +
  provider fee pages + Bangladesh Bank circular number/URL to be attached).
- `docs/competitive-scan.md`: 5-alternative scan + screenshots.
- `docs/validation/survey.md`: collect 15–25 responses.
- `docs/nrb/README.md`: keep-or-drop decision by Oct 30.
- `deploy/render.yaml`: human deploy steps (credentials).
- Not attempted (blocked on external data/keys, no fakes committed): timing
  advisor backtest, GNN calibration on the Kaggle fraud set, LLM-on in a
  deployed demo (needs `XPAY_LLM_API_KEY` + live URL).

## Verification checklist (run before handoff)

- [x] `git log --oneline` — one commit per numbered item (grouped where items shared files); no push (`git rev-list origin/main..HEAD --count` > 0)
- [x] `git status` clean
- [x] `docker compose up --build` succeeds from a fresh in-repo clone (backend healthy; frontend serves "xPay — Send more home"; `/routes/compare` returns 33,423.20)
- [x] Full test suite passes; new tests cover: platform fee, no-rail-above-mid-market, config-added corridor loads, failure-model rename, deadline filter (scorer + utterance), alias→review policy, leet/unscreenable hardening
- [x] `grep -R` for NetworkX / real-time / 1.3 ms / no other app / 33.6 / +3.26 → only intended matches (banned-phrase rationale, engine-contract test fixtures documented in FINANCIAL_MODEL, corridor-agnostic claim proven by test)
