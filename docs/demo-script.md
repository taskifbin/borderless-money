# Borderless Money — 3-Minute Video Script (rubric-aligned cut)

Mapped to the six published judging criteria (Innovation, Technical Execution, Business Model, Impact + Ethical AI, Scalability + NRB, Presentation). All numbers below are the system's actual measured outputs — verify with `python3 backend/run_demo.py` and `GET /metrics` before recording. **3:00 hard cap.**

| Time | Segment | Criteria served |
| :--- | :--- | :--- |
| 0:00–0:30 | Problem, users, urgency | Impact, Innovation |
| 0:30–1:00 | Solution & differentiation | Innovation |
| 1:00–2:00 | Demo/flow | Presentation, Impact |
| 2:00–2:30 | AI approach | Technical Execution |
| 2:30–3:00 | Impact numbers + next step | Business Model, Scalability |

---

## 0:00–0:30 · Problem, users, urgency

Open with a stat, not a logo.

> "Bangladesh received **$35.56 billion** in remittances in FY2025-26 — **$4.58 billion** of it from the UAE alone *(Bangladesh Bank FY2025-26 release — keep the citation link open for Q&A)*. A worker sending 1,000 dirhams home loses 3–6% to hidden spreads and fees, and most apps never show the **2.5% government incentive** his family is entitled to on formal remittance. Meet Rahim — a construction worker in Dubai, sending to his mother's bKash in Dhaka, on a mid-range Android, in Bangla. Every month, the gap compounds."

*(Screen: the Send screen — amount 1,000 AED, recipient field. Nothing else.)*

## 0:30–1:00 · Solution & differentiation

> "Borderless Money is a **net-receive router**. One sentence in Bangla, English, or Arabic. We compare every rail and show the exact taka that arrives — fees out, government bonus in."

*(Screen: quote screen. Point at: They receive ৳33,488.80 · Includes ৳820.00 government bonus. One line only:)*

> "No other app optimizes for net receive — because computing the 2.5% incentive into the route choice is the whole product."

## 1:00–2:00 · Demo / flow

Fast cuts, no narration of architecture here:

1. *(Voice input — or type)* "Send 1,000 dirhams to my mother's bKash in Dhaka" → parsed → quote.
2. Tap **Traditional SWIFT** → hero flips to ৳32,432.40, sentence flips to "৳1,056 less arrives than Stellar Hybrid Anchor." → tap back to the recommended rail. *(3 seconds — proves route choice.)*
3. Send → receipt: **Sent**, route, arrival time, reference.
4. Switch to the review scenario: payment **held** — "We need to verify this transfer. A human will review it within 24 hours." *(10 seconds — this is the responsible-AI proof: holds, not silent rejections.)*
5. Show the receipt's audit hash + Technical details for 2 seconds.

At **1:45**: click **বাংলা** — the quote screen flips to Bangla for 3 seconds, same ৳33,488.80. *(Bangla localisation, proven not claimed.)*

## 2:00–2:30 · AI approach (Technical Execution)

Four layers, thirty seconds:

> "A multilingual intent parser handles Bangla numerals and code-switching — **100% on our 49-utterance en/bn/ar benchmark**. A LangGraph orchestrator calls **deterministic tools — the LLM never does arithmetic**; that's how we prevent hallucinated money. A corridor graph scores every rail from config — UAE today, KSA already stubbed, a new corridor is a new file. And a **trained graph neural network plus OFAC fuzzy matching** runs pre-settlement risk — test AUC 0.90, with human review, never silent rejection. Regulatory grounding comes from a **retrieval layer over Bangladesh Bank circulars and OFAC guidance** — every decision ships with citations."

*(Screen: `/docs` endpoint list → `/metrics` → the corridor config file, 3 seconds each.)*

## 2:30–3:00 · Impact numbers + next step

> "Measured today: **+3.26% more money arrives**, sub-3-second quotes, zero false holds, full screening recall. Next: a pilot with one UAE exchange partner, three corridors — UAE, KSA, Malaysia to Bangladesh — and a **Remittance-as-a-Service API** for bKash and Nagad partners, at a 0.2–0.5% take rate. Ten thousand senders in six months. FinSphere AI track — **Borderless Money. Built in Dhaka, for the world.**"

*(Screen: `/metrics` JSON or the KPI table. End on it.)*

---

## Recording checklist

- [ ] Figures on camera: **$35.56B** (FY2025-26 total) and **$4.58B** (UAE corridor) — keep the Bangladesh Bank release link open for Q&A
- [ ] **SWIFT→bKash settlement = 28 h** (24 h rail + 4 h last-mile) — the system output in `run_demo.py` / `/quote` is the source of truth; never say 24 on camera
- [ ] `run_demo.py` + `/metrics` outputs match every number quoted
- [ ] Chrome mic permission granted; rehearse the sentence twice; quiet room
- [ ] "Simulated quotes / testnet" honesty labels visible in every money screen
- [ ] Review scenario pre-loaded via `/?scenario=fuzzy_review`
- [ ] Bangla toggle moment at 1:45 actually recorded (persisted toggle — switch back after)
- [ ] Burn in captions on: ৳33,488.80, +3.26%, AUC 0.90, 100% recall
- [ ] 3:00 hard cap; fresh-eyes viewer test passed before final cut
