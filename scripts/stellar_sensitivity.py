"""Stellar rail sensitivity — how much anchor spread can the headline survive?

The +3.05% uplift headline assumes the Stellar Hybrid Anchor quotes a customer
FX rate ~1.0% inside the mid-market rate. This script re-prices the best route
across pessimistic anchor spreads (0.5% / 1.0% / 1.5%) and reports whether the
headline still clears the >= 3.0% internal target.

Deterministic, stdlib-only. Run:  python3 scripts/stellar_sensitivity.py
Writes nothing; prints a markdown table (paste into docs/stellar-sensitivity.md).
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.incentive import calculate_true_net_receive_exact  # noqa: E402
from app.services.money import D, to_number  # noqa: E402

CFG = json.load(open(BACKEND / "config" / "corridors" / "uae_bd.json"))
AMOUNT = 1000.0
PAYOUT = "BKASH"
PLATFORM = D(CFG["platform_fee_source"])
SPREADS = ["0.005", "0.010", "0.015"]


def legacy_swift_net() -> str:
    """The counterfactual /metrics uses: same SWIFT rail, no platform fee."""
    rail = next(r for r in CFG["rails"] if r["name"] == "Traditional SWIFT")
    lm = CFG["last_mile"][PAYOUT]["Traditional SWIFT"][0]
    exact = calculate_true_net_receive_exact(
        AMOUNT, rail["fx"], D(rail["fee_source"]) + D(lm),
        currency_source=CFG["source_currency"], dest_currency=CFG["dest_currency"],
        govt_incentive_rate=CFG["govt_incentive_rate"], platform_fee_source=0,
    )
    return str(exact["values"]["true_net_dest"])


def stellar_net_at_spread(spread: str) -> dict:
    rail = next(r for r in CFG["rails"] if r["name"] == "Stellar Hybrid Anchor")
    lm = CFG["last_mile"][PAYOUT]["Stellar Hybrid Anchor"][0]
    fx = D(CFG["mid_market_rate"]) * (D(1) - D(spread))
    return calculate_true_net_receive_exact(
        AMOUNT, fx, D(rail["fee_source"]) + D(lm),
        currency_source=CFG["source_currency"], dest_currency=CFG["dest_currency"],
        govt_incentive_rate=CFG["govt_incentive_rate"],
        platform_fee_source=PLATFORM,
    )


def main() -> None:
    legacy = D(legacy_swift_net())
    print(f"Legacy counterfactual (SWIFT, no platform fee): {legacy} BDT")
    print(f"xPay platform fee: {PLATFORM} AED | incentive rate: {CFG['govt_incentive_rate']}")
    print()
    print("| Anchor spread | Stellar customer FX | Best-route net (BDT) | Uplift vs legacy | Meets >= 3.0% target |")
    print("| ---: | ---: | ---: | ---: | :--- |")
    rows = []
    for spread in SPREADS:
        priced = stellar_net_at_spread(spread)
        net = D(str(priced["values"]["true_net_dest"]))
        uplift = float(round((net / legacy - 1) * 100, 2))
        meets = "yes" if uplift >= 3.0 else "**NO**"
        fx = D(CFG["mid_market_rate"]) * (D(1) - D(spread))
        print(f"| {float(spread)*100:.1f}% | {to_number(fx):.4f} | {net} | +{uplift:.2f}% | {meets} |")
        rows.append({"spread": float(spread), "fx": to_number(fx),
                     "net_bdt": str(net), "uplift_pct": uplift, "meets_target": uplift >= 3.0})
    print()
    print("json:", json.dumps(rows))


if __name__ == "__main__":
    main()
