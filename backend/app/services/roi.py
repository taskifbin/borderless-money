"""Customer ROI model — transparent, assumption-labeled, Decimal-exact.

Answers one B2B question honestly: "If I plug this API into my remittance
flow, what do I gain and what do I pay?" Every input is a USER ASSUMPTION
(echoed back in `assumptions`), every derived number is a MODELED ESTIMATE —
the output carries these labels so a dashboard can never dress assumptions up
as measurements.

Model contract (docs/PRODUCT_STRATEGY.md §ROI model):

    eligible_transfers   = monthly_transfers x eligibility_share
    adopted_transfers    = eligible_transfers x adoption_rate
    principal_moved      = adopted_transfers x avg_principal
    cost_gap_pct         = baseline_all_in_cost_pct - proposed_all_in_cost_pct
    gross_recipient_benefit  = principal_moved x cost_gap_pct
    customer_cost_savings    = gross_recipient_benefit x customer_cost_bearing_share
    api_revenue (vendor)     = adopted_transfers x api_price_per_tx + api_monthly_fee
    customer_net_benefit     = customer_cost_savings - api_revenue - customer_monthly_costs
    vendor_gross_margin_pct  = (api_revenue - variable costs) / api_revenue   [only if cost inputs given]

Hard honesty rules:
  - recipient benefit is NEVER counted as vendor revenue (it belongs to the
    recipient — this is the 2.5% BD incentive principle applied to our own book);
  - gross margin is None unless the caller supplies real cost inputs;
  - break-even is None with an explanatory note when no positive volume works;
  - scenarios (conservative/base/optimistic) scale adoption and eligibility —
    they are modeled, not measured.
"""
import math
from decimal import ROUND_HALF_UP, Decimal

from app.services.money import D, MoneyValueError

_TWO_DP = Decimal("0.01")


def _pct(value, name) -> Decimal:
    d = D(value)
    if not (0 <= d <= 1):
        raise MoneyValueError(f"{name} must be a fraction in [0, 1], got {d}")
    return d


def _nonneg(value, name) -> Decimal:
    d = D(value)
    if d < 0:
        raise MoneyValueError(f"{name} cannot be negative, got {d}")
    return d


