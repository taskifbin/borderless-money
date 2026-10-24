# Borderless Money — One-Pager

**FinSphere AI · Challenge: Borderless Money — Cross-border payments and remittance intelligence**
**Team CTRL V** (5 members) · Idea to Unicorn · International AI Builders Congress 2026

---

## 1. Problem & user

Bangladesh received **$35.56 billion** in remittances in FY2025-26 — **$4.58 billion** of it from the UAE corridor alone *(Bangladesh Bank)*. A worker sending AED 1,000 home loses 3–6% to exchange-rate spreads and stacked fees — and almost no app shows the **2.5% government cash incentive** the family is entitled to on formal-channel remittance. The user: **Rahim, a construction worker in Dubai**, sending to his mother's bKash in Dhaka on a mid-range Android, often in Bangla, often by voice.

## 2. Solution & differentiator

Borderless Money is a **net-receive router**: say or type the transfer in Bangla, English, or Arabic, and it ranks every viable rail by the taka that actually arrives — fees out, **government incentive in**. One sentence: *no other app optimizes for what arrives, because it is the only one that computes the 2.5% incentive into the route choice.* On AED 1,000, the recommended rail delivers **৳33,488.80 vs ৳32,432.40 over SWIFT (+3.26%)**.

## 3. System flow

Voice/text → multilingual intent parser → corridor graph scorer (NetworkX: rails × payout legs, priced end-to-end) → pre-settlement risk (GNN + OFAC fuzzy screening with human review) → execution (Stellar testnet hybrid anchor; simulated hash when keys are absent, always labeled) → receipt with audit hash and ISO 20022 payload. PII stays off-chain.

## 4. AI approach

- **Intent parsing:** rule-based multilingual parser (Bengali/Arabic numerals, code-switching, transliterations) — deterministic where money is involved. **Measured: 100% on a 49-utterance curated en/bn/ar benchmark.**
- **Orchestration:** LangGraph state machine over **deterministic Python tools — the LLM never does arithmetic**, which is how we prevent hallucinated money. (Runs with an identical sequential fallback.)
- **Routing:** corridor graph priced by the True Net Receive engine; corridors are config files (`uae_bd.json`, `ksa_bd.json`) — a new corridor is a new file, not code.
- **Risk:** trained 2-layer GCN over transaction subgraphs (held-out **AUC 0.9038 on a labeled synthetic benchmark** — prototype evidence, not production effectiveness; `ml/eval.json` publishes the class-error analysis, and `ml/ablation.md` shows a simple linear rule matches it) + OFAC fuzzy matching (recall 100%, false-hold 0% on our labeled set) with holds-not-blocks human review.
- **RAG:** regulatory corpus (Bangladesh Bank circular excerpts, OFAC FAQ, ISO 20022) grounds every decision with **cited passages** (`regulatory_basis` in the API response).
- **Personalisation:** corridor defaults, recipient registry, language preference (persisted).

## 5. Bangla localisation

Full **bn UI toggle on all four screens** (persisted), Bangla voice input, and the intent parser handling Bengali numerals ("২ হাজার টাকা"), inflections, and Banglish transliteration ("dui hajar taka bkash e pathao"). The quote screen renders identical numbers in both languages.

## 6. KPIs (all measured — `GET /metrics`)

| KPI | Value | Target |
| :--- | ---: | :--- |
| Net-receive uplift vs SWIFT | **+3.26%** | ≥ 3.0% |
| Intent accuracy (curated en/bn/ar benchmark) | **100%** | ≥ 95% |
| p95 quote latency (engine) | **~1.3 ms** | ≤ 3 s |
| Compliance false-positive hold rate | **0.0%** | ≤ 2.0% |
| OFAC screening recall | **100%** | 100% |
| GNN test AUC (synthetic benchmark — prototype evidence, not production effectiveness) | **0.9038** | ceiling ≈0.94; linear-rule baseline matches (0.9185) |

## 7. Team, NRB, business model & roadmap

Team CTRL V — Taskif Bin Parves, Wasik Ahmed, Fahim Ahmed, Sukonya Dutta Pushpa (Captain), Alisha Akter — covering AI orchestration, RegTech/data, routing/incentive, frontend/UX, and backend/Stellar. NRB advisor: outreach in progress — confirmed by Oct 30 or the claim is omitted from the submission entirely.

**Business model (assumptions sized for the pilot — full model in docs/unit-economics.md):** senders pay a **flat AED 2.00** per transfer (a fifth of incumbent fees); exchange-house/MTO partners pay a **0.15% take rate on principal** for the routing + compliance API; bKash/Nagad pay nothing (they earn last-mile volume). Variable cost ≈ AED 0.15/transfer → **≈96% gross margin**. **CAC ≈ AED 8** via employer/exchange-house partnerships (payback < 1 month). **10,000 senders in 6 months** at 2 transfers/month ≈ AED 17M monthly volume → **≈ AED 65,500 monthly gross revenue / 62,500 gross margin**. Marginal cost of a new corridor: 2 engineer-weeks + one compliance review (rules are config files — KSA ships as the proof). Our revenue never touches the 2.5% government incentive — it belongs to the beneficiary.

Roadmap: pilot with one UAE MTO → three corridors (UAE, KSA, Malaysia → Bangladesh; KSA config already shipped) → B2B Remittance-as-a-Service API for bKash/Nagad partners. 10,000 senders in six months.

---

*Honesty statement: quotes are simulated snapshots; settlement runs on Stellar testnet (or a clearly labeled simulated hash); payout rails are mocked; GNN/regulatory evals are synthetic/curated benchmarks. Production integration replaces each labeled surface one-for-one.*
