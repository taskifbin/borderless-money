"""Layer A — Routing Scorer.

Corridor-agnostic: every rail, FX rate, fee and last-mile rule comes from the
corridor config (backend/config/corridors/<code>.json). Each rail is priced
end-to-end — rail fee/FX/hours plus the last-mile payout leg — the 2.5%
government incentive is applied ONLY to incentive-eligible rails, and routes
are ranked by expected value (true net x success rate). A naive
cheapest-fee baseline is exposed alongside so the ranking's value is
measurable, not asserted.
"""
from functools import lru_cache

from app.services import corridor as corridor_cfg
from app.services.incentive import calculate_true_net_receive


def score_routes(amount_source: float, payout_method: str = "BKASH",
                 corridor_code: str = corridor_cfg.DEFAULT_CORRIDOR,
                 deadline_hours: float | None = None) -> list[dict]:
    """Enumerate corridor paths, price each with True Net Receive (the 2.5%
    incentive applied ONLY to incentive-eligible rails), rank by expected value
    (true net x success rate), best-first."""
    corridor = corridor_cfg.load_corridor(corridor_code)
    payout_method = (payout_method or corridor["default_payout"]).upper()
    mid = corridor["mid_market_rate"]
    src_ccy = corridor["source_currency"]

    scored = []
    for rail in corridor["rails"]:
        rail_name = rail["name"]
        if rail_name not in corridor["last_mile"].get(payout_method, {}):
            continue  # rail does not serve this payout method
        eligible = bool(rail.get("incentive_eligible", True))
        fee, extra_h, succ = corridor["last_mile"][payout_method][rail_name]
        fee_total = rail["fee_source"] + fee
        hours = rail["hours"] + extra_h
        success = rail["success_rate"] * succ
        name = f"{rail_name} → {payout_method}"
        breakdown = calculate_true_net_receive(
            amount_source, rail["fx"], fee_total, route=name, settlement_time_hrs=hours,
            govt_incentive_rate=corridor["govt_incentive_rate"] if eligible else 0.0,
        )
        breakdown["incentive_eligible"] = eligible
        breakdown["hops"] = rail.get("hops", [corridor["source_currency"], corridor["dest_currency"]])
        expected_value = round(breakdown["true_net_receive_bdt"] * success, 2)
        scored.append({
            "name": name,
            "rail": rail_name,
            "payout_method": payout_method,
            "fx_rate": rail["fx"],
            "mid_market_rate": mid,
            "spread_bdt_per_aed": round(mid - rail["fx"], 2),
            "fee_aed": round(fee_total, 2),
            "settlement_time_hrs": hours,
            "success_rate": round(success, 4),
            "incentive_eligible": eligible,
            "expected_value_bdt": expected_value,
            "ranking_rationale": ("ranked by expected value = true net x success rate; "
                                  "the 2.5% incentive applies only to incentive-eligible rails"),
            "is_best": False,
            "advantage_bdt_vs_best": 0.0,
            "breakdown": breakdown,
        })

    if deadline_hours is not None:
        scored = [r for r in scored if r["settlement_time_hrs"] <= deadline_hours]
        if not scored:
            raise ValueError(f"No route arrives within {deadline_hours}h for '{payout_method}'")
    scored.sort(key=lambda r: r["expected_value_bdt"], reverse=True)
    best_ev = scored[0]["expected_value_bdt"]
    for i, route in enumerate(scored):
        route["is_best"] = i == 0
        route["advantage_bdt_vs_best"] = round(best_ev - route["expected_value_bdt"], 2)
    return scored


def naive_baseline(routes: list[dict]) -> dict | None:
    """The route a fee-only comparison would pick — the baseline the expected-
    value ranking is measured against."""
    if not routes:
        return None
    return min(routes, key=lambda r: (r["fee_aed"], -r["expected_value_bdt"]))
