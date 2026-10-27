# Financial Model — Calculation Contract

**Status: implemented and test-covered** (`backend/tests/test_financial.py`,
`backend/tests/test_core.py`). This document is the single source of truth for
how every monetary figure in xPay is computed. If code and this
document disagree, that is a bug — file it.

## 1. Arithmetic substrate

- All financial math runs in **exact decimal arithmetic** (`decimal.Decimal`),
  via `backend/app/services/money.py`. Binary floats never participate in a
  monetary computation; they appear only at the serialization edge.
- Floats arriving from JSON/HTTP are converted **once** through their shortest
  round-trip decimal repr (`D(32.8) → Decimal("32.8")`).
- NaN, ±inf, booleans, malformed strings and non-numeric types are **rejected**
  (`MoneyValueError`, a `ValueError` subclass) — never coerced.
- Currency minor units follow ISO 4217 (`CURRENCY_EXPONENTS`: BDT/AED/USD/SAR 2dp,
  JPY 0dp, KWD/BHD/OMR 3dp; unlisted → 2dp).

## 2. Rounding

- Intermediate results stay at full Decimal precision (28 significant digits).
- Quantization to a currency's minor unit happens **only at presentation/
  settlement edges**, always **ROUND_HALF_UP** (2.005 → 2.01; −2.005 → −2.01).
  Banker's rounding is never used for displayed amounts.
- Every API response carries exact decimal strings alongside display floats:
  `breakdown.true_net_receive_exact`, `gross_exact`, `fees_deducted_exact`,
  `govt_incentive_exact`, and route-level `expected_value_exact`. **The string
  is the authoritative value; the float is presentation.**

## 3. True Net Receive — the formula

For a route with principal `P` (source ccy), all-in FX rate `r`, fee `f`
(source ccy), and government incentive rate `g`:

```
gross_dest       = P × r
fees_dest        = (f + p) × r      (f = rail+last-mile fee, p = platform fee
                                     — xPay's own flat sender fee, both quoted
                                     in SOURCE currency — default; p is itemized
                                     as breakdown.platform_fee_source)
                 | f + p × r        (fees quoted in DEST currency: fee_currency="DEST")
incentive_dest   = gross_dest × g   (computed on converted principal BEFORE
                                     fee deduction — the BB incentive attaches
                                     to the remitted amount, not the fee)
true_net_dest    = gross_dest − fees_dest + incentive_dest
```

- `g` comes from the corridor config (`govt_incentive_rate`, UAE→BD: 0.025) and
  is applied **only** to rails flagged `incentive_eligible: true`. It is applied
  exactly **once** per route — the engine takes a single rate argument.
- Fees are **deducted from the converted proceeds**, not charged on top of the
  principal; a sender paying "AED 4 fee" pays exactly AED 4 total.
- **Anti-double-counting:** the corridor `fx` per rail is the **all-in customer
  rate**. Any provider spread is understood to be embedded in it and is never
  added again as a separate fee. `spread_bdt_per_aed` (mid − rail rate) is
  displayed for transparency only and never re-applied.

## 4. Missing data — flagged, never zeroed

A route whose fee is absent (`fee_source: null` in corridor config) is:

- priced with `fee_source=None` → `pricing_completeness: "incomplete"`,
  `missing_fields: ["fee_source"]`, `data_quality_note` set;
- given **no** fee/net/EV figures (`None`, not 0);
- marked `eligibility.eligible = false, reason = "missing_fee_data"`;
- **excluded from winning** — ranked after every priced route, `is_best` never
  true, `advantage_bdt_vs_best: null`;
- **refused at settlement** (`error: "incomplete_pricing"`) even if explicitly
  selected — an unpriced route may be displayed as flagged but can never settle,
  and `to_pacs_008` raises rather than fabricate a settlement amount.

## 5. Eligibility before optimization

Ranking order: (1) mark eligibility; (2) rank **eligible** routes by expected
value `EV = true_net × success_rate` (rounded half-up 2dp); (3) append
ineligible/unpriced routes; (4) `is_best` only on the top eligible route.

Hard eligibility inputs today: complete pricing, deadline feasibility (a
deadline that excludes all priced routes raises `ValueError`), corridor/payout
support. Compliance outcomes (`BLOCKED`, `FUZZY_MATCH_REVIEW`,
`HIGH_RISK_REVIEW`) gate execution *after* routing and can never be overridden
by user preference or route selection. Ties (identical candidates) keep
corridor-config order — deterministic output.

