# xPay — Unit Economics (half-page model)

**Status: every number below is an assumption for the preliminary round.** They are internally consistent and sized to be defensible in 60 seconds of Q&A, but none are validated. Replace each with pilot data before the in-person round. Our revenue **never touches the government's 2.5% incentive** — that belongs entirely to the beneficiary, by design and by law.

## 1. Who pays? (three candidate payers, two chosen)

| Payer | Mechanism | Decision |
| :--- | :--- | :--- |
| Sender | **Flat AED 2.00 per transfer** — a fifth of the AED 15–25 incumbents charge | ✅ primary consumer-side revenue |
| MTO / exchange-house partner (RaaS API) | **0.15% take rate on principal** for routing + incentive optimization + compliance rails | ✅ primary B2B revenue. **The partner pays it** out of its own fee income. `# SOURCE NEEDED: partner willingness` — who ultimately bears it (partner margin vs a sender surcharge) is unresolved until pilot LOIs exist. |
| bKash / Nagad API partners | Nothing — they gain last-mile volume and formal-channel incentive flows | ❌ they are a distribution channel, not a payer |

## 2. How much? (per-transfer unit economics at AED 1,000 principal)

| Line | AED | Note (assumption) |
| :--- | ---: | :--- |
| Sender flat fee | 2.00 | consumer price anchor |
| Partner take rate 0.15% × 1,000 | 1.50 | RaaS fee on principal, paid by the partner |
| **Gross revenue / transfer** | **3.50** | |
| Infra & compute (API, DB, egress) | −0.06 | |
| FX rate feed (amortized per call) | −0.03 | |
| Sanctions screening (amortized per party) | −0.02 | |
| Settlement & audit writes (Horizon probe, ledger writes, log storage) | −0.05 | **added in the Oct 27 pass — the earlier model lumped this into infra and understated cost** |
| **Total variable cost / transfer** | **−0.16** | |
| **Gross margin / transfer** | **3.34 (95.4%)** | not "≈96%" — the settlement line moves it. `# SOURCE NEEDED`: infra/FX/screening cost lines are estimates; replace with measured cloud spend in the pilot |

Sensitivity — take rate (at AED 850 avg principal, cost held at 0.16):

| Take rate | Gross/transfer | Gross margin | Margin % |
| ---: | ---: | ---: | ---: |
| 0.10% | 2.85 | 2.69 | 94.4% |
| 0.15% (base) | 3.275 | 3.115 | 95.1% |
| 0.20% | 3.70 | 3.54 | 95.7% |

Margin % is structurally insensitive to the take rate (cost is flat per
transfer) — the lever that matters is VOLUME, which is why the CAC line below
is the one to attack in Q&A.

## 3. Why does it scale?

- **CAC ≈ AED 8 per activated sender** via employer/payroll and exchange-house partnerships (B2B2C), vs AED 40–80 typical paid-digital fintech CAC *(assumption)*. CAC payback at the AED 850 average principal (margin ≈ AED 3.115/transfer): **1.3 months** at 2 transfers/sender/month; sensitivity below.

| Transfers/sender/month | Margin/month/sender | CAC payback (AED 8) |
| ---: | ---: | ---: |
| 1 | 3.115 | 2.6 months |
| 2 (base) | 6.23 | 1.3 months |
| 3 | 9.345 | 0.9 months |

- **6-month target: 10,000 activated senders** × 2 transfers/month × AED 850 avg = **AED 17M monthly volume** → **≈ AED 65,500 monthly gross revenue** (20,000 × 3.275), **≈ AED 62,300 monthly gross margin** (20,000 × 3.115).
- Total CAC spend to reach 10K senders ≈ AED 80,000 — recovered in **~5 weeks** of margin at target volume.
- **Marginal cost per additional corridor:** a config file (FX, incentive rule, rails, sanctions list) + one payout-rail integration ≈ **2 engineer-weeks + one compliance review**; platform infrastructure stays flat. KSA (`ksa_bd.json`) and Malaysia (`my_bd.json`) already ship as config-only proofs — the engine is corridor-agnostic.
- Growth loop that partners fund: every incentive-optimized transfer is marketing for the formal channel — MTOs and MFS wallets acquire volume through us, so partner-borne distribution substitutes for paid CAC as corridors grow.

## 4. The 60-second judge answer

> "Senders pay a flat AED 2 — a fifth of incumbent fees. Exchange-house partners pay 0.15% of principal for the routing and compliance API — the partner pays it, and who bears it finally is a pilot question; bKash and Nagad pay nothing because they earn the last-mile volume. Variable cost is 16 fils per transfer across infra, FX feed, screening and settlement writes, so gross margin is 95.4%. CAC is AED 8 through employer partnerships, paid back in about six weeks at two transfers a month, and 10,000 senders is roughly AED 62K of monthly gross margin by month six. A new corridor costs two engineer-weeks because the rules are config files — KSA and Malaysia already ship as config stubs. These are assumptions sized for the pilot; the pilot validates them."

*(Assumption register: take rate, flat fee, CAC, transfer frequency, average principal, variable cost, corridor integration cost — all to be replaced by pilot data; none derived from production data.)*
