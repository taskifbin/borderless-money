"""Measured demo KPIs — computed from the repo's own eval sets, never invented.

Every number returned here is reproducible:
  - net_receive_uplift_pct     : corridor math (best route vs Traditional SWIFT)
  - intent_accuracy_pct        : backend/data/intent_eval.json (50 utterances, en/bn/ar)
  - p95_quote_latency_ms       : 20 in-process full quote runs, timed
  - false_positive_hold_rate_pct / ofac_recall_pct
                               : backend/data/compliance_eval.json (20 labeled names)

Computed once per process (lru_cache) — the endpoint never fabricates values
at request time.
"""
import datetime as _dt
import json
import time
from functools import lru_cache
from pathlib import Path

from app.services import compliance, intent_parser, routing_scorer
from app.services import corridor as corridor_cfg

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_eval(name: str) -> dict:
    with open(_DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def _net_receive_uplift_pct() -> float:
    routes = routing_scorer.score_routes(1000.0, corridor_cfg.load_corridor().get("default_payout", "BKASH"))
    by_name = {r["name"]: r for r in routes}
    best = routes[0]["breakdown"]["true_net_receive_bdt"]
    swift = next(
        (r for name, r in by_name.items() if r["rail"] == "Traditional SWIFT"),
        routes[-1],
    )["breakdown"]["true_net_receive_bdt"]
    return round((best / swift - 1.0) * 100.0, 2)


def _intent_accuracy() -> tuple[float, dict]:
    ev = _load_eval("intent_eval.json")
    fields = ev.get("fields_checked", [])
    total, passed, failures = len(ev["cases"]), 0, []
    for case in ev["cases"]:
        got = intent_parser.parse_intent(case["text"])
        ok = True
        for field in fields:
            if field in case["expected"] and got.get(field) != case["expected"][field]:
                ok = False
                failures.append({"text": case["text"], "field": field,
                                 "expected": case["expected"][field], "got": got.get(field)})
        passed += ok
    return round(passed / total * 100.0, 1), {"n": total, "passed": passed, "failures": failures[:5]}


def _p95_quote_latency_ms() -> float:
    from app.agent import orchestrator  # local import: avoids import cycle at module load

    timings = []
    for _ in range(20):
        t0 = time.perf_counter()
        orchestrator.run("quote", text="Send 1,000 dirhams to my mother's bKash in Dhaka")
        timings.append((time.perf_counter() - t0) * 1000.0)
    timings.sort()
    return round(timings[int(0.95 * (len(timings) - 1))], 1)


def _compliance_scores() -> tuple[float, float, dict]:
    ev = _load_eval("compliance_eval.json")
    tp, tp_caught, clear, clear_flagged = 0, 0, 0, 0
    for case in ev["cases"]:
        status = compliance.screen_party(case["name"], "eval")["status"]
        if case["label"] in ("exact", "fuzzy"):
            tp += 1
            tp_caught += status in ("BLOCKED", "FUZZY_MATCH_REVIEW")
        else:
            clear += 1
            clear_flagged += status in ("BLOCKED", "FUZZY_MATCH_REVIEW")
    recall = round(tp_caught / tp * 100.0, 1) if tp else 100.0
    fp_rate = round(clear_flagged / clear * 100.0, 1) if clear else 0.0
    return recall, fp_rate, {"true_positives": tp, "caught": tp_caught,
                             "clear_names": clear, "wrongly_flagged": clear_flagged}


@lru_cache(maxsize=1)
def compute_metrics() -> dict:
    recall, fp_rate, compliance_counts = _compliance_scores()
    intent_pct, intent_counts = _intent_accuracy()
    return {
        "net_receive_uplift_pct": _net_receive_uplift_pct(),
        "intent_accuracy_pct": intent_pct,
        "p95_quote_latency_ms": _p95_quote_latency_ms(),
        "false_positive_hold_rate_pct": fp_rate,
        "ofac_recall_pct": recall,
        "methodology": {
            "net_receive_uplift_pct": "AED 1,000 -> BKASH: best-route True Net Receive vs Traditional SWIFT, from corridor config",
            "intent_accuracy_pct": f"full-field match on {intent_counts['n']} curated en/bn/ar utterances (backend/data/intent_eval.json); {intent_counts['passed']} passed",
            "p95_quote_latency_ms": "p95 of 20 in-process end-to-end quote runs (parse -> score -> screen)",
            "compliance": f"{compliance_counts['true_positives']} labeled true positives, {compliance_counts['clear_names']} clear names (backend/data/compliance_eval.json)",
        },
        "targets": {
            "net_receive_uplift_pct": ">= 3.0",
            "intent_accuracy_pct": ">= 95",
            "p95_quote_latency_ms": "<= 3000",
            "false_positive_hold_rate_pct": "<= 2.0",
            "ofac_recall_pct": "100",
        },
        "corridor": corridor_cfg.DEFAULT_CORRIDOR,
        "computed_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "All values are measured from this repository's code and eval data at process start; intent/compliance sets are curated benchmarks, not production statistics.",
    }
