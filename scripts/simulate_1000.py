"""1,000-transfer simulation — xPay's EV ranking vs three baselines.

Synthetic but deterministic (random.Random(42)). Every transfer is priced by
the real engine (exact-decimal, corridor config, platform fee included).

Baselines:
  (a) current channel  — legacy Traditional SWIFT priced WITHOUT xPay's
      platform fee (the sender's status quo counterfactual, same as /metrics)
  (b) fee-only         — cheapest total fee among xPay routes (a rate-table
      comparison that ignores FX and incentive differences)
  (c) cost-only        — ranks xPay routes by net WITH the 2.5% incentive
      switched off (a competitor that does not compute the incentive), then
      the recipient gets whatever that route actually pays

Reported: net-receive uplift vs (a) for each strategy, and the share of
transfers where xPay's expected-value ranking disagrees with (b)/(c).

Run:  backend/.venv/bin/python scripts/simulate_1000.py
Output: reports/simulation_1000.json (summary only — no per-row CSV).
"""
import json
import random
import statistics
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.incentive import calculate_true_net_receive_exact  # noqa: E402
from app.services.money import D  # noqa: E402
from app.services import routing_scorer  # noqa: E402

CFG = json.load(open(BACKEND / "config" / "corridors" / "uae_bd.json"))
PAYOUT_MIX = {"BKASH": 0.60, "NAGAD": 0.25, "BANK": 0.15}  # synthetic assumption
N = 1000
SEED = 42


def legacy_swift_net(amount: D) -> str:
    rail = next(r for r in CFG["rails"] if r["name"] == "Traditional SWIFT")
    lm = CFG["last_mile"]["BKASH"]["Traditional SWIFT"][0]  # conservative: bKash leg
    priced = calculate_true_net_receive_exact(
        amount, rail["fx"], D(rail["fee_source"]) + D(lm),
        currency_source=CFG["source_currency"], dest_currency=CFG["dest_currency"],
        govt_incentive_rate=CFG["govt_incentive_rate"], platform_fee_source=0,
    )
    return str(priced["values"]["true_net_dest"])


def pick_payout(rng: random.Random) -> str:
    x, acc = rng.random(), 0.0
    for payout, share in PAYOUT_MIX.items():
        acc += share
        if x <= acc:
            return payout
    return "BKASH"


def main() -> None:
    rng = random.Random(SEED)
    results = {"xpay_ev": [], "fee_only": [], "cost_only": [], "current_channel": []}
    rank_diff_fee_only = 0
    rank_diff_cost_only = 0

    for _ in range(N):
        amount = D(max(200, min(5000, round(rng.lognormvariate(6.8, 0.55)))))
        payout = pick_payout(rng)
        routes = routing_scorer.score_routes(amount, payout)
        priced = [r for r in routes if r["expected_value_bdt"] is not None]
        if not priced:
            continue

        current = D(legacy_swift_net(amount))
        xpay = D(str(routes[0]["breakdown"]["true_net_receive_bdt"]))

        fee_only_route = min(priced, key=lambda r: D(str(r["fee_aed"])))
        fee_only = D(str(fee_only_route["breakdown"]["true_net_receive_bdt"]))

        cost_only_route = max(
            priced,
            key=lambda r: D(str(r["breakdown"]["gross_bdt"]))
            - D(str(r["breakdown"]["fees_deducted_bdt"])),
        )
        cost_only = D(str(cost_only_route["breakdown"]["true_net_receive_bdt"]))

        if routes[0]["name"] != fee_only_route["name"]:
            rank_diff_fee_only += 1
        if routes[0]["name"] != cost_only_route["name"]:
            rank_diff_cost_only += 1

        results["current_channel"].append(float(current))
        results["xpay_ev"].append(float(xpay))
        results["fee_only"].append(float(fee_only))
        results["cost_only"].append(float(cost_only))

    def uplift_stats(baseline: str) -> dict:
        ups = [(x / c - 1) * 100 for x, c in zip(results["xpay_ev"], results[baseline])]
        return {
            "mean_pct": round(statistics.mean(ups), 2),
            "median_pct": round(statistics.median(ups), 2),
            "min_pct": round(min(ups), 2),
            "max_pct": round(max(ups), 2),
        }

    report = {
        "suite": "xpay-simulation-1000",
        "n_transfers": N,
        "seed": SEED,
        "synthetic_assumptions": {
            "amount_aed": "lognormal(mu=6.8, sigma=0.55), clipped to [200, 5000], rounded to whole AED",
            "payout_mix": PAYOUT_MIX,
            "note": "amounts and payout mix are synthetic assumptions, not field data; the PRICING is the real engine",
        },
        "mean_net_receive_bdt": {
            "current_channel_legacy_swift": round(statistics.mean(results["current_channel"]), 2),
            "xpay_ev_ranking": round(statistics.mean(results["xpay_ev"]), 2),
            "fee_only_ranking": round(statistics.mean(results["fee_only"]), 2),
            "cost_only_ranking": round(statistics.mean(results["cost_only"]), 2),
        },
        "uplift_vs_current_channel": {
            "xpay_ev_ranking": uplift_stats("current_channel"),
            "fee_only_ranking_if_it_were_used": {
                k: v for k, v in uplift_stats_fee_only(results).items()
            },
            "cost_only_ranking_if_it_were_used": uplift_stats_cost_only(results),
        },
        "share_of_transfers_where_ranking_differs": {
            "xpay_ev_vs_fee_only": round(rank_diff_fee_only / N, 4),
            "xpay_ev_vs_cost_only": round(rank_diff_cost_only / N, 4),
        },
        "interpretation": {
            "ranking_differs_1.0": "fee-only and cost-only both always pick the incentive-ineligible promo rail (lowest fee / lowest cost), so on this corridor config they disagree with incentive-aware EV ranking on every transfer — that disagreement IS the product",
            "uplift_gap": "mean uplift difference between xPay EV ranking and fee-only = the BDT value of computing the 2.5% incentive into the route choice",
        },
    }
    out = Path(__file__).resolve().parents[1] / "reports" / "simulation_1000.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"\nwritten: {out}")


def uplift_stats_fee_only(results: dict) -> dict:
    ups = [(f / c - 1) * 100 for f, c in zip(results["fee_only"], results["current_channel"])]
    return {"mean_pct": round(statistics.mean(ups), 2), "median_pct": round(statistics.median(ups), 2),
            "min_pct": round(min(ups), 2), "max_pct": round(max(ups), 2)}


def uplift_stats_cost_only(results: dict) -> dict:
    ups = [(f / c - 1) * 100 for f, c in zip(results["cost_only"], results["current_channel"])]
    return {"mean_pct": round(statistics.mean(ups), 2), "median_pct": round(statistics.median(ups), 2),
            "min_pct": round(min(ups), 2), "max_pct": round(max(ups), 2)}


if __name__ == "__main__":
    main()
