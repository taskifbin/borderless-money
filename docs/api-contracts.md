# Borderless Money — API Contracts

Base URL (dev): `http://localhost:8000` · Interactive docs: `/docs`
These contracts are the team-wide interface — frontend and B2B RaaS consumers build
against them.

---

## `GET /api/health`

```json
{
  "status": "ok",
  "corridor": {"source": "AED", "dest": "BDT", "source_country": "UAE", "dest_country": "BD"},
  "engines": {"langgraph": false, "networkx": false, "torch_geometric": false, "stellar_sdk": false}
}
```

`engines` reports which optional libraries are active — the API behaves identically
either way (fallbacks kick in); this is for ops/debugging.

---

## `POST /api/agent/parse-intent`

Voice transcript or typed text → structured intent.

**Request**
```json
{"text": "Send 1,000 dirhams to my mother's bKash in Dhaka", "default_corridor": "AED_TO_BDT"}
```

**Response** — `ParsedIntent`
```json
{
  "raw_text": "Send 1,000 dirhams to my mother's bKash in Dhaka",
  "amount": 1000.0,
  "source_currency": "AED",
  "dest_currency": "BDT",
  "recipient": "Mother",
  "payout_method": "BKASH",
  "corridor": "AED_TO_BDT",
  "language_detected": "en",
  "confidence": 0.9,
  "defaults_applied": []
}
```

`payout_method` ∈ `BKASH | NAGAD | BANK`. If the amount can’t be extracted, `amount`
is `null` and `defaults_applied` contains `"amount"` (the UI then asks for it).

---

## `POST /api/agent/quote`

Full orchestrated quote: intent → ranked routes → compliance preview → reasoning log.
No money moves.

**Request** (any subset; `text` is parsed if given, explicit fields override)
```json
{"text": "Send 1000 dirhams to my mother's bKash", "amount": 1000, "payout_method": "BKASH"}
```

**Response** — orchestrator state (trimmed to the important fields):
```json
{
  "mode": "quote",
  "parsed_intent": { "...": "ParsedIntent as above" },
  "amount": 1000.0,
  "payout_method": "BKASH",
  "routes": [
    {
      "name": "Stellar Hybrid Anchor → BKASH",
      "rail": "Stellar Hybrid Anchor",
      "payout_method": "BKASH",
      "fx_rate": 32.8,
      "mid_market_rate": 33.15,
      "spread_bdt_per_aed": 0.35,
      "fee_aed": 4.0,
      "settlement_time_hrs": 2.0,
      "success_rate": 0.98,
      "is_best": true,
      "advantage_bdt_vs_best": 0.0,
      "breakdown": {
        "amount_source": 1000.0,
        "currency_source": "AED",
        "fx_rate": 32.8,
        "fee_source": 4.0,
        "gross_bdt": 32800.0,
        "fees_deducted_bdt": 131.2,
        "govt_incentive_rate": 0.025,
        "govt_incentive_added_bdt": 820.0,
        "true_net_receive_bdt": 33488.8,
        "route": "Stellar Hybrid Anchor → BKASH",
        "settlement_time_hrs": 2.0
      }
    }
  ],
  "risk": {
    "gnn_risk_score": 0.07,
    "risk_band": "LOW",
    "graph_nodes_evaluated": ["sender:usr_uae_001", "recipient:rcp_001", "device:fp_ae_9f2c", "geo:AE->BD"],
    "requires_manual_review": false,
    "engine": "heuristic-stand-in",
    "ai_explanation": "GNN subgraph analysis (4 nodes / 3 edges): trusted device fingerprint, 430-day account history, amount within 1.2× historical mean, long-standing recipient relationship. Behavior consistent with normal remittance pattern."
  },
  "compliance": {
    "ofac_match_status": "CLEAR",
    "screened_parties": [
      {"role": "sender", "name": "Mohammed Rafiq", "status": "CLEAR", "best_match": null},
      {"role": "recipient", "name": "Ayesha Begum", "status": "CLEAR", "best_match": null}
    ]
  },
  "decision": "CLEAR",
  "execution": null,
  "transaction": null,
  "explanation_log": [
    "Intent parsed: send AED 1,000 → BDT via BKASH to 'Mother' (confidence 0.90)",
    "Scored 3 viable corridor paths; best = Stellar Hybrid Anchor → BKASH: True Net Receive 33,488.80 BDT ..."
  ]
}
```

`routes` is sorted best-first by `true_net_receive_bdt`. `advantage_bdt_vs_best` is how
many BDT *less* this route delivers than the winner (0 for the winner).

---

## `POST /api/agent/execute`

Compliance gate → (if CLEAR) execution → stored receipt. Idempotent per call; each
call is a new transaction.

**Request**
```json
{
  "text": "Send 1000 dirhams to my mother's bKash",
  "amount": 1000,
  "payout_method": "BKASH",
  "selected_route_name": "Stellar Hybrid Anchor → BKASH",
  "recipient_name": "Ayesha Begum",
  "demo_scenario": "default"
}
```

`demo_scenario` ∈ `default | fuzzy_review | high_risk` (see README). All fields
optional except `selected_route_name` — without `text`/`amount`, the demo corridor
default (1,000 AED → bKash) applies.

**Response** — orchestrator state; the new parts:

```json
{
  "mode": "execute",
  "selected_route": { "...": "RouteOption as in /quote" },
  "decision": "CLEAR",
  "execution": {
    "status": "COMPLETED",
    "stellar_hash": "9f2c6e…64-hex…",
    "network": "SIMULATED",
    "simulated": true,
    "memo": "BM-3F9A1C2B",
    "settlement_seconds": 7200
  },
  "transaction": {
    "transaction_id": "0b9f…-uuid",
    "sender_id": "usr_uae_001",
    "sender_name": "Mohammed Rafiq",
    "recipient_name": "Ayesha Begum",
    "recipient_handle": "01712-345678 (bKash)",
    "amount_source": 1000.0,
    "currency_source": "AED",
    "fx_rate_applied": 32.8,
    "fee_deducted_aed": 4.0,
    "govt_incentive_2_5_pct": 820.0,
    "true_net_receive_bdt": 33488.8,
    "route_selected": "Stellar Hybrid Anchor → BKASH",
    "stellar_hash": "9f2c6e…",
    "status": "COMPLETED",
    "created_at": "2026-10-24T14:30:05Z",
    "breakdown": { "...": "same breakdown object as the route" },
    "iso_20022": { "MsgId": "BM3F9A1C2B", "CreDtTm": "…", "Dbtr": "Mohammed Rafiq", "Cdtr": "Ayesha Begum", "IntrBkSttlmAmt": {"Ccy": "BDT", "Value": "33488.80"} }
  }
}
```

**Held transaction (fuzzy_review / high_risk):** `decision` is `FUZZY_MATCH_REVIEW`
(or the GNN hold), `execution` is `null`, and `transaction.status` is
`COMPLIANCE_REVIEW` — with a plain-language `explanation_log` entry for the analyst.
A hard OFAC block returns `decision: "BLOCKED"`, `transaction.status: "BLOCKED"`.

---

## `GET /api/transactions/{transaction_id}` → stored `transaction` (404 if unknown)

## `GET /api/routes/compare?amount=1000&payout_method=BKASH`

Direct Layer A access (no agent): `{"routes": [RouteOption, …]}` — same shape as
`routes` in `/api/agent/quote`.

---

## Error shape (all endpoints)

```json
{"detail": "Could not parse any amount from the provided text"}
```