def _q(d: Decimal) -> Decimal:
    return d.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def calculate_roi(
    monthly_transfers,
    avg_principal,
    baseline_all_in_cost_pct,
    proposed_all_in_cost_pct,
    eligibility_share,
    adoption_rate,
    api_price_per_tx=0,
    api_monthly_fee=0,
    customer_cost_bearing_share=1.0,
    customer_monthly_costs=0,
    vendor_variable_cost_per_tx=None,
    horizon_months=12,
) -> dict:
    """Compute the monthly + horizon ROI picture. Raises MoneyValueError on
    malformed inputs; returns labeled modeled values."""
    n_tx = int(monthly_transfers)
    if n_tx <= 0:
        raise MoneyValueError("monthly_transfers must be a positive integer")
    if int(horizon_months) <= 0:
        raise MoneyValueError("horizon_months must be a positive integer")

    principal = D(avg_principal)
    if principal <= 0:
        raise MoneyValueError("avg_principal must be positive")
    baseline = _pct(baseline_all_in_cost_pct, "baseline_all_in_cost_pct")
    proposed = _pct(proposed_all_in_cost_pct, "proposed_all_in_cost_pct")
    if proposed > baseline:
        raise MoneyValueError("proposed_all_in_cost_pct cannot exceed baseline (that would be a loss-making switch)")
    eligibility = _pct(eligibility_share, "eligibility_share")
    adoption = _pct(adoption_rate, "adoption_rate")
    bearing = _pct(customer_cost_bearing_share, "customer_cost_bearing_share")
    price_per_tx = _nonneg(api_price_per_tx, "api_price_per_tx")
    monthly_fee = _nonneg(api_monthly_fee, "api_monthly_fee")
    cust_costs = _nonneg(customer_monthly_costs, "customer_monthly_costs")

    eligible_tx = _q(Decimal(n_tx) * eligibility)
    adopted_tx = _q(eligible_tx * adoption)
    principal_moved = _q(adopted_tx * principal)
    cost_gap = baseline - proposed
    recipient_benefit = _q(principal_moved * cost_gap)
    customer_savings = _q(recipient_benefit * bearing)
    api_revenue = _q(adopted_tx * price_per_tx + monthly_fee)
    customer_net = _q(customer_savings - api_revenue - cust_costs)
    cost_per_tx = _q(api_revenue / adopted_tx) if adopted_tx > 0 else None

    # Break-even monthly volume: smallest n_tx where customer_net >= 0.
    # net(n) = n x elig x adopt x (saving_per_tx - price_per_tx) - fee - costs
    saving_per_adopted = _q(principal * cost_gap * bearing) - price_per_tx
    fixed_drag = monthly_fee + cust_costs
    if adopted_tx > 0:
        observed_net = customer_savings - api_revenue - cust_costs
    else:
        observed_net = -(monthly_fee + cust_costs)
    if fixed_drag == 0:
        breakeven_monthly = Decimal(0)
        breakeven_note = "no fixed costs or fees to recover — profitable at any volume"
    elif saving_per_adopted <= 0 or eligibility == 0 or adoption == 0:
        breakeven_monthly = None
        breakeven_note = ("no positive break-even: per-transfer saving does not exceed the "
                          "per-transfer API price, or eligibility/adoption is zero under "
                          "the current assumptions")
    else:
        breakeven_monthly = _q(Decimal(math.ceil(
            fixed_drag / (eligibility * adoption * saving_per_adopted))))
        breakeven_note = "smallest monthly transfer count at which customer net benefit turns non-negative"

    margin_pct = None
    if vendor_variable_cost_per_tx is not None:
        var_cost = _nonneg(vendor_variable_cost_per_tx, "vendor_variable_cost_per_tx")
        if api_revenue > 0:
            margin_pct = _q((api_revenue - adopted_tx * var_cost) / api_revenue * 100)
        else:
            margin_pct = None

    scenarios = {}
    for name, adopt_mult, elig_mult in (("conservative", "0.5", "0.8"),
                                        ("base", "1", "1"),
                                        ("optimistic", "1.5", "1")):
        s_elig = min(eligibility * D(elig_mult), Decimal(1))
        s_adopt = min(adoption * D(adopt_mult), Decimal(1))
        s_adopted = _q(_q(Decimal(n_tx) * s_elig) * s_adopt)
        s_moved = _q(s_adopted * principal)
        s_benefit = _q(s_moved * cost_gap)
        s_savings = _q(s_benefit * bearing)
        s_revenue = _q(s_adopted * price_per_tx + monthly_fee)
        s_net = _q(s_savings - s_revenue - cust_costs)
        scenarios[name] = {
            "adopted_transfers": s_adopted,
            "gross_recipient_benefit": s_benefit,
            "customer_cost_savings": s_savings,
            "api_revenue": s_revenue,
            "customer_net_benefit": s_net,
        }

    horizon = int(horizon_months)
    return {
        "unit": "source-currency value where money, % where rates",
        "labels": {
            "monthly_transfers": "user_assumption", "avg_principal": "user_assumption",
            "baseline_all_in_cost_pct": "user_assumption",
            "proposed_all_in_cost_pct": "user_assumption",
            "eligibility_share": "user_assumption", "adoption_rate": "user_assumption",
            "api_price_per_tx": "user_assumption", "api_monthly_fee": "user_assumption",
            "customer_cost_bearing_share": "user_assumption",
            "customer_monthly_costs": "user_assumption",
            "vendor_variable_cost_per_tx": "user_assumption" if vendor_variable_cost_per_tx is not None else "not_provided",
            "all_derived_values": "modeled_estimate",
        },
        "monthly": {
            "eligible_transfers": eligible_tx,
            "adopted_transfers": adopted_tx,
            "principal_moved": principal_moved,
            "gross_recipient_benefit": recipient_benefit,
            "customer_cost_savings": customer_savings,
            "api_revenue": api_revenue,
            "customer_net_benefit": customer_net,
            "customer_cost_per_transaction": cost_per_tx,
            "vendor_gross_margin_pct": margin_pct,
        },
        "horizon": {
            "months": horizon,
            "gross_recipient_benefit": _q(recipient_benefit * horizon),
            "customer_cost_savings": _q(customer_savings * horizon),
            "api_revenue": _q(api_revenue * horizon),
            "customer_net_benefit": _q(customer_net * horizon),
        },
        "break_even": {
            "monthly_transfers": breakeven_monthly,
            "note": breakeven_note,
        },
        "scenarios": {k: {kk: _q(vv) for kk, vv in v.items()} for k, v in scenarios.items()},
        "assumptions_echo": {
            "monthly_transfers": n_tx, "avg_principal": str(_q(principal)),
            "baseline_all_in_cost_pct": str(baseline), "proposed_all_in_cost_pct": str(proposed),
            "eligibility_share": str(eligibility), "adoption_rate": str(adoption),
            "api_price_per_tx": str(price_per_tx), "api_monthly_fee": str(monthly_fee),
            "customer_cost_bearing_share": str(bearing),
            "customer_monthly_costs": str(_q(cust_costs)),
            "vendor_variable_cost_per_tx": str(_q(D(vendor_variable_cost_per_tx))) if vendor_variable_cost_per_tx is not None else None,
        },
        "disclaimer": ("All outputs are modeled estimates from user-supplied assumptions; "
                       "none are measured. Recipient benefit is money that stays with the "
                       "recipient and is never counted as vendor revenue."),
    }
