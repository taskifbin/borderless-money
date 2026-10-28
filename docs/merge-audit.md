# Merge audit — PR #2 `feat/frontend-redesign` → `main` (2026-10-28)

Audited **before touching anything**, per the merge policy: logic and trust
win over styling.

## 0.1 — Hardening commits on main (must survive)

| Item | SHA | Subject |
| :--- | :--- | :--- |
| B2 | `fa23002` | include platform fee in first true-net call |
| F1 | `aa9f3f2` | pre-select backend is_best route + ranking label |
| F2 | `5138779` | relabel corridor as simulated, remove live-data claims |
| F3 | `04ca7b5` | compliance banner conditional on quote.decision |
| F4 | `cc83def` | remove/bind hard-coded stats contradicting config |
| F5 | `f5a6f13` | i18n: every user-facing string (en+bn), /roi Bangla |
| F6 | `d91b6e0` | manual QA record (375 px, mic) |
| F7 | `41f58bf` | scenario URL verification |
| F8 | `a38cb81` | API-down + Retry, "Waking up…" cold-start state |
| F9 | `4ea4edf` | remove manus-routes.json, unify xPay brand |
| B4 | `d9e0bcb` | source-or-assumption labels (sources.md) |
| B5 | `e559e6f` | RAG traceability record |
| 5.1 | `e337961` | compliance token floor + real-SDN workload |
| 5.3 | `75c975e` | forfeited bonus on ineligible RouteCards |

## 0.2 — What the branch actually is

Fork point: `13599c8` (the pre-hardening baseline of the Oct-28 run).
Single commit `403c277` touching **7 frontend files only**
(+1,514/−193): `globals.css`, `page.tsx`, `roi/page.tsx`,
`components/AgentPipeline.tsx` (new), `components/ChainTrail.tsx`,
`components/MicButton.tsx`, `lib/api.ts` (+5: a `fmtCurrency` helper).
**No backend, test, or docs file is modified relative to the fork point** —
the alarming `git diff main..branch` numbers were "branch lacks main's 24
commits", not reverts. B2/B4/B5/5.1 backend code is not at risk from the
branch itself; the risk is that main's frontend hardening (F1–F8, 5.3) is
absent from the branch's rewritten components and must be re-injected.

## 0.3 — Regressions found in the redesign (to fix during merge)

| Check | Finding | Severity |
| :--- | :--- | :--- |
| **F1** | `bestPossible` is a client-side sort by raw `true_net_receive_bdt` (`page.tsx:697-703`) instead of `quote.routes.find(r => r.is_best)` — pre-selects the teaser rail over the EV winner | **logic** |
| **F2** | "Live Corridor Status Badge — **Active Rail Feed**" (Topbar); "**live** payout rails" (AgentPipeline:33); "**Real-time** Push-to-Card" badge; "Guaranteed Recipient Net Receive · No Hidden Spreads"; footer "incentive **verified**"; sidebar "Engine Operational / cryptographically bound" | **trust** |
| **F3** | "Pre-Screening Cleared" banner is **unconditional** (`page.tsx:820-832`) — no `quote.decision` check | **logic/trust** |
| **F4** | Stats `~2 hr Fastest Arrival` and `100% OFAC Screened` (contradict config: 1 hr rail, 60 min expiry, curated benchmark not 100%) | trust |
| **F5** | Redesign uses `t.*` for some strings but inlines many EN strings (scenario labels, form labels, quote inspector, AgentPipeline, review/receipt); `roi/page.tsx` forked pre-i18n; font stack drops Inter/Noto Sans Bengali | completeness |
| **F8** | No API-down message, no Retry, no "Waking up…" state; `send()` reverts to the old inline bn/en expired-message ternary | completeness |
| **5.3** | Ineligible RouteCards show "— Non-eligible Rail" without the forfeited-bonus amount | completeness |
| **NEW fabrication** | ChainTrail prev/next blocks show "Block #742918" / "Block #742920" — specific fake chain data; was honest "···" | **trust** |
| **NEW fake control** | Corridor switcher lists Malaysia/KSA but **never passes a corridor to the API** — selecting "Malaysia → Bangladesh" still returns the AED→BDT quote. Also: showing Malaysia numbers in the UI is on the permanent cut list, and ksa/my configs are unsourced fixtures | **trust/cut-list** |
| F9 | `manus-routes.json` present on branch (untouched from base) — main's deletion auto-wins at merge; brand string is xPay ✓ | expected OK |

## 0.4 — Resolution policy (per task instructions)

- **Logic files/behavior**: main's version wins — `is_best` pre-selection,
  conditional banner, simulated labels, config-bound stats, F8 states,
  forfeited bonus, i18n keys.
- **Presentation**: redesign's dark styling wins — `globals.css`, layout,
  `AgentPipeline` component, RouteCard/Topbar/Shell markup — with the
  hardening strings/conditions re-applied on top.
- **Corridor switcher**: removed entirely (fake control + cut-list item);
  the demo stays UAE→BDT, matching the one priced corridor.

## 0.5 — Merge mechanics

`git merge main` on `feat/frontend-redesign` (no `-X ours/theirs`), manual
resolution expected in: `page.tsx`, `roi/page.tsx`, `globals.css`,
`ChainTrail.tsx`, `MicButton.tsx`, `api.ts`. `i18n.ts` merges clean (branch
didn't touch it; main's superset survives, then gains the redesign's keys).
Post-merge: Phase 2 checklist + live browser run (en/bn, 375 px, scenarios,
F8 states), full backend suite (126 tests) + sanctions/RAG evals + frontend
build, then push the branch and merge PR #2 with a merge commit.