## 6. Quote lifecycle (what the user confirmed is what settles)

- Every quote gets `quote_id`, `created_at`, `expires_at` (TTL from corridor
  `quote_ttl_minutes`, default 60 min), stored verbatim (floats **and** exact
  strings).
- Execution may bind to a quote: `quote_id` + `confirmed: true`. Revalidation
  before settlement checks: exists → not expired → not already consumed
  (single use) → route ∈ quoted set → amount matches → payout method matches.
  Failure codes: `quote_not_found`, `quote_expired`, `quote_already_used`,
  `route_not_in_quote`, `amount_mismatch`, `payout_method_mismatch`,
  `confirmation_required`.
- Binding uses **the stored quoted numbers verbatim** for the receipt — a
  re-score between quote and confirm can never change the settled price.
- The unbound demo path (no `quote_id`) is labeled
  `quote_binding: "fresh_unbound_demo"` in the receipt and the log.
- API-level duplicates are absorbed by `Idempotency-Key`: the first response
  wins; replays return it verbatim with `idempotent_replay: true`.

## 7. Settlement honesty

`stellar.simulate_settlement` returns `COMPLETED` (with a simulated, clearly
labeled hash) or — when the demo harness injects `outcome=TIMEOUT|FAILED` — an
**uncertain** result. Uncertain results are never reported as success:
transaction status becomes `RECONCILIATION_REQUIRED`, no hash is produced, the
log says "no success claim", and the receipt carries
`reconciliation_required: true`.

## 8. Test coverage (actual, run via `make test` / `make test-financial`)

| Area | Coverage |
| :--- | :--- |
| Exact fee math, rounding boundaries (half-up, negative, 0/3dp currencies) | `TestMoneyPrimitives`, `TestTrueNetReceiveExact` |
| Source vs destination fee currency | `test_fee_in_*` |
| Missing fee → incomplete, no net | `test_missing_fee_is_flagged_never_zeroed` |
| Zero/negative principal, NaN, bad FX, negative fee, invalid incentive rate | input-validation tests |
| Incentive applied once, zero-rate disable | `test_incentive_applied_exactly_once`, `test_zero_rate_disables_incentive` |
| Large valid amounts (1e9) | `test_very_large_but_valid_amount` |
| Reproducibility (same inputs → same outputs) | `test_reproducible_*` |
| Unpriced route never wins; winner = max-EV eligible (200 seeded random amounts) | `test_missing_fee_data_route_cannot_win`, `test_ineligible_or_unpriced_never_wins_property` |
| Identical candidates → stable order | `test_identical_candidates_keep_stable_config_order` |
| Malformed corridor pricing surfaced (not swallowed) | `test_malformed_rail_fx_is_surfaced_not_swallowed` |
| Quote TTL/expiry/single-use/mismatch gates; expired quote refuses execution | `TestQuoteLifecycle`, `TestExecuteBindingSafety` |
| Unconfirmed binding refused; consumed quote refused | same |
| Uncertain settlement → no success claim | `test_uncertain_settlement_never_reports_success` |
| Unpriced route refused at settlement + pacs.008 raises | `test_unpriced_route_refused_at_settlement` |
| Idempotency first-response-wins | `TestIdempotencyStore` |
| Known reference values (engine: AED 1,000 → ৳33,488.80 ex-platform-fee; end-to-end incl. AED 2 platform fee → ৳33,423.20; uplift vs legacy SWIFT +3.05%) | `test_core.TestIncentiveMath`, `test_financial.TestPlatformFee`, `tests/test_smoke.py` |

## 9. Known modeling simplifications (honest list)

- FX rates and rail fees are **fixture snapshots** in corridor config; no live
  FX feed is wired (interface documented in `fx.py`).
- Fees are modeled as a single source-currency line per leg (rail + last-mile);
  intermediary/deduction-from-principal variants beyond §3 are not modeled.
- Taxes: none modeled (the 2.5% incentive is a government *payment*, not a tax
  refund); VAT/GST on fees is not represented.
- Delivery time is the corridor's static `hours` estimate, not a live SLA.
