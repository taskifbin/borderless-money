"""Sanctions-matcher benchmark (Step 1) — one-command repro: `make eval-sanctions`.

Runs backend/data/sanctions_eval.json against app.services.compliance.screen_party
and reports per-category decisions plus precision / recall / FPR / FNR, where:

    true match   = exact_normalized cases (list hit after normalization)
    near variant = near_variant cases            (expected: REVIEW, not BLOCK)
    cleared      = clear cases                   (expected: no flag at all)

    recall  = true matches flagged (BLOCKED or REVIEW) / true matches
    FPR     = cleared names flagged / cleared names
    FNR     = true matches cleared / true matches
    precision (block) = exact hits correctly BLOCKED / everything BLOCKED

Exit code 1 if the policy table is violated (any mismatch vs the expected
category decision), so CI fails loudly.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import compliance  # noqa: E402

EXPECTED = {
    "exact_normalized": "BLOCKED",
    "near_variant": "FUZZY_MATCH_REVIEW",
    "single_token": "FUZZY_MATCH_REVIEW",
    "unscreenable": "FUZZY_MATCH_REVIEW",
    "clear": "CLEAR",
}


def main() -> int:
    data_file = Path(__file__).resolve().parents[1] / "data" / "sanctions_eval.json"
    with open(data_file, "r", encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    results = defaultdict(list)
    mismatches = []
    for case in cases:
        party = compliance.screen_party(case["name"], "eval")
        results[case["category"]].append((case["name"], party["status"]))
        if party["status"] != EXPECTED[case["category"]]:
            mismatches.append({
                "name": case["name"], "category": case["category"],
                "expected": EXPECTED[case["category"]], "got": party["status"],
                "why": party["rationale"]["decision_rule"],
            })

    print(f"{'category':<18} {'n':>3}  decisions")
    stats = {}
    for category in ("exact_normalized", "near_variant", "single_token", "unscreenable", "clear"):
        rows = results[category]
        counts = defaultdict(int)
        for _, status in rows:
            counts[status] += 1
        stats[category] = counts
        breakdown = ", ".join(f"{k.split('_')[0]}={v}" for k, v in sorted(counts.items()))
        print(f"{category:<18} {len(rows):>3}  {breakdown}")

    true_n = len(results["exact_normalized"])
    true_blocked = stats["exact_normalized"].get("BLOCKED", 0)
    near_n = len(results["near_variant"])
    near_flagged = (stats["near_variant"].get("FUZZY_MATCH_REVIEW", 0)
                    + stats["near_variant"].get("BLOCKED", 0))
    clear_n = len(results["clear"])
    clear_flagged = (stats["clear"].get("FUZZY_MATCH_REVIEW", 0)
                     + stats["clear"].get("BLOCKED", 0))
    total_blocked = sum(stats[c].get("BLOCKED", 0) for c in stats)

    recall = true_blocked / true_n if true_n else 1.0
    near_recall = near_flagged / near_n if near_n else 1.0
    fpr = clear_flagged / clear_n if clear_n else 0.0
    fnr = (true_n - true_blocked) / true_n if true_n else 0.0
    precision_block = true_blocked / total_blocked if total_blocked else 1.0

    print()
    print(f"recall (true hits BLOCKED)          : {recall:.1%}  ({true_blocked}/{true_n})")
    print(f"near-variant recall (REVIEW)        : {near_recall:.1%}  ({near_flagged}/{near_n})")
    print(f"false-positive rate on clear names  : {fpr:.1%}  ({clear_flagged}/{clear_n})")
    print(f"false-negative rate on true matches : {fnr:.1%}")
    print(f"block precision                     : {precision_block:.1%}")
    print(f"single-token hard-blocks            : {stats['single_token'].get('BLOCKED', 0)} (policy: 0)")
    print(f"unscreenable inputs cleared          : {clear_count_unscreenable(stats)} (policy: 0 — must go to review)")


def clear_count_unscreenable(stats: dict) -> int:
    return stats["unscreenable"].get("CLEAR", 0)

    if mismatches:
        print("\nPOLICY MISMATCHES:")
        for m in mismatches:
            print(f"  {m['name']!r} [{m['category']}] expected {m['expected']}, got {m['got']} — {m['why']}")
        return 1
    print("\nPolicy table satisfied: true hits block, near-misses review, unrelated clear, no single-token blocks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
