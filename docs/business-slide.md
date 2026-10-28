# xPay — business slide (numbers verified against the engine, 2026-10-28)

One slide. Every number below is computed in this repo — the footnote column is
the source of truth, and `# SOURCE NEEDED` marks the only externally claimed
figure. Do not put any number on a slide that is not a row here or in
[docs/kpis.md](kpis.md) / [docs/unit-economics.md](unit-economics.md).

## The slide

**Headline:** *On a AED 1,000 transfer, xPay's recommended route delivers
**৳33,423.20** where the legacy bank rail delivers **৳32,432.40** —
**+3.05% more money arrives**, after counting our own AED 2 fee.*

**Why it wins:** we rank rails by the taka that actually lands — fees out,
2.5% Bangladesh Bank government incentive in — instead of by the lowest
advertised fee. The 2.5% incentive is worth ৳820 on this transfer; fee-shopping
alone leaves most of that on the table.

| Line | Value | Source of truth |
| :--- | ---: | :--- |
| Net-receive uplift vs legacy SWIFT (headline) | **+3.05%** | corridor math, `GET /metrics` · [docs/kpis.md](kpis.md) |
| Pessimistic anchor-pricing case | **+2.59%** (table range +2.59–3.63%) | [docs/stellar-sensitivity.md](stellar-sensitivity.md) |
| 1,000-transfer simulation | **+3.53% mean** (1.57–11.08%) | `reports/simulation_1000.json` — fee-only ranking picks the ineligible promo rail on every transfer (100% disagreement with EV ranking); that gap is the incentive value |
| xPay consumer fee | **AED 2.00 flat**, shown as a line item | product decision · [docs/unit-economics.md](unit-economics.md) |
| B2B (Remittance-as-a-Service) price | **0.15% take rate on principal** | product decision · [docs/unit-economics.md](unit-economics.md) |
| Cost per transfer | **AED 0.16** (infra 0.06 · FX 0.03 · screening 0.02 · settlement/audit 0.05) | [docs/unit-economics.md](unit-economics.md) |
| Gross margin (consumer fee) | **AED 3.34 / 95.4%** | [docs/unit-economics.md](unit-economics.md) |
| Sanctions screening | **100% recall, 0% false-hold** on the 58-case benchmark | `make eval-sanctions` · [docs/kpis.md](kpis.md) |
| Review workload | **0 / 1,000 transfers** on the local list; **40 / 1,000** vs the real 19,484-entry OFAC SDN file | `reports/review_volume.json`; real-list run 2026-10-28 — `data/sources.md` |
| Quote latency | **21.2 ms p95 end-to-end HTTP** | `reports/load_test.txt` |
| Market size | **$35.56B** FY2025-26 remittances to BD; **$4.58B** UAE corridor | `# SOURCE NEEDED: Bangladesh Bank release URL + date` — see [data/sources.md](../data/sources.md) before quoting on camera |

**Honesty line (keep on the slide):** quotes are simulated corridor fixtures;
sanctions/intent benchmarks are curated, not production statistics; **no user
validation has been run yet** (instrument ready —
[docs/validation/survey.md](validation/survey.md)).

**What we ask for:** pilot with one UAE exchange-house partner (LOI), three
corridors (UAE/KSA→BD live today as configs), and the RaaS API in front of
bKash/Nagad. Unit economics hold down to AED 850 average principal
(95.1% margin at the 0.15% B2B take rate).
