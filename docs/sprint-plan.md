# xPay — 11-Day Sprint Plan (Oct 20 → Oct 31)

> **⚠️ Superseded (Oct 24):** [submission-plan.md](submission-plan.md) v2 is now the **single critical path** — recording Oct 25–26, hosted deploy Oct 27, pitch rehearsal Oct 28, submission Oct 29. This file is kept as the historical build log: the Days 1–5 rows describe what landed in the repo, and the Days 6–11 rows are superseded by the submission plan. Do not plan from this file.

Submission deadline: **Oct 31, 11:59 PM GMT+6.** Preliminary round scoring favors a
working end-to-end flow + explainability over model sophistication — the plan below
is sequenced accordingly.

> **Repo status (Day 5, Oct 24):** the Days 1–5 foundation has landed in this repo —
> monorepo, API contracts, Layer A engines (routing/incentive, GNN RegTech, OFAC),
> Layer B orchestrator (LangGraph + fallback), FastAPI shell, PostgreSQL schema,
> Next.js flow, and a terminal demo (`backend/run_demo.py`).

| Day | Dates | Focus | Deliverable | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1–2 | Oct 20–21 | Foundation & contracts | Locked demo scenario (1,000 AED → bKash), JSON API contracts, repo initialized | ✅ done |
| 3 | Oct 22 | Routing & incentive | `calculate_true_net_receive` incl. 2.5% incentive; SWIFT vs Stellar comparison | ✅ done |
| 4 | Oct 23 | RegTech | GNN skeleton + OFAC fuzzy matcher with explanations | ✅ done |
| 5 | Oct 24 | Orchestrator + shells | LangGraph chain over the tools; FastAPI + Next.js skeletons | ✅ done (this scaffold) |
| 6–7 | Oct 25–26 | Integration & happy path | Voice → parse → quote (with incentive line) → GNN clear → testnet execute → receipt, wired in the UI | 🔜 next |
| 8–9 | Oct 27–28 | Polish & edge cases | Force `FUZZY_MATCH_REVIEW` (demo scenario), UI labels “Simulated Quote”/“Testnet Transaction”, reasoning-log panel styling | ⬜ |
| 10 | Oct 29 | Demo recording | 3-minute video per `demo-script.md`; focus on True Net Receive + voice-to-action | ⬜ |
| 11 | Oct 30–31 | Submission | Team lead fills portal, uploads video + GitHub link, submits **before 11:59 PM GMT+6** | ⬜ |

## Day-by-day owner notes (Days 6–11)

- **AI Orchestrator Lead (Day 6):** verify LangGraph mode locally (`pip install
  langgraph`) — the fallback sequential path is fine for the video either way; tighten
  intent parsing on real Bengali/Arabic voice samples.
- **Routing & Incentive Lead (Day 6):** sanity-check route snapshots against live
  corridor rates; update `data/fx_rates.json` + rail constants the morning of the
  recording.
- **RegTech Lead (Day 8):** rehearse the fuzzy-review scenario; make sure the
  explanation log reads like an analyst brief, not a stack trace.
- **Frontend Lead (Days 6–9):** wire all four steps; the incentive line must be
  visually the loudest green on the comparison screen; print-friendly receipt.
- **Backend & Stellar Lead (Day 6):** run the Stellar testnet path once with real
  testnet keys (`STELLAR_SECRET_KEY`) so the receipt hash links to
  stellar.expert; otherwise ship the simulated hash (labeled).

## Pro-tips carried from the plan

1. **NRB collaborator:** confirm the “3–5 members + 1 NRB advisor” slot — an NRB
   professional as Advisor strengthens the global-scalability story.
2. **Fake it gracefully:** the GNN stand-in inference is a feature of the demo, not a
   secret — say “deterministic stand-in, production graph model is in the repo.”
3. **Explainability is the secret weapon:** every screen that moves money must show
   its reasoning log entry.
