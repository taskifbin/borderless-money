# Responsible AI — one page

xPay is a hackathon prototype for the AI Builders Congress (FinSphere AI track).
This page states what the system does for safety, what a human can do when it
is wrong, and — most importantly — what it does **not** claim. The detailed
threat model lives in [SECURITY_AND_RESPONSIBLE_AI.md](SECURITY_AND_RESPONSIBLE_AI.md);
the claim-by-claim truth table lives in [REAL_VS_SIMULATED.md](../REAL_VS_SIMULATED.md).

## What the safety path actually does

- **Screening, not judgment.** Every transfer screens sender and recipient
  against a local sanctions sample with a documented matcher (normalized Jaro +
  token coverage; thresholds in `backend/app/services/compliance.py`). Every
  decision carries a machine-readable rationale — matched name, score,
  algorithm, thresholds, decision rule.
- **Holds, not silent rejections.** Near-matches (score ≥ 0.90) and
  unscreenable inputs are held for human review; only canonical full-name
  equality blocks. Alias-only equalities ("Md Salim" → "Mohammad Salim") are
  **never auto-blocked** — without a second identifier (DOB / nationality),
  which this demo does not collect, an alias is not identity.
- **No LLM on the money path.** The rule-based parser and exact-decimal engine
  produce every number; the optional LLM is schema-validated, off by default,
  and its output is rejected if it invents a number (`tests/test_step3.py`).
- **Explainability by construction.** The reasoning log (intent → ranking →
  screening → execution) is returned with every response and rendered in the UI.

## Measured safety metrics (this repo, not production statistics)

| Metric | Value | Source |
| :--- | ---: | :--- |
| Recall on true list hits | 100% (11/11, exact + leet) | `make eval-sanctions` |
| Alias-only equalities auto-blocked | 0 (policy: review) | `make eval-sanctions` |
| False-positive rate on clear names | 0.0% (0/21) | `make eval-sanctions` |
| Review volume on common names | 8 reviews / 1,000 transfers | `reports/review_volume.json` |
| GNN false-hold rate | 0.0% on the labeled eval set | `GET /metrics` |

## When the gate is wrong: the appeals path

1. A held transfer surfaces `FUZZY_MATCH_REVIEW` **with its rationale** — the
   user is told what matched and why, in plain language (en/bn).
2. A human reviewer sees the same rationale plus the raw names and score.
3. The reviewer can release (proceed) or reject; the decision is appended to
   the audit log. In this demo the "review" is the `REVIEW` screen — there is
   no reviewer console, which is exactly the kind of gap production must fill.
4. Documented human-review SLA: 24 hours (stated in the UI review screen).
5. **PII minimization:** PII never touches a ledger — only hashes and
   non-identifying audit data (`docs/SECURITY_AND_RESPONSIBLE_AI.md`).

## What this project does NOT claim

- **Not a sanctions-compliance system.** The list is a 10-entry local sample,
  not the OFAC SDN export. The matcher is not a legal screening tool and has
  never been validated against real sanctions data.
- **Not fraud detection.** The trained GNN is prototype evidence on a
  *synthetic* benchmark (AUC 0.9038; a linear rule matches it — `ml/ablation.md`).
  The explainable deterministic rule is the shipped default.
- **Not production pricing.** All FX/fees are labeled fixture snapshots
  (`data/sources.md`: everything UNVERIFIED until sourced). The uplift
  headline is a scenario, not a constant (`docs/stellar-sensitivity.md`).
- **Not a licensed money-services business.** No regulatory approvals exist;
  settlement is simulated by design, and payout rails are mocked.
- **No user data was collected.** The "users" in evals are fixture personas;
  the review-volume names are synthetic combinations of common names.

## Before any production use (the honest list)

Real authN (the demo API is open by design), an official sanctions feed with
re-measured review volume, a real second-identifier check before blocking,
a deployed reviewer console with the appeals SLA backed by staff, licensed
payout integrations, and a privacy review. None of these exist in this repo,
and nothing in the docs pretends otherwise.
