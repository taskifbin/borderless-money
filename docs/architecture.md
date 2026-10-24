# Borderless Money — System Architecture

Two-layer agentic orchestration over a deterministic Python scoring engine. The LLM
agent never does math itself — it *calls tools* and *explains* their output. That is
the whole design idea: **agency on top, determinism underneath.**

```text
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  📱 Web App (Next.js)  │  🎤 Voice (Web Speech API / Whisper)   │
│  📞 USSD Gateway (feature phones, planned) │ 🔌 B2B RaaS REST   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           LAYER B: AGENTIC ORCHESTRATOR (LangGraph)              │
│                                                                  │
│   parse_intent → score_routes → check_compliance                 │
│                        │ (conditional gate)                     │
│              ┌─────────┴──────────┐                             │
│              ▼                    ▼                              │
│         execute            explain_decision ──→ reasoning log   │
│                                                                  │
│   If LangGraph is not installed, an equivalent sequential        │
│   orchestrator runs the same node functions.                     │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            LAYER A: SCORING & EXECUTION ENGINE (Python)          │
│  📊 routing_scorer.py   corridor rail pricing, EV ranking        │
│  🛡️ gnn_risk.py         PyTorch Geometric GCN + stand-in infer   │
│  ⚖️ compliance.py        OFAC fuzzy matching, ISO 20022 mapping  │
│  💱 incentive.py        True Net Receive + 2.5% BD incentive     │
│  ⛓️ stellar.py          Testnet path payment (or simulated)      │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATA & INTEGRATION LAYER                       │
│  data/fx_rates.json (snapshot)  data/ofac_sample.json (local)    │
│  data/recipients.json (mock bKash/Nagad registry)                │
│  db/schema.sql (PostgreSQL)  ·  store.py (memory/SQLite demo)    │
└─────────────────────────────────────────────────────────────────┘
```

## Layer B — Agentic Orchestrator (`backend/app/agent/orchestrator.py`)

A LangGraph `StateGraph` over a typed `AgentState`:

| Node | Tool it calls (Layer A) | Output in state |
| :--- | :--- | :--- |
| `parse_intent` | `intent_parser.parse_intent` | `parsed_intent` |
| `score_routes` | `routing_scorer.score_routes` | `routes` (ranked, True Net Receive) |
| `check_compliance` | `gnn_risk.pre_settlement_check` + `compliance.screen_transaction` | `risk`, `compliance`, `decision` |
| `execute` *(gated)* | `stellar.execute_path_payment` + `store` + `compliance.to_pacs_008` | `execution`, `transaction` |
| `explain_decision` | — (composes from state) | `explanation_log` |

**Gate rule** — `execute` runs only when: mode is `execute` AND decision is `CLEAR`.
Anything else flows straight to `explain_decision` with the hold reason. Blocked or
reviewed transactions never touch a payout rail.

**Why this matters for judges:** the explainer emits a step-by-step plain-language
reasoning log (intent → ranking → incentive → RegTech verdict → execution). Explainable
AI is a scoring criterion, and the log is rendered verbatim in the UI.

## Layer A — Scoring & Execution

### Routing Scorer (`services/routing_scorer.py`)
Every rail, FX rate, fee, and last-mile rule lives in the corridor config
(`config/corridors/<code>.json`) — a new corridor is a new file, not code.

- Rails (UAE→BD): `Traditional SWIFT`, `Stellar Hybrid Anchor`, `Exchange House
  MTO`, `Stellar Multi-hop (AED-USD-BDT)`, and a `Cash Pickup Agent (teaser
  rate)` sample that is **incentive-ineligible** — it wins on raw numbers and
  loses once the 2.5% incentive and expected value are applied, demonstrating
  the eligibility flag as real routing logic
- Payout legs: `bkash`, `nagad`, `bank` (each rail pays a different last-mile
  partner fee — SWIFT reaching bKash is the expensive case)
- Each route is priced end-to-end (rail fee/FX/hours + last-mile leg), the
  incentive applies **only to eligible rails**, and routes are ranked by
  **expected value (true net × success rate)**; a naive cheapest-fee baseline is
  exposed in `/api/routes/compare` alongside the winner, with FX `as_of`
  timestamps and a live Horizon reachability probe in `data_sources`.

### Incentive Engine (`services/incentive.py`)
Pure, dependency-free, exactly testable:

```
gross_bdt          = amount_aed × fx
fees_deducted_bdt  = fee_aed × fx
govt_incentive_bdt = gross_bdt × 0.025        # Bangladesh Bank circular
true_net_receive   = gross − fees + incentive
```

### GNN RegTech (`services/gnn_risk.py`)
- `RemittanceGNN` — a 2-layer GCN (PyTorch Geometric) over the transaction subgraph
  (sender / recipient / device / geo nodes; transaction-history edges) lives in the
  repo to show the production architecture.
- Demo inference uses a **deterministic stand-in** over the same features
  (device trust, account age, amount-vs-history ratio, recipient relationship,
  unusual hour, jurisdiction risk) so the demo never depends on a GPU or a checkpoint.
  Score > 0.8 → `requires_manual_review`.

### Compliance Gate (`services/compliance.py`)
- OFAC screening with `difflib.SequenceMatcher`: exact hit → `BLOCKED`,
  similarity ≥ 0.85 → `FUZZY_MATCH_REVIEW` (human in the loop, zero silent false
  rejections), else `CLEAR`. List ships as local JSON.
- ISO 20022 mapping (`to_pacs_008`) attaches a pacs.008-shaped payload to every
  executed transaction — familiar territory for banking judges.

### Execution (`services/stellar.py`)
If `stellar-sdk` is installed **and** `STELLAR_SECRET_KEY` is set, a testnet path
payment is attempted; any failure — or absence of the SDK — falls back to a
deterministic simulated hash. `network: "SIMULATED" | "TESTNET"` is always explicit,
in the API and on the receipt.

## Data Flow — Happy Path (sequence)

```text
Voice "Send 1,000 dirhams to my mother's bKash in Dhaka"
  → POST /api/agent/parse-intent        (intent: 1000 AED → BDT, BKASH, "Mother")
  → POST /api/agent/quote               (3 routes ranked; Stellar best: 33,488.80 BDT)
  → user approves route in UI
  → POST /api/agent/execute
       ├─ GNN risk 0.07 (LOW)           → pass
       ├─ OFAC CLEAR (both parties)     → pass  ── gate opens
       ├─ Stellar testnet path payment  → hash
       ├─ ISO 20022 payload + receipt   → store
       └─ explanation log               → UI
```

## Real vs. Simulated

| Surface | Real | Simulated |
| :--- | :--- | :--- |
| Incentive math (2.5%) | ✅ | — |
| Routing/fee comparison engine | ✅ | rate & fee snapshots |
| OFAC fuzzy matcher | ✅ | sample list |
| GNN model architecture | ✅ (PyG, in repo) | stand-in inference |
| Stellar settlement | ✅ testnet path | fallback simulated hash |
| bKash/Nagad payout | — | mock registry |

PostgreSQL is the production store (`db/schema.sql`); the demo store is in-memory with
optional SQLite persistence via `BORDERLESS_MONEY_DB_PATH` — zero setup for judges.
