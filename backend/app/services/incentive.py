"""True Net Receive engine — the killer differentiator.

Calculates the exact amount the recipient gets, including the Bangladesh
Bank's official 2.5% cash incentive for formal remittance:

    True Net Receive = (Amount x FX) - Fees + (Amount x FX x 0.025)

Pure, deterministic, dependency-free — exactly testable.
"""
from app import config


def calculate_true_net_receive(
    amount_source: float,
    fx_rate: float,
    fee_source: float,
    route: str = "",
    settlement_time_hrs: float | None = None,
    currency_source: str = "AED",
    dest_currency: str = "BDT",
    govt_incentive_rate: float | None = None,
) -> dict:
    """Price one route and return the full receipt-style breakdown (BDT)."""
    rate = config.GOVT_INCENTIVE_RATE if govt_incentive_rate is None else govt_incentive_rate

    gross_bdt = amount_source * fx_rate
    fees_deducted_bdt = fee_source * fx_rate
    govt_incentive_bdt = gross_bdt * rate
    true_net_bdt = gross_bdt - fees_deducted_bdt + govt_incentive_bdt

    breakdown = {
        "amount_source": round(amount_source, 2),
        "currency_source": currency_source,
        "fx_rate": fx_rate,
        "fee_source": round(fee_source, 2),
        "gross_bdt": round(gross_bdt, 2),
        "fees_deducted_bdt": round(fees_deducted_bdt, 2),
        "govt_incentive_rate": rate,
        "govt_incentive_added_bdt": round(govt_incentive_bdt, 2),
        "true_net_receive_bdt": round(true_net_bdt, 2),
        "route": route,
    }
    if settlement_time_hrs is not None:
        breakdown["settlement_time_hrs"] = settlement_time_hrs
    return breakdown
