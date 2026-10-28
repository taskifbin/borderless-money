# Decision log

Decisions with real consequences for architecture, compliance posture, or
claims. Each entry: what was decided, why, and where it lives in the repo.
Open items stay here until resolved — they are never silently dropped.

## Decided

| Date | Decision | Rationale | Where |
| :--- | :--- | :--- | :--- |
| 2026-10-25 | Money math runs in exact `Decimal` with half-up rounding only at display edges; NaN/garbage rejected | float drift in remittance math is a correctness and trust bug; taka figures must reconcile to the poisha | `backend/app/services/money.py`, `docs/FINANCIAL_MODEL.md` |
| 2026-10-25 | Platform fee: **AED 2.00 flat, charged in source currency**, always a visible line item | simple, honest, covers cost 0.16/transfer with 95.4% margin; hiding it inside FX would be the dark pattern we criticize | `backend/config/corridors/uae_bd.json` (`platform_fee_source`), `docs/unit-economics.md` |
| 2026-10-25 | Settlement is **simulated by design** and never shown as a real testnet hash | an earlier self-to-self testnet "attempt" could not work (no trustlines/counterparty) and would have failed silently — honest labeling beats a fake success | `backend/app/services/stellar.py`, `REAL_VS_SIMULATED.md` |
| 2026-10-26 | Compliance policy: **BLOCK only exact canonical equality**; alias-only equality (Md/Mohammed → Mohammad) and unscreenable names → REVIEW with a recorded rationale | blocking near-matches produces false rejections of real customers; blocking aliases without a second identifier is over-blocking | `backend/app/services/compliance.py`, `data/sanctions_eval.json` (58-case benchmark) |
| 2026-10-26 | Ranking metric: **reliability-adjusted net** (`true_net × success_rate`), displayed next to each route and identical to the ranking call (B2 fix) | fee-only ranking ignores failure risk; the metric shown must be the metric used — enforced by unit test | `backend/app/services/routing_scorer.py`, `backend/tests/test_step4.py` |
| 2026-10-27 | Engine-only latency is **not** quoted as a KPI — the 21.2 ms end-to-end HTTP p95 is the user-facing figure | engine-only timing flatters the system by excluding HTTP/parsing; end-to-end is the honest number | `README.md` KPI table, `docs/kpis.md` |
| 2026-10-28 | Compliance matcher: the full-name-Jaro review branch additionally requires a **token floor of 0.80** — every meaningful query token (len ≥ 2) must be fuzzy-close to some entry token | "Mohammad Pal"/"Mohammad Mia" scored 0.90+/0.925 against listed "Mohammad Salim" purely on the shared "mohammad" prefix and wrongly reviewed; real spelling variants (Ahmad/Ahmed ≈ 0.867) pass the floor, shared-forename collisions (pal↔salim ≈ 0.5) fail it. Query-side only, so abbreviated queries ("Nasir U. Chaudhury") still review. 58-case benchmark unchanged (recall 100%, FPR 0%); local-list review volume 8→0 / 1,000; real-SDN workload measured at 40 / 1,000 | `backend/app/services/compliance.py` (`_token_floor_ok`), `data/sources.md` |
| 2026-10-28 | Corridor fixture stays at the 2026-10-24 snapshot (33.15) even though the live reference was 33.776 on 2026-10-28; the ~1.9% delta is disclosed, re-baseline deferred | re-baselining would change every headline number days before submission; disclosure beats a silent mid-demo shift | `data/sources.md` live-reference section, `backend/config/corridors/uae_bd.json` `_sources` |

## Open items

| Opened | Item | Owner | Due | Status |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-25 | **NRB advisor** — Bangladesh Bank regulatory note (incentive eligibility + RaaS licensing question) | captain | 2026-10-30 | **OPEN — do not resolve without the actual advisor response**; slot for the signed note: `docs/nrb/advisor-note.md` |
| 2026-10-28 | Provider rate+fee sourcing (Wise / Remitly / Al Ansari) + World Bank RPW row — blocked on interactive-tool pages and a 403; exact human-fill URLs in `data/sources.md` | team | post-submission | **OPEN (blocked)** — do not invent the numbers |
