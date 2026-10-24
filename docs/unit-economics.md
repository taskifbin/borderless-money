# Borderless Money — Unit Economics (half-page model)

**Status: every number below is an assumption for the preliminary round.** They are internally consistent and sized to be defensible in 60 seconds of Q&A, but none are validated. Replace each with pilot data before the in-person round. Our revenue **never touches the government's 2.5% incentive** — that belongs entirely to the beneficiary, by design and by law.

## 1. Who pays? (three candidate payers, two chosen)

| Payer | Mechanism | Decision |
| :--- | :--- | :--- |
| Sender | **Flat AED 2.00 per transfer** — a fifth of the AED 15–25 incumbents charge | ✅ primary consumer-side revenue |
| MTO / exchange-house partner (RaaS API) | **0.15% take rate on principal** for routing + incentive optimization + compliance rails | ✅ primary B2B revenue |
| bKash / Nagad API partners | Nothing — they gain last-mile volume and formal-channel incentive flows | ❌ they are a distribution channel, not a payer |

## 2. How much? (per-transfer unit economics at AED 1,000 avg)

| Line | AED | Note (assumption) |
| :--- | ---: | :--- |
| Sender flat fee | 2.00 | consumer price anchor |
| Partner take rate 0.15% × 1,000 | 1.50 | RaaS fee on principal |
| **Gross revenue / transfer** | **3.50** | |
| Variable cost (infra, FX feed, screening, settlement calls) | −0.15 | ~4% of revenue |
| **Gross margin / transfer** | **3.35 (≈96%)** | software-like margin; settlement is testnet→institutional, not per-tx human ops |

## 3. Why does it scale?

- **CAC ≈ AED 8 per activated sender** via employer/payroll and exchange-house partnerships (B2B2C), vs AED 40–80 typical paid-digital fintech CAC *(assumption)*. CAC payback: **<1 month** at 2 transfers/sender/month (2 × 3.35 = 6.70/mo per sender).
- **6-month target: 10,000 activated senders** × 2 transfers/month × AED 850 avg = **AED 17M monthly volume** → **≈ AED 65,500 monthly gross revenue** (20,000 × 3.275), **≈ AED 62,500 gross margin**.
- Total CAC spend to reach 10K senders ≈ AED 80,000 — recovered in **~5 weeks** of margin at target volume.
- **Marginal cost per additional corridor:** a config file (FX, incentive rule, rails, sanctions list) + one payout-rail integration ≈ **2 engineer-weeks + one compliance review**; platform infrastructure stays flat. KSA (`ksa_bd.json`) already ships as proof — the engine is corridor-agnostic.
- Growth loop that partners fund: every incentive-optimized transfer is marketing for the formal channel — MTOs and MFS wallets acquire volume through us, so partner-borne distribution substitutes for paid CAC as corridors grow.

## 4. The 60-second judge answer

> "Senders pay a flat AED 2 — a fifth of incumbent fees. Exchange-house partners pay 0.15% of principal for the routing and compliance API; bKash and Nagad pay nothing because they earn the last-mile volume. Variable cost is ~15 fils per transfer, so gross margin is ~96%. CAC is AED 8 through employer partnerships, paid back in under a month, and 10,000 senders at two transfers a month is roughly AED 65K of monthly gross margin by month six. A new corridor costs two engineer-weeks because the rules are config files — KSA already ships as a stub. These are assumptions sized for the pilot; the pilot validates them."

*(Assumption register: take rate, flat fee, CAC, transfer frequency, average principal, variable cost, corridor integration cost — all to be replaced by pilot data; none derived from production data.)*
