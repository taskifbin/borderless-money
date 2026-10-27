# The eight hard questions — 20-second answers

Every answer is grounded in a file in this repo. Answers marked **TODO:
depends on …** cannot be fully answered until that artifact exists — say the
honest sentence instead of improvising.

1. **Is your headline model just a rebrand of a simpler one?**
   No — and we ship the ablation that proves we asked the question ourselves:
   `ml/ablation.md` shows a simple linear rule MATCHES the trained GCN on this
   data (same split), so the explainable rule is the shipped default and the
   GCN is opt-in with a published class-error analysis (`ml/eval.json`). The
   differentiator is not the model anyway — it is computing the 2.5% incentive
   into the route choice (`backend/app/services/incentive.py`,
   `docs/FINANCIAL_MODEL.md`).

2. **Why trust your numbers?**
   Every headline is computed by `GET /metrics` from in-repo eval sets with the
   methodology in the payload; the uplift is +3.05% recomputed after our own
   AED 2 platform fee is included (`test_financial.TestPlatformFee` asserts the
   fee is subtracted exactly once), corridor inputs carry provenance
   (`data/sources.md` — everything UNVERIFIED is labeled as such), and the
   sensitivity table shows where the headline breaks
   (`docs/stellar-sensitivity.md`). **TODO: depends on survey** for any
   user-side number.

3. **Does your differentiator apply to every route?**
   No — and the config flag is visible: the incentive applies only to rails
   marked `incentive_eligible` in `backend/config/corridors/uae_bd.json`; the
   promo Cash Pickup rail has the best headline FX and still loses because it
   earns zero incentive (`tests/test_step4.py::test_incentive_flag_flips_the_winner`).

4. **Who holds the license / who is accountable?**
   Nobody yet — honestly. xPay is a hackathon prototype, not a licensed
   money-services business; settlement is simulated by design and payout rails
   are mocked (`README` disclaimer, `docs/responsible-ai.md`). Accountability
   in the demo = the audit log, the reasoning log on every decision, and the
   named human-review SLA; production accountability requires the licensed
   entity we do not have.

5. **Why not the incumbent / a global remittance app?**
   Scoped answer: the incumbent tools we checked show fees and rates; we found
   none that computes the 2.5% incentive into the route choice
   (`docs/competitive-scan.md` — **TODO: depends on scan**; if a judge names
   one, we ask to see it and will say so on stage). Our wedge is the incentive
   math plus the corridor-config model, not a faster horse.

6. **What happens when the safety check is wrong?**
   Two-sided answer: a TRUE hit never auto-clears (recall 11/11 on
   `make eval-sanctions`, leet-obfuscation included), and an innocent name is
   never auto-blocked on an alias — alias-only matches are held for review
   because we collect no second identifier. The user sees the rationale in
   plain language, a human releases or rejects within the stated 24-hour SLA,
   and the operational load is measured at 8 reviews per 1,000 transfers
   (`reports/review_volume.json`).

7. **What did real users say?**
   **TODO: depends on survey** — the instrument is drafted in
   `docs/validation/survey.md`; until n≥15 responses exist, the honest answer
   is: "we have the questionnaire and the collection plan; we will not invent
   user data." If the survey lands before recording, cite the counts from that
   file only.

8. **What is real and what is simulated?**
   Read from `REAL_VS_SIMULATED.md` verbatim: the money math, ranking,
   compliance logic, quote lifecycle and idempotency are real and tested; FX
   rates and fees are labeled snapshot fixtures; settlement is simulated by
   design (testnet-ready adapter, never shown as a real ledger transaction);
   the sanctions list is a 10-entry local sample; the GNN benchmark is
   synthetic. Every simulated surface is labeled in the UI.
