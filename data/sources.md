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

## Real OFAC SDN list (verified 2026-10-28)

| Item | Value |
| :--- | :--- |
| File | OFAC Specially Designated Nationals list, full CSV |
| URL | https://www.treasury.gov/ofac/downloads/sdn.csv |
| Retrieved | 2026-10-28 |
| Size | 19,484 data rows (5.7 MB — not committed; re-download to reproduce) |
| One-off measurement | 100-party sample of the `review_volume.py` seeded pool screened against the full file with the production matcher logic (pre-normalized entries): **4 reviews / 100 parties = 40 / 1,000** — fuzzy collisions with real entries (e.g. "Rahim Hossain" jw 0.871, "Shamim Alam" jw 0.848), no exact hits, no blocks. This is the honest operational-cost planning number; the 10-entry local sample understates it. |

## Live reference check (2026-10-28 — network-sourced)

| Field | Live value | Source URL | Date accessed | Status |
| :--- | ---: | :--- | :--- | :--- |
| Mid-market AED→BDT (reference) | **33.7761** | https://open.er-api.com/v6/latest/AED (provider: exchangerate-api.com; last update Wed, 28 Oct 2026 00:02 UTC) | 2026-10-28 | **verified** |
| Mid-market AED→BDT (cross-check) | 33.81 (1 AED = 33.81 BDT; 1,000 AED → 33,814.30 BDT) | https://wise.com/gb/currency-converter/aed-to-bdt-rate?amount=1000 | 2026-10-28 | **verified (cross-check)** |

**Finding (recorded, not silently re-baselined):** the corridor config's
`mid_market_rate` fixture is 33.15 (snapshot dated 2026-10-24) — **~1.9% below
the 2026-10-28 reference (33.776)**. Re-baselining the fixture would change
every headline number (uplift, worked example, tests) and is deliberately
deferred: the demo is locked for submission. The delta is disclosed here
instead of hidden; re-baseline + full number regeneration is the first task
after submission.

| Field | Status | Exact URLs a human must fill (interactive tools — automated fetch blocked) |
| :--- | :--- | :--- |
| Provider A rate+fee (Wise) | blocked — rate page shows mid-market only; fee behind the Send tool | https://wise.com/gb/currency-converter/aed-to-bdt-rate?amount=1000 |
| Provider B rate+fee (Remitly UAE) | blocked — calculator is JS-rendered, placeholders in HTML | https://www.remitly.com/ae/en/money-transfer/bangladesh |
| Provider C rate+fee (Al Ansari Exchange) | blocked — /en/rates 404s; use their Online Currency Converter | https://alansariexchange.com/en/currency-converter |
| World Bank UAE→BD average | blocked — remittanceprices.worldbank.org returns 403 to automated fetch; download the RPW Excel manually | https://remittanceprices.worldbank.org/en/data |

## RAG corpus traceability (verified 2026-10-28)

Every passage in `backend/rag/corpus/*.md` carries a `Source:` line naming a
real organization + domain (bb.org.bd, ofac.treasury.gov, iso20022.org) and is
labeled **demo excerpt**. Passages cite departments and policy topics, never
invented circular numbers. `backend/evals/eval_rag.py` enforces both properties
mechanically: every retrieved passage's domain must be in its allow-list or the
eval exits 1. Latest run: **hit@2 8/8 = 100%, all citations resolve to allowed
domains** (`make eval-rag`, exit 0).

## Corridor field table

| Corridor | Field | Current value | Source | As of | Status |
| :--- | :--- | ---: | :--- | :--- | :--- |
| uae_bd | `mid_market_rate` | 33.15 | Live reference SOURCED 2026-10-28: 33.776 (open.er-api.com; cross-checked Wise 33.81) — config value kept as the Oct-24 fixture snapshot, delta ~1.9% disclosed above, re-baseline deferred | 2026-10-28 | SOURCED (reference) / fixture value |
| uae_bd | `rails[].fx` (per-rail customer rates) | 32.3–33.1 | # SOURCE NEEDED: World Bank Remittance Prices Worldwide (UAE→BD) + published provider rate pages. The two Stellar rails are additionally labeled `"source_class": "scenario assumption"` in the config | — | UNVERIFIED (Stellar rails: scenario assumption) |
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
