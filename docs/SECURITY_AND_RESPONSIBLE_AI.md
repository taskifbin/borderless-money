# Security & Responsible AI

**Status: implemented safeguards described precisely; remaining risks stated
bluntly. Nothing here claims certification, accreditation, or regulatory
compliance — this is a hackathon-grade prototype with honest boundaries.**

## 1. Threat model (abridged, STRIDE-flavored)

| Threat | Vector | Safeguard in this repo | Residual risk |
| :--- | :--- | :--- | :--- |
| Spoofed caller | Unauthorized execute/quote | Optional API key (`BORDERLESS_MONEY_API_KEY` → `X-API-Key` required on private endpoints); no auth by default because the demo must run zero-setup — **documented, deliberate** | Default-open deployment is a footgun for production; add real authN (OIDC/mtls) before any real data |
| Duplicate settlement | Retry storms / double-click | `Idempotency-Key` (first response wins, replays labeled); quotes single-use (`quote_already_used`) | Idempotency store is in-memory/SQLite per process — multi-node needs shared store |
| Stale pricing | Executing an expired quote | Quote TTL + revalidation gate; `quote_expired` refusal (scenario C) | Clock skew across nodes untested |
| Rate abuse / DoS | API flooding | Per-IP fixed-window limiter (default 240/min, `/api/health`+`/api/ready` exempt), structured 429 | In-memory limiter resets on restart; no global (multi-IP) quota |
| Log-based PII leak | Names/handles in logs | Explanation logs carry route/amount figures, not party names; demo personas are fixtures, not real people | Demo store persists full receipts (names + handles) — acceptable for fixtures, NOT for real users |
| Prompt injection | User text steering the LLM | Deterministic pipeline: the LLM (a) is OFF by default, (b) only parses when the rule parser fails, (c) is schema-validated, (d) can never override compliance holds or routing math; scenario G proves injection phrasing cannot bypass the sanctions gate | If the LLM fallback is enabled, parsed amounts deserve human confirmation in production |
| Sanctions false negative | Fuzzy matcher misses a variant | Documented honestly: the matcher is a prototype on a **sample** list (10 entries); it is NOT a legal screening system; the GNN score is a prototype risk signal, never a legal determination | Real deployment needs licensed list data + vendor screening or in-house sanctions ops |
| Config tampering | Corridor JSON edits changing financials | Corridor files are repo-versioned; math is exact-decimal with documented formulas + tests; missing pricing can't settle | No runtime integrity check (signing corridor configs is future work) |
| Secret leakage | Keys in repo/env | No secrets in the repo; LLM/testnet keys only via env; demo API key examples are labeled `demo-not-production` | — |

## 2. Execution safeguards (the part judges test)

- Compliance hold is **structural**: `execute` runs only when the decision is
  `CLEAR`; held/blocked transactions flow to an audit record with
  `hold_reason` and move no money. No orchestration path (LangGraph or
  sequential fallback) can reach settlement otherwise — both runners share the
  same node functions.
- Quote binding: settlement uses the exact quoted numbers; expired / consumed /
  mismatched / unconfirmed quotes are refused (evaluation scenarios C, F).
- Uncertain settlement is never success: `RECONCILIATION_REQUIRED`, no hash,
  explicit log line (scenario F).
- Unpriced routes refuse to settle (`incomplete_pricing`); pacs.008 raises
  rather than invent a settlement amount.

## 3. Responsible-AI documentation

**Intended use:** decision support for comparing eligible remittance routes and
explaining the recommendation, in corridors configured by the operator.

**Out-of-scope use:** legal compliance determinations; autonomous execution
without human confirmation; consumer credit/risk scoring; screening real
parties against the sample sanctions list as if it were authoritative.

**Known failure modes & limitations:**
- *Risk model:* the shipped GCN is trained on a **synthetic** benchmark
  (`ml/eval.json`: held-out AUC 0.9038 with a documented ~0.94 ceiling under 2%
  label noise and 1:7 imbalance; ablation in `ml/ablation.md`). Three honesty
  constraints travel with every claim:
  1. **Generator mirroring** — the benchmark's fraud/normal feature ranges are
     the same signals the stand-in rule scores, so the metrics measure how well
     a model learns *that generator's* separability and may substantially
     overstate real-world effectiveness. Prototype evidence, not proof of
     production fraud detection.
  2. **Class-specific error analysis** (in `ml/eval.json`) — at the train-tuned
     operating threshold (0.51): TP 52 / FP 3 / FN 8 / TN 417 (FPR 0.7%, FNR
     13.3%). At the **0.8 production review gate the trained model flags
     nothing** (recall 0.0, FNR 100%) — its raw sigmoids are uncalibrated and
     never reach the policy threshold, so enabling it for review-triggering
     requires recalibration first. The deterministic stand-in remains the
     default scorer.
  3. **Split account** — 2,400 samples; single RNG stream (seed 42), first
     1,920 train / next 480 test, i.i.d. from the same generator. No graph
     leakage is possible (each transaction is an independent 4-node subgraph;
     batching merges disjoint subgraphs), but the split is per-transaction —
     NOT per-sender or temporal — so production evaluation must split by
     sender/time. Same-split baselines (`ml/ablation.md`): linear rule 0.9185,
     logistic 0.9217, boosted stumps 0.9068, GCN 0.9130 — **the simple
     explainable rule matches the deep model**, which is why it is preferred.
- *Screening:* fuzzy matching (normalized Jaro-Winkler + coverage) has
  measurable false-negative risk for transliteration variants beyond its
  normalization; thresholds are configurable but unvalidated against real-world
  name diversity. Precision/recall numbers in `GET /metrics` come from the
  in-repo benchmark (14 true hits, 14 near-variants, 21 clear names) — small,
  curated, and labeled as such.
- *Explanations:* template-grounded with a number guard (LLM paraphrases are
  rejected if they introduce numbers); Bengali templates are simpler than
  English ones.

**Human responsibilities:** a named reviewer must sign off every
`FUZZY_MATCH_REVIEW` / `HIGH_RISK_REVIEW` hold before any payout; operators own
their corridor config accuracy (fees, FX snapshot freshness, incentive rules);
operators must replace fixture data with licensed/verified data before real use.

**Appeal & correction paths (design, not yet product):** holds carry a reason
string and the matched list entry; the audit record (transaction + explanation
log) is stored and retrievable by ID, giving a reviewer everything needed to
overturn a hold. A reviewer-decision API with timestamps (spec 6.1's reviewer
sign-off records) is the next implementation step, not yet built.

**Data & privacy:** demo fixtures only; no real PII is processed. Receipts
(store + pacs.008) carry party names by design of the demo — a production
deployment must minimize (IDs not names), encrypt at rest, and set retention.
Logs avoid credentials and full identities.

**Conditions that force a hold** (implemented): sanctions `BLOCKED` (exact
match), `FUZZY_MATCH_REVIEW` (≥ threshold near-match), `HIGH_RISK_REVIEW`
(risk score ≥ policy threshold). Uncertain settlement ⇒ reconciliation, not
hold — money never moves twice.

## 4. Operational security posture

- CI (`.github/workflows/ci.yml`) runs tests + evals on every push; Docker
  image builds the full stack.
- Health (`/api/health`) + readiness (`/api/ready`) endpoints; request IDs on
  every response (`X-Request-ID`) for tracing.
- CORS is allow-listed via env (default: localhost:3000).
- Known gaps, stated plainly: no dependency vulnerability scanning yet, no
  structured JSON logging (plain strings), no mTLS/TLS termination story, no
  secrets-rotation, store has no encryption at rest. Each is pre-competition
  hardening work, not something to claim.
