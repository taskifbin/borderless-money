# Final gate — verification table (2026-10-28)

Every row was re-verified on the final tree immediately before the completion
report. Baseline for this run: `13599c8`; branch: `main`; commits this run: 23;
working tree clean; **nothing pushed** (per the task constraints).

| # | Gate | Check performed | Result |
| :-: | :--- | :--- | :--- |
| 1 | **Judge-visible quote path** (B2 + F1–F4, F9) | B2 identity test (`reliability_adjusted_net == displayed_net × success_rate`, exact-decimal) in the suite; live browser run: Recommended badge on the EV-winning route, ranked-by line shown, compliance banner conditional on `quote.decision`, no stray `manus-routes.json` | ✅ 126 tests OK; browser-verified (en+bn) |
| 2 | **Backend/data integrity** (B4 + B5) | `make eval-sanctions` equivalent (`eval_sanctions.py`): recall 100% (11/11), near-variant recall 100% (15/15), FPR 0% (0/21), exit 0; `eval_rag.py`: hit@2 8/8, all citations in allowed domains, exit 0; `data/sources.md`: 2 fields network-verified, provider/WB rows blocked with human-fill URLs, no invented numbers | ✅ both evals exit 0 |
| 3 | **Frontend completion** (F5–F8) | All user-facing strings in `i18n.ts` (en+bn) incl. `/roi`; 375 px class viewport: zero horizontal overflow on home + quote screens (live, production build); `?scenario=fuzzy_review` / `?scenario=high_risk` → correct hold/review banners; API-down → friendly message + Retry, "Waking up…" state >5 s | ✅ verified live, `docs/manual-qa.md` |
| 4 | **Docs synced to engine** (D1, D3, D4–D6) | README/kpis/one-pager/business-slide numbers recomputed from engine output (uplift +3.05%, sensitivity +2.59–3.63%, sim +3.53%, review volume 0/1,000 local · 40/1,000 real SDN, 21.2 ms end-to-end); engine-only latency KPI removed; deploy recorded BLOCKED (no credentials); NRB advisor left OPEN | ✅ grep sweep clean, `docs/final-gate.md` is the record |
| 5 | **Constraints honored** | Repo-root only; one commit per numbered step; git push / reset --hard / clean / branch deletion never used; no fabricated sources, numbers, provider rates, or user-validation counts (absences are labeled BLOCKED/OPEN, not invented); permanent cut list respected (no repo rename, no Malaysia numbers in UI, no graph/NetworkX claims, no timing advisor, no real testnet payment, no Whisper/USSD/new rails/new ML, no engine-only latency KPI) | ✅ 23 commits on `main`, tree clean, **not pushed** |

## Known deviations (logged, not hidden)

- **B4 partially blocked** — provider rate+fee pages and World Bank RPW are
  not machine-fetchable (JS calculators / HTTP 403); mid-market rate verified
  from two independent sources instead; exact human-fill URLs in
  `data/sources.md`.
- **D1 deploy blocked** — no credentials in this environment; blueprint ready,
  VERIFY steps documented in `deploy/render.yaml`.
- **5.4 LLM fallback blocked** — no API key; deterministic parser stays the
  shipped default; recorded in `docs/decisions.md`.
- **Corridor fixture not re-baselined** — live mid-market 33.776 vs fixture
  33.15 (~1.9%) disclosed in `data/sources.md`; re-baseline deliberately
  deferred past submission to keep every headline number stable.
- **Mic flow on Android Chrome** — requires device verification
  (`docs/manual-qa.md`); the automation browser cannot exercise
  SpeechRecognition.
