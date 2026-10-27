"""Layer A — Routing Scorer.

Corridor-agnostic: every rail, FX rate, fee and last-mile rule comes from the
corridor config (backend/config/corridors/<code>.json). Each rail is priced
end-to-end — rail fee/FX/hours plus the last-mile payout leg — the 2.5%
government incentive is applied ONLY to incentive-eligible rails, and routes
are ranked by expected value (true net x success rate). A naive
cheapest-fee baseline is exposed alongside so the ranking's value is
measurable, not asserted.

Eligibility before optimization (docs/FINANCIAL_MODEL.md §eligibility):
a route can only win if it has complete pricing. A route with missing fee
data is flagged `eligibility.eligible=false, reason="missing_fee_data"`, gets
NO net/EV figures (never a silently-zeroed fee) and can never win. All math
is exact Decimal (see money.py); floats appear only as display serialization.

Fee composition: every route's sender cost is rail fee + last-mile fee + the
corridor's platform fee (xPay's own flat sender fee, `platform_fee_source` in
the config; 0 if absent). The composition travels with each route as
`fee_source_components` so the platform fee is an explicit line item, never
buried inside a single number.
"""
from functools import lru_cache

from decimal import ROUND_HALF_UP

from app.services import corridor as corridor_cfg
from app.services.incentive import calculate_true_net_receive, calculate_true_net_receive_exact
from app.services.money import D, quantize, to_number

_DISPLAY = D("0.01")
_SUCCESS_PRECISION = D("0.0001")


def score_routes(amount_source, payout_method: str = "BKASH",
                 corridor_code: str = corridor_cfg.DEFAULT_CORRIDOR,
                 deadline_hours: float | None = None) -> list[dict]:
    """Enumerate corridor paths, price each with True Net Receive (the 2.5%
    incentive applied ONLY to incentive-eligible rails), mark eligibility,
    rank by expected value (true net x success rate), best-first."""
    corridor = corridor_cfg.load_corridor(corridor_code)
    payout_method = (payout_method or corridor["default_payout"]).upper()
    mid = corridor["mid_market_rate"]
    src_ccy = corridor["source_currency"]
    dest_ccy = corridor["dest_currency"]
    amount = D(amount_source)
    platform_fee = D(corridor.get("platform_fee_source", 0))

    scored: list[dict] = []
    for rail in corridor["rails"]:
        rail_name = rail["name"]
        if rail_name not in corridor["last_mile"].get(payout_method, {}):
            continue  # rail does not serve this payout method
        eligible = bool(rail.get("incentive_eligible", True))
        lm_fee, extra_h, succ = corridor["last_mile"][payout_method][rail_name]
        rail_fee = rail.get("fee_source")  # absent/None → incomplete pricing
        # rail + last-mile only: the platform fee is passed to the engine
        # separately (platform_fee_source) so it is added exactly once and
        # stays a visible line item.
        fee_total = None if rail_fee is None else D(rail_fee) + D(lm_fee)
        hours = rail["hours"] + extra_h
        success = D(rail["success_rate"]) * D(succ)
        name = f"{rail_name} → {payout_method}"
        priced = calculate_true_net_receive_exact(
            amount, rail["fx"], fee_total, route=name, settlement_time_hrs=hours,
            currency_source=src_ccy, dest_currency=dest_ccy,
            govt_incentive_rate=corridor["govt_incentive_rate"] if eligible else 0.0,
        )
        pricing_ok = not priced["incomplete"]
        net = priced["values"]["true_net_dest"]
        ev = None if net is None else quantize(net * success, dest_ccy)

        route = {
            "name": name,
            "rail": rail_name,
            "payout_method": payout_method,
            "fx_rate": to_number(D(rail["fx"])),
            "mid_market_rate": mid,
            "spread_per_source_unit": to_number(quantize(D(mid) - D(rail["fx"]), dest_ccy)),
            "fee_total_source": to_number(D(fee_total) + platform_fee) if fee_total is not None else None,
            "platform_fee_source": to_number(platform_fee),
            "fee_source_components": {
                "rail_fee_source": to_number(D(rail_fee)) if rail_fee is not None else None,
                "last_mile_fee_source": to_number(D(lm_fee)),
                "platform_fee_source": to_number(platform_fee),
            },
            "settlement_time_hrs": hours,
            "success_rate": float(success.quantize(_SUCCESS_PRECISION, rounding=ROUND_HALF_UP)),
            "incentive_eligible": eligible,
            "expected_value_bdt": to_number(ev) if ev is not None else None,
            "expected_value_exact": str(ev) if ev is not None else None,
            "eligibility": {
                "eligible": pricing_ok,
                "reason": None if pricing_ok else "missing_fee_data",
                "note": None if pricing_ok else
                "Fee data missing for this rail/last-mile pair; the route cannot be priced or ranked.",
            },
            "pricing_completeness": "complete" if pricing_ok else "incomplete",
            "missing_fields": priced["missing"],
            "ranking_rationale": ("ranked by expected value = true net x success rate; "
                                  "the 2.5% incentive applies only to incentive-eligible rails"),
            "is_best": False,
            "advantage_bdt_vs_best": None,
            "breakdown": calculate_true_net_receive(
                amount, rail["fx"], fee_total, route=name, settlement_time_hrs=hours,
                currency_source=src_ccy, dest_currency=dest_ccy,
                govt_incentive_rate=corridor["govt_incentive_rate"] if eligible else 0.0,
                platform_fee_source=platform_fee,
            ),
        }
        route["breakdown"]["incentive_eligible"] = eligible
        route["breakdown"]["hops"] = rail.get("hops", [src_ccy, dest_ccy])
        scored.append(route)

    if deadline_hours is not None:
        scored = [r for r in scored if r["settlement_time_hrs"] <= deadline_hours]
        if not any(r["expected_value_bdt"] is not None for r in scored):
            raise ValueError(f"No route arrives within {deadline_hours}h for '{payout_method}'")

    complete = [r for r in scored if r["expected_value_bdt"] is not None]
    incomplete = [r for r in scored if r["expected_value_bdt"] is None]
    # Stable sort: identical candidates keep config order (deterministic output).
    complete.sort(key=lambda r: D(r["expected_value_exact"]), reverse=True)
    ranked = complete + incomplete

    if complete:
        best_ev = D(complete[0]["expected_value_exact"])
        for i, route in enumerate(ranked):
            route["is_best"] = i == 0
            if route["expected_value_exact"] is not None:
                route["advantage_bdt_vs_best"] = to_number(
                    quantize(best_ev - D(route["expected_value_exact"]), dest_ccy))
    return ranked


def naive_baseline(routes: list[dict]) -> dict | None:
    """The route a fee-only comparison would pick — the baseline the expected-
    value ranking is measured against. Routes with unknown fees cannot play."""
    priced = [r for r in routes if r["fee_total_source"] is not None and r["expected_value_bdt"] is not None]
    if not priced:
        return None
    return min(priced, key=lambda r: (r["fee_total_source"], -r["expected_value_bdt"]))
