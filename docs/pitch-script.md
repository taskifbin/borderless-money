# xPay — 3-Minute Spoken Pitch (Dec 26, in-person round)

This is a **stand-up pitch script, not the video narration** — it must work with no screen-share (a live demo or a single slide is optional garnish, not a dependency). ~390 spoken words ≈ 3:00 at a calm pace. Rehearse twice minimum (plan: Oct 28), once with a stopwatch.

Delivery notes: open to the panel, not the screen. Numbers are spoken slowly. If the live demo fails, say "the recording shows this flow" and keep talking — never debug on stage.

---

**[0:00–0:30 · The person, the gap]**

> Rahim builds scaffolding in Dubai. Every month he sends one thousand dirhams to his mother's bKash in Dhaka. His exchange house takes fifteen dirhams in fees, hides a worse rate in the spread — and nobody tells his mother she is entitled to the government's two-and-a-half percent cash incentive for formal remittance. Multiply that gap across [verified Bangladesh Bank figure] a year, and you have the problem we built xPay to solve: money goes missing between two honest people and a regulation nobody surfaced for them.

**[0:30–1:00 · Solution & differentiation]**

> xPay is a net-receive router. One sentence — in Bangla, English, or Arabic — and it compares every rail on the exact taka that arrives: fees out — including our own flat two-dirham fee, shown as a line item — government incentive in. On a thousand dirhams, our recommended rail delivers 33,423 taka where legacy SWIFT delivers 32,432 — 991 taka more, in two hours instead of twenty-eight. The differentiator is not a prettier rate table. It's the only tool we found that computes the 2.5 percent incentive into the route choice itself.

**[1:00–2:00 · Live flow]**

> Let me show you. *(type: "Send 1,000 dirhams to my mother's bKash in Dhaka")* They receive 33,423 taka — including 820 taka of government bonus. Watch what honesty looks like: I switch to the traditional SWIFT rail, and the app itself tells me 991 taka less arrives. I switch back, and send. Before any money moves, the compliance gate runs: a trained graph neural network scores the transaction, sanctions screening checks both names with fuzzy matching — and if anything is near a match, we do not reject silently. We hold the payment and tell the user a human will review it within twenty-four hours. Then the receipt: settlement hash, ISO 20022 payload, and every decision grounded in cited Bangladesh Bank and OFAC passages.

**[2:00–2:30 · AI approach]**

> Under the hood, the LLM never does arithmetic — an orchestrator calls deterministic tools; that is how we prevent hallucinated money. Corridors are configuration files: UAE today, KSA already stubbed — a new corridor is a new file, not a codebase. And the risk model is honest: a trained GCN ships in-repo, evaluated on a held-out **synthetic** benchmark (AUC 0.90) — published as prototype evidence with class-error analysis and simple-baseline ablation, not pitched as production fraud detection; the explainable deterministic rule stays the default scorer.

**[2:30–3:00 · Business & close]**

> And the business: senders pay a flat two dirhams — a fifth of incumbent fees. Exchange-house partners pay 0.15 percent of principal for the routing and compliance API. At ten thousand senders, that is roughly sixty-five thousand dirhams of monthly gross margin, with an eight-dirham acquisition cost paid back in weeks. Next: a pilot with one UAE exchange partner, then KSA and Malaysia, then Remittance-as-a-Service for the wallet providers. FinSphere AI track — xPay. Built in Dhaka, for the world.

---

## Q&A one-liners (memorize)

- **Stellar / crypto regulation:** "Retail crypto-to-fiat is restricted in Bangladesh, so the hybrid model keeps digital-asset settlement institutional and back-end — the sender and recipient only ever see taka."
- **"Isn't this just FX comparison?"** "The moat is the jurisdiction rule engine — incentive math, sanctions screening with human review, ISO 20022, config-driven corridors — and the B2B API on top. The UI is the smallest part."
- **"Is the GNN real?"** "Trained and evaluated in the repo — AUC 0.90 on a labeled synthetic benchmark, ceiling documented. Production labels are the roadmap; the deterministic stand-in remains the safe default."
- **"Who pays?"** "Senders pay a flat two dirhams; exchange-house partners pay 0.15% of principal; wallets pay nothing — they earn the last-mile volume. Full model is in our one-pager."
- **"What about the 2.5% incentive — is that yours?"** "Never. It flows to the beneficiary exactly as the Bangladesh Bank circulars intend. We optimize for it; we don't touch it."
