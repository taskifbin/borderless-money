# Product Strategy — B2B Remittance Intelligence

**Status: business model documented with explicit assumption labels. Nothing
below is validated by customer evidence; the validation plan in
[business-validation.md](business-validation.md) is how it gets validated.**

## 1. What the product is

A **B2B Remittance Intelligence API** with a consumer-facing demonstration app:
it ingests a transfer intent (text/voice, en/bn/ar), compares every eligible
payout route in the corridor, computes the **exact recipient net** (fees, FX,
2.5% Bangladesh Bank incentive — exact-decimal math, test-covered), screens
parties against sanctions, explains every recommendation with traceable
evidence, and binds execution to the confirmed quote.

Value proposition: *"Help remittance providers and fintech platforms compare
eligible transfer routes, maximize the recipient's net amount, understand
compliance restrictions, and explain every recommendation using traceable
evidence."*

## 2. Initial customer segment (chosen)

| Segment | Access from Dhaka/UAE network | Why / why not first |
| :--- | :--- | :--- |
| **UAE exchange-house MTOs & SME remittance operators** | **Chosen first** | They already aggregate UAE→BD flow, feel fee/FX pressure daily, have compliance teams that understand a "decision-support" pitch, and integrate via simple REST. Decision-maker: Head of Operations / COO. Buyer persona is reachable at industry events (e.g., remittance conferences in Dubai) without enterprise procurement. |
| Bangladeshi MFS wallets (bKash/Nagad-class) | Later | High volume, but they ARE the last mile — they'd want the inbound-routing side; slower BDV/BB-touching sales cycle. Distribution partner, not first payer. |
| Banks / licensed MTBs | Later | Long procurement (6–12+ months), ISO 27001/SOC 2 expectations a hackathon prototype cannot meet. |
| Consumer senders | Not a payer | The demo app exists to *show* the engine, not to acquire consumers; consumer fintech needs licenses we don't claim. |

**Initial customer (assumption, unvalidated):** a UAE-licensed exchange house
or SME remittance operator sending ≥ AED 2M/month to Bangladesh, currently
pricing routes manually across 3–5 correspondent options, with no in-house
engineering to build this themselves.

- Their workflow today (assumed): spreadsheets + correspondent WhatsApp quotes;
  a compliance officer eyeballs screening; pricing updated weekly at best.
- The problem we claim we solve: leaving 0.5–1.0% of principal on the table in
  fees/spread, plus manual screening drag. **The cost of the problem is an
  assumption to validate in discovery — not a measured number.**
- Who buys: COO/Head of Ops. Who uses: ops analysts + compliance officer.
- Why buy vs build: 2 engineer-weeks of corridor config vs months of in-house
  build; screened/audited decision logs out of the box.
- Required integrations (from them): REST client, their rail fee schedules
  (config JSON), their sanctions list source, SSO/API keys.
- Barriers: security review (we ship: optional API keys, rate limits, request
  IDs, no PII in logs), data-residency questions, "prove the numbers" pilots.
- Sales cycle: **assumption** — 4–8 weeks to a paid pilot for SME operators.

## 3. Monetization models compared

| Model | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- |
| A. Monthly SaaS | Predictable revenue; simple procurement | Pricing must guess volume; poor fit for spiky remittance flow | Fallback |
| **B. Usage-based API pricing** | Aligns cost with value; tiny entry price lowers pilot friction; scales with corridor growth | Revenue less predictable; needs metering (we ship idempotency + request IDs, which help) | **Primary** |
| C. Enterprise licensing | Big contracts | Sales cycle incompatible with our stage; on-prem support burden | Not now |
| D. Paid pilot → annual | Converts Proof into commitment | Only after B proves value | Sequence after B |
| E. Revenue share on flow | Big upside | Legally loaded: sharing in money-transfer economics can trigger licensing questions we cannot answer as a non-MSB | Rejected for now |

**Primary: B — usage-based, per successful route recommendation executed.**
Anchor (assumption, sized from the unit-economics doc): **AED 1.00 per executed
transfer** (vs incumbent all-in fees of AED 15–25 per transfer — incumbents
leave far more than AED 1 of value per transfer on the table, so the price is
an order of magnitude under the value while staying software-margin).
**Fallback: A — monthly SaaS** at AED 1,500–5,000/month tiered by volume for
customers whose procurement hates metering.

Revenue never touches the government's 2.5% incentive (it belongs to the
recipient) and never takes transfer fees that require MSB licenses — we sell
software intelligence, not money transmission.

## 4. ROI model (implemented + tested)

`backend/app/services/roi.py` (mirror: `/roi` page in the frontend) computes,
from **user-labeled assumptions**:

- `eligible_transfers = monthly_transfers × eligibility_share`
- `adopted_transfers = eligible_transfers × adoption_rate`
- `gross_recipient_benefit = principal_moved × (baseline_all_in_pct − proposed_all_in_pct)`
- `customer_cost_savings = recipient_benefit × customer_cost_bearing_share`
- `api_revenue = adopted × api_price_per_tx + api_monthly_fee`
- `customer_net_benefit = savings − api_revenue − customer_monthly_costs`
- break-even volume; vendor gross margin **only when a cost input is supplied**;
  conservative/base/optimistic scenarios scaling adoption (×0.5/×1/×1.5) and
  eligibility (×0.8/×1/×1).

Hard honesty rules enforced in code and tests: recipient benefit is never
vendor revenue; missing cost inputs → margin reported as unknown, not invented;
break-even returns "no positive break-even" rather than a fake number; every
derived value is labeled `modeled_estimate`. 15 hand-computed tests in
`backend/tests/test_roi.py`.

## 5. Competitive differentiation

1. **Net-receive correctness** — exact-decimal, incentive-eligibility-aware,
   missing-data-honest (competitor dashboards routinely zero unknown fees).
2. **Evidence, not vibes** — every recommendation carries a reason log,
   regulatory citations, and a reproducible quote ID bound to settlement.
3. **Compliance-first routing** — holds are structural (cannot be routed
   around), demo scenarios prove it (evaluation scenarios D & G).
4. **Corridor-as-config** — a new corridor is a JSON file; KSA→BD ships as proof.

## 6. Validation plan (summary — full kit in [business-validation.md](business-validation.md))

Riskiest assumptions to kill first (ordered):
1. MTO operators will route ≥ 50% of eligible volume through a third-party API
   (adoption_rate — the single biggest ROI lever).
2. Operators can share real all-in cost baselines (else the ROI model has no
   honest input).
3. UAE SME operators will buy without enterprise procurement friction.
4. Per-execution pricing is acceptable (vs flat SaaS).
5. Recipients/operators value the incentive-eligibility explanation enough to
   pay for the intelligence rather than the transfer itself.

Kill criteria: if discovery shows operators insist on in-house builds (3) or
flat pricing (4), pivot pricing model A; if baseline cost data is unavailable
(2), sell compliance/audit value, not savings.
