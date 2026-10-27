# Data sources — what is sourced, what is not

Rule: **every number that can appear on a slide or be said on camera must trace
to a row in this table** with a real source and a retrieval date. Values marked
`UNVERIFIED` are fixture assumptions inherited from the demo config — they may
be *computed on* (the engine treats them as data), never *cited as fact*.

Status vocabulary:

| Status | Meaning |
| :--- | :--- |
| `SOURCED` | Public, checkable source attached with a retrieval date |
| `POLICY-CITED` | Real published policy; circular number/URL still to be attached |
| `PRODUCT-DECISION` | xPay's own commercial choice, not an external fact |
| `UNVERIFIED` | Fixture assumption — `# SOURCE NEEDED` before any public use |

## Corridor field table

| Corridor | Field | Current value | Source | As of | Status |
| :--- | :--- | ---: | :--- | :--- | :--- |
| uae_bd | `mid_market_rate` | 33.15 | # SOURCE NEEDED: Bangladesh Bank reference rate or citable AED→BDT mid-market source (AED is USD-pegged at 3.6725/USD) | — | UNVERIFIED |
| uae_bd | `rails[].fx` (per-rail customer rates) | 32.3–33.1 | # SOURCE NEEDED: World Bank Remittance Prices Worldwide (UAE→BD) + published provider rate pages | — | UNVERIFIED |
| uae_bd | `rails[].fee_source` | 1.5–15.0 | # SOURCE NEEDED: published fee schedules of 3–4 named providers (bank SWIFT tariff, exchange-house table, wallet pricing) | — | UNVERIFIED |
| uae_bd | `rails[].hours` | 1–24 h | # SOURCE NEEDED: provider service-level statements | — | UNVERIFIED |
| uae_bd | `rails[].success_rate` | 0.90–0.98 | No public per-rail data exists — internal assumption; label as such | — | UNVERIFIED |
| uae_bd | `last_mile[payout][rail]` fees | 0–9.0 | # SOURCE NEEDED: bKash/Nagad/bank payout fee schedules | — | UNVERIFIED |
| uae_bd | `govt_incentive_rate` | 0.025 | Bangladesh Bank SME & Remittance Department circulars (2.5% cash incentive on formal remittance) — # SOURCE NEEDED: exact circular number + URL | — | POLICY-CITED |
| uae_bd | `platform_fee_source` | 2.0 | xPay product decision (docs/unit-economics.md) | — | PRODUCT-DECISION |
| ksa_bd | `mid_market_rate` | 8.83 | # SOURCE NEEDED: citable SAR→BDT mid-market source | — | UNVERIFIED |
| ksa_bd | `rails[].fx` / `fee_source` / `hours` / `success_rate` | fixture | # SOURCE NEEDED: World Bank RPW (KSA→BD) + provider pages — KSA rail is a stub | — | UNVERIFIED |
| ksa_bd | `platform_fee_source` | 2.0 (SAR) | xPay product decision (SAR 2.00 ≈ AED 2.00 assumption) | — | PRODUCT-DECISION |

Both corridor configs carry the same table inline under `_sources` so the data
and its provenance travel together.

## Replacement workflow

1. Fetch the source (World Bank RPW query for UAE→BD / KSA→BD; provider fee
   pages; Bangladesh Bank circular).
2. Write the retrieved value + `as_of` date into the corridor JSON field.
3. Flip the matching `_sources` entry to `SOURCED` with the URL and date.
4. Re-run `make test && make scenarios` — `TestCorridorConfigInvariants`
   enforces fx ≤ mid-market and sane fees/rates on every corridor, so a
   bad source value fails CI instead of shipping.
5. Regenerate any derived number (`make scenarios`) and update the one-pager.

## External anchors used in prose (verify before quoting on camera)

| Claim | Where used | Status |
| :--- | :--- | :--- |
| World Bank RPW: global average cost of sending $200 ≈ 6%+ | docs/kpis.md "Public baseline" | # SOURCE NEEDED: exact RPW release + figure |
| Bangladesh remittance volume ($35.56B FY2025-26; $4.58B UAE corridor) | docs/one-pager.md, docs/demo-script.md | # SOURCE NEEDED: Bangladesh Bank release URL + date |
