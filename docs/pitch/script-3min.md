# 3-minute pitch — in-person round (Dec 26) / video cut

**Grounded numbers (all recomputed Oct 27, traceable in-repo):** best route
net ৳33,423.20 on AED 1,000 incl. xPay's AED 2 fee · legacy SWIFT ৳32,432.40 ·
uplift +3.05% (survives to +2.59% at a 1.5% anchor spread —
`docs/stellar-sensitivity.md`) · recall 11/11, review volume 8/1,000
(`reports/review_volume.json`) · p95 21.2 ms end-to-end
(`reports/load_test.txt`).

*(The longer cut with stage directions lives in docs/demo-script.md; the spoken
in-person version is docs/pitch-script.md. This file is the canonical 3-minute
structure both must match — update numbers HERE first.)*

## 0:00–0:30 · Rahim's problem (concrete user story)

> Rahim builds scaffolding in Dubai. He sends AED 1,000 home to his mother's
> bKash every month. His exchange house takes its fee, hides a worse rate in
> the spread — and nobody tells him the government pays his mother a 2.5% cash
> incentive for formal remittance. Multiply that gap by [TODO: Bangladesh Bank
> FY2025-26 figure — $35.56B claimed in docs/one-pager.md; SOURCE NEEDED:
> attach the BB release URL before recording].

## 0:30–1:00 · What xPay is

> xPay is a net-receive router. Say it — in Bangla, English, or Arabic — and it
> ranks every rail by the taka that actually arrives: fees out, including our
> own flat two-dirham fee shown as a line item; government incentive in. On
> Rahim's 1,000 dirhams the best rail delivers 33,423 taka where legacy SWIFT
> delivers 32,432 — 991 taka more, in two hours instead of twenty-eight. The
> differentiator isn't a prettier rate table: to our knowledge it's the only
> tool we found that computes the incentive into the route choice itself.

## 1:00–1:45 · Live demo of the hard cases

> *(Type the demo sentence.)* They receive 33,423.20. *(Switch to the SWIFT
> rail — the app itself says 991 taka less arrives.)* Now the honest part:
> sanctions screening holds a near-match for a human instead of silently
> blocking — every decision shows its own rationale. And when settlement is
> uncertain, the receipt says RECONCILIATION REQUIRED — never fake success.

## 1:45–2:20 · How it's built (fast)

> An orchestrator over deterministic tools — the LLM never does arithmetic, so
> it cannot hallucinate money. Exact-decimal money math, quote lifecycle with
> single-use binding and idempotency keys. Corridors are config files: UAE
> today, KSA and Malaysia already load as pure config. Every number we just
> said is computed by `GET /metrics` from this repository — not invented.

## 2:20–3:00 · Honest limits & the ask

> What is simulated: settlement, FX snapshots, the sanctions sample. What is
> real: the math, the ranking, the compliance logic, the tests — 90+ of them,
> green on a fresh clone. The uplift survives until the anchor spread passes
> about 1.1%; at 1.5% it is +2.6%, and we say so. Pilot: one UAE exchange
> partner, three corridors. We are CTRL V — xPay, built in Dhaka, for the
> world.

---

**Before recording (checklist):**
- [ ] Attach the Bangladesh Bank release URL for the market-size figure
- [ ] Fill `docs/competitive-scan.md` (5 alternatives) or keep "the only one we found" scoping
- [ ] Fill `docs/validation/survey.md` if responses exist; else drop "users told us" lines
- [ ] NRB decision per `docs/nrb/README.md` (Oct 30): cite the note or drop the claim
- [ ] Re-run `make scenarios` and sync any changed numbers into this file
