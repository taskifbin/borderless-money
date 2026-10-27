# xPay × AI Builders Congress — Competition Analysis

Verified against the live event page (cloudcampbd.com/ai-builders-congress, fetched 2026-10-24). Where a fact comes from the advisory rather than the page, it is marked **[verify in portal]**.

## What the event actually is

| Fact | Value | Source |
| :--- | :--- | :--- |
| Event | International AI Builders Congress 2026 — "Build Products. Create Jobs. Grow Economies." | page |
| Congress day | **Dec 26, 2026**, Daffodil International University, Ashulia, Dhaka | page |
| Builder journey | Jul 1 → Dec 26, 2026 (six months) | page |
| Scale | **3,500+ participants · 600+ teams** (recent reporting; verify live count in the portal before citing on camera) | advisory update |
| Domains | 11 × 5 challenges (55 total); **FinSphere AI** = "Inclusive, secure financial intelligence — credit, fraud defense, wealth, SME capital, and borderless money movement" | page |
| **Our challenge** | **"Borderless Money — Cross-border payments and remittance intelligence"** (a named FinSphere AI challenge) | page |
| Competitions | Idea to Unicorn (preliminary **Jul 1 → Oct 31, 2026**) + Zero to Launch (Oct 15 → Nov 15, live build) | page |
| In-person judging | ~14 teams/panel · 1 min transition + **3 min pitch** + 1 min scoring | page |
| Prizes | **~1M BDT cash confirmed by DIU press release; incubation, NRB connections, and investor access are portal-dependent — do not state as confirmed until seen in the submission terms** | advisory update |

## The published judging rubric (normalized 0–100, min 5 judges)

| Criterion | Weight | What judges look for | Our evidence |
| :--- | ---: | :--- | :--- |
| **Innovation** | 20% | Non-obvious AI application; breakthrough vs incremental | True Net Receive optimization incl. the 2.5% incentive — genuinely non-obvious, locally grounded |
| **Technical Execution** | 20% | Architecture, AI integration depth — **"LLMs, ML, RAG, multimodal"** named explicitly — robustness, **explainability of the intelligence core** | LangGraph orchestrator over deterministic tools, trained GNN (AUC 0.90, **synthetic** benchmark — prototype evidence, class-error analysis + baselines published) + stand-in default, **RAG over Bangladesh Bank/OFAC corpus with `regulatory_basis` citations**, OFAC fuzzy + human review, ISO 20022 |
| **Business Model + Global Readiness** | 20% | Monetization, adoption pathway, cross-border viability | B2B RaaS API, take-rate hypothesis, **config-driven corridors (uae_bd + ksa_bd prove multi-corridor without code changes)** |
| **Real-World Impact + Ethical AI Compliance** | 20% | **"Measurable outcomes or KPIs"**, responsible data, bias mitigation, transparency | **`GET /metrics` returns five measured KPIs** (computed from in-repo eval sets); holds-not-blocks compliance; PII off-chain; honesty labels |
| **Scalability + NRB Collaboration** | 10% | Cloud readiness, modular design, **NRB/global collaboration** | Corridor abstraction, containerizable, hosted URL planned; **NRB advisor = the one open gap** |
| **Presentation** | 10% | Storytelling, demo effectiveness, explaining AI decisions | Reasoning surfaced in product copy; 5-segment video script (docs/demo-script.md) |

**Reading:** Technical Execution + Impact = 40% of the score, and the rubric literally names RAG, KPIs, and explainability — the four upgrades just added (RAG, `/metrics`, trained GNN, corridor config) are direct rubric coverage, not feature creep. The weakest cells are **Business Model packaging** and **NRB collaboration**.

## Gap analysis (post-upgrades)

| Requirement | Status | Remaining work |
| :--- | :--- | :--- |
| Defined problem & user | Strong | Open the video with corridor stats (verify figures vs Bangladesh Bank releases first) |
| AI-native approach | **Strong** | — |
| System flow | Strong | — |
| Initial demo | Strong locally | **Host a public URL** (Vercel + Render/Fly, or docker compose) |
| Bangla localisation | **Strong** | bn toggle shipped on all four screens, persisted in localStorage; parser handles bn numerals/words |
| Measurable KPIs | **Strong** | `/metrics` returns measured values; targets in docs/kpis.md |
| Differentiation | Strong | State it in one sentence, not a formula |
| Business potential | Weak→Medium | One-pager economics section (docs/one-pager.md); rehearse the take-rate answer |
| Global scalability | **Strong** | ksa_bd stub + `/api/health` lists corridors — show it for 3 seconds in the video |
| Responsible AI | **Strong** | Holds-not-blocks + audit hash + citations; put it in the video at 1:30–2:00 |
| **NRB collaborator** | **Open** | Outreach this week; the rubric awards it inside the 10% Scalability criterion |
| "Mocked GNN" flank | **Closed** | Trained GCN shipped with honest eval (docs/kpis.md); stand-in still the safe default |

## Review of the advisory (what we adopted, what we corrected)

**Adopted:** video-first priority; NRB outreach as a delegated non-technical task; Bangla UI toggle; measured KPIs; RAG (rubric names it); corridor config; honest GNN framing; submit with buffer.

**Corrected / verified against the live page:**
1. The advisory's **five 30–60s video segments are not on the public page** — the page publishes the six criteria above and a 3-minute in-person pitch format. Treat the 5-segment cut as good discipline; confirm exact portal requirements (video length, public/unlisted) before recording.
2. **KPI honesty:** the advisory suggests "≥95% intent accuracy" — ours is **measured at 100% on a curated 49-utterance en/bn/ar benchmark** and labeled as such (not production statistics). Never present curated-benchmark numbers as production metrics.
3. **+3.2% uplift checks out:** computed 3.26% (AED 1,000: ৳33,488.80 vs SWIFT ৳32,432.40).
4. The corridor figures — **$35.56B FY2025-26 total, $4.58B UAE corridor** — were confirmed by the team and are now filled into `demo-script.md` and `one-pager.md`. Keep the Bangladesh Bank release link citable in Q&A; re-verify the link resolves before recording day.
5. Config format: advisory said YAML; we used **JSON** so the whole engine + tests stay stdlib-only (schema identical to the suggested one).
6. "Don't spend the week adding features" — right instinct, but 4 of the 5 suggested upgrades map 1:1 to published criteria; that's submission work. The one we'd have skipped if short on time was GNN training — done anyway with an honest eval.
7. **Missed by the advisory:** the congress also runs **Zero to Launch** (500 finalists, 1-hour live build, Oct 15–Nov 15 preliminary) — **decision (Oct 24): xPay is NOT entering Zero to Launch.** We have no dedicated sub-team; a live-build format would cannibalize the video, NRB outreach, and recording time in the only week that matters. The team lead records this call so nobody relitigates it on Day 5. Revisit only if the preliminary is submitted early (Oct 29) AND a two-person sub-team volunteers — otherwise closed.
8. **Business model was the thin 20%** — fixed Oct 24: the one-pager now carries the unit-economics model (flat AED 2 + 0.15% partner take rate, AED 8 CAC, 10K senders → ~AED 65K monthly gross margin, all labeled assumptions); full model in [docs/unit-economics.md](unit-economics.md). The in-person round is a stand-up performance — [docs/pitch-script.md](pitch-script.md) drafts the 3-minute spoken pitch now, rehearsed twice.
