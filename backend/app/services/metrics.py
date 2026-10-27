"""Measured demo KPIs — computed from the repo's own eval sets, never invented.

Every number returned here is reproducible:
  - net_receive_uplift_pct     : corridor math (best route incl. platform fee vs
                                 the legacy SWIFT counterfactual without it)
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


def _net_receive_uplift_pct() -> tuple[float, dict]:
    """xPay's best route (all sender costs incl. the platform fee) vs the
    legacy counterfactual: the same Traditional SWIFT rail priced WITHOUT
    xPay's platform fee — i.e. what the sender's current channel costs."""
    from app.services.incentive import calculate_true_net_receive_exact
    from app.services.money import D, to_number

    cfg = corridor_cfg.load_corridor()
    payout = cfg.get("default_payout", "BKASH")
    routes = routing_scorer.score_routes(1000.0, payout)
    best = routes[0]["breakdown"]["true_net_receive_bdt"]
    rail = next(r for r in cfg["rails"] if r["name"] == "Traditional SWIFT")
    lm_fee = cfg["last_mile"][payout]["Traditional SWIFT"][0]
    legacy = calculate_true_net_receive_exact(
        1000.0, rail["fx"], D(rail["fee_source"]) + D(lm_fee),
        currency_source=cfg["source_currency"], dest_currency=cfg["dest_currency"],
        govt_incentive_rate=cfg["govt_incentive_rate"],
        platform_fee_source=0,
    )
    legacy_net = to_number(legacy["values"]["true_net_dest"])
    uplift = round((best / legacy_net - 1.0) * 100.0, 2)
    detail = {
        "best_route_net": best,
        "legacy_swift_net": legacy_net,
        "platform_fee_included_in_best": True,
        "platform_fee_in_legacy_baseline": False,
    }
    return uplift, detail


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
    """Recall/FPR on the realistic sanctions benchmark (data/sanctions_eval.json):
    exact_normalized = list hits after normalization (must BLOCK), near_variant =
    added/variant tokens (must REVIEW), clear = unrelated names (no flag)."""
    ev = _load_eval("sanctions_eval.json")
    counts = {"exact": {"n": 0, "flagged": 0}, "near": {"n": 0, "flagged": 0},
              "clear": {"n": 0, "flagged": 0}, "single_token": {"n": 0, "flagged": 0},
              "unscreenable": {"n": 0, "flagged": 0}, "alias_only": {"n": 0, "flagged": 0}}
    for case in ev["cases"]:
        status = compliance.screen_party(case["name"], "eval")["status"]
        bucket = {"exact_normalized": "exact", "near_variant": "near",
                  "single_token": "single_token", "unscreenable": "unscreenable",
                  "alias_only": "alias_only"}.get(case["category"], "clear")
        counts[bucket]["n"] += 1
        counts[bucket]["flagged"] += status in ("BLOCKED", "FUZZY_MATCH_REVIEW")
    exact, near, clear, single, unscreenable, alias = (counts["exact"], counts["near"], counts["clear"],
                                                       counts["single_token"], counts["unscreenable"],
                                                       counts["alias_only"])
    recall = round(exact["flagged"] / exact["n"] * 100.0, 1) if exact["n"] else 100.0
    fpr = round(clear["flagged"] / clear["n"] * 100.0, 1) if clear["n"] else 0.0
    detail = {
        "true_hits_blocked": f"{exact['flagged']}/{exact['n']}",
        "alias_only_reviewed": f"{alias['flagged']}/{alias['n']}",
        "near_variants_reviewed": f"{near['flagged']}/{near['n']}",
        "single_token_reviewed": f"{single['flagged']}/{single['n']}",
        "unscreenable_reviewed": f"{unscreenable['flagged']}/{unscreenable['n']}",
        "clear_flagged": f"{clear['flagged']}/{clear['n']}",
        "benchmark": "backend/data/sanctions_eval.json (realistic variants; see make eval-sanctions)",
    }
    return recall, fpr, detail


@lru_cache(maxsize=1)
def compute_metrics() -> dict:
    recall, fp_rate, compliance_counts = _compliance_scores()
    intent_pct, intent_counts = _intent_accuracy()
    uplift, uplift_detail = _net_receive_uplift_pct()
    return {
        "net_receive_uplift_pct": uplift,
        "net_receive_uplift_detail": uplift_detail,
        "intent_accuracy_pct": intent_pct,
        "p95_quote_latency_ms": _p95_quote_latency_ms(),
        "false_positive_hold_rate_pct": fp_rate,
        "ofac_recall_pct": recall,
        "methodology": {
            "net_receive_uplift_pct": "AED 1,000 -> BKASH: best route priced end-to-end WITH xPay's flat platform fee vs the legacy counterfactual (same Traditional SWIFT rail WITHOUT the platform fee — the sender's current channel), from corridor config",
            "intent_accuracy_pct": f"full-field match on {intent_counts['n']} curated en/bn/ar utterances (backend/data/intent_eval.json); {intent_counts['passed']} passed",
            "p95_quote_latency_ms": "p95 of 20 in-process end-to-end quote runs (parse -> score -> screen)",
            "compliance": f"realistic sanctions benchmark: {compliance_counts['true_hits_blocked']} true hits blocked, "
                          f"{compliance_counts['near_variants_reviewed']} near-variants reviewed, "
                          f"{compliance_counts['clear_flagged']} clear names flagged",
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
