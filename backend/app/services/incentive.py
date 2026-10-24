"""True Net Receive engine — the killer differentiator.

Calculates the exact amount the recipient gets, including the Bangladesh
Bank's official 2.5% cash incentive for formal remittance.

Pure, deterministic, dependency-free, and computed entirely in exact Decimal
arithmetic (see money.py). Binary floats are used only for display
serialization at the API edge; every breakdown also carries the exact decimal
string (`*_exact` fields) which is the authoritative value.

Calculation model (full contract in docs/FINANCIAL_MODEL.md):

    gross_dest   = principal_source x fx_rate
    fees_dest    = fee_source x fx_rate          (fees quoted in SOURCE currency
                                                  and converted at the same rate;
                                                  pass fee_currency="DEST" for
                                                  fees already priced in BDT)
    incentive    = gross_dest x incentive_rate   (computed on the converted
                                                  principal BEFORE fee deduction —
                                                  BB incentive attaches to the
                                                  remitted amount, not the fee)
    true_net     = gross_dest - fees_dest + incentive

Anti-double-counting: fx_rate is the ALL-IN customer rate — any provider spread
is understood to be embedded IN it, never added again as a separate fee line.
Missing fee data is surfaced (`fee_info_missing`), never silently zeroed: an
incomplete quote returns net = None instead of a falsely precise number.
"""
from app import config
from app.services.money import D, MoneyValueError, quantize, to_number

# Keys the legacy float wrapper guarantees (backward compatibility with
# test_core.py / orchestrator receipts).
_FLOAT_KEYS = (
    "amount_source", "fee_source", "gross_bdt", "fees_deducted_bdt",
    "govt_incentive_added_bdt", "true_net_receive_bdt",
)


def calculate_true_net_receive_exact(
    amount_source,
    fx_rate,
    fee_source=None,
    route: str = "",
    settlement_time_hrs=None,
    currency_source: str = "AED",
    dest_currency: str = "BDT",
    govt_incentive_rate=None,
    fee_currency: str = "SOURCE",
) -> dict:
    """Price one route in exact Decimal. Returns {"values": {...Decimal...},
    "incomplete": bool, "missing": [str], "currency_dest": str}.

    Raises MoneyValueError (a ValueError) for negative/zero principal, non-
    positive FX rates, or malformed numeric input. A missing fee (None) does
    NOT raise: it marks the quote incomplete and withholds the net figure.
    """
    amount = D(amount_source)
    rate_fx = D(fx_rate)
    if amount <= 0:
        raise MoneyValueError(f"transfer principal must be positive, got {amount}")
    if rate_fx <= 0:
        raise MoneyValueError(f"fx rate must be positive, got {rate_fx}")

    incentive_rate = D(config.GOVT_INCENTIVE_RATE if govt_incentive_rate is None else govt_incentive_rate)
    if not (0 <= incentive_rate <= 1):
        raise MoneyValueError(f"incentive rate must be within [0, 1], got {incentive_rate}")

    missing: list[str] = []
    fee = None
    if fee_source is None:
        missing.append("fee_source")
    else:
        fee = D(fee_source)
        if fee < 0:
            raise MoneyValueError(f"fee cannot be negative, got {fee}")

    gross = amount * rate_fx
    if fee is None:
        fees_dest = None
    elif (fee_currency or "SOURCE").upper() == "SOURCE":
        fees_dest = fee * rate_fx
    else:
        fees_dest = fee
    incentive = gross * incentive_rate if not missing else None
    net = None if missing else (gross - fees_dest + incentive)

    q_src = lambda v: None if v is None else quantize(v, currency_source)
    q_dst = lambda v: None if v is None else quantize(v, dest_currency)
    values = {
        "amount_source": q_src(amount),
        "fee_source": q_src(fee),
        "fx_rate": rate_fx,
        "gross_dest": q_dst(gross),
        "fees_deducted_dest": q_dst(fees_dest),
        "govt_incentive_rate": incentive_rate,
        "govt_incentive_dest": q_dst(incentive),
        "true_net_dest": q_dst(net),
    }
    return {
        "values": values,
        "incomplete": bool(missing),
        "missing": missing,
        "currency_source": currency_source,
        "currency_dest": dest_currency,
        "route": route,
    }


def calculate_true_net_receive(
    amount_source,
    fx_rate,
    fee_source=None,
    route: str = "",
    settlement_time_hrs=None,
    currency_source: str = "AED",
    dest_currency: str = "BDT",
    govt_incentive_rate=None,
    fee_currency: str = "SOURCE",
) -> dict:
    """Backward-compatible breakdown (display floats) + exact decimal strings.

    Display floats are quantized ROUND_HALF_UP to 2dp by the engine first, so
    the float a client sees is the faithful rendering of the exact value, not a
    re-rounding of a binary artifact. If the fee is missing, the fee/net fields
    are None and `pricing_completeness` says so — never a silent zero.
    """
    exact = calculate_true_net_receive_exact(
        amount_source, fx_rate, fee_source, route=route,
        settlement_time_hrs=settlement_time_hrs, currency_source=currency_source,
        dest_currency=dest_currency, govt_incentive_rate=govt_incentive_rate,
        fee_currency=fee_currency,
    )
    v = exact["values"]
    dest = exact["currency_dest"]
    dest_field = "bdt" if dest == "BDT" else dest.lower()
    num = lambda d: to_number(d) if d is not None else None

    breakdown = {
        "amount_source": num(v["amount_source"]),
        "currency_source": exact["currency_source"],
        "fx_rate": num(v["fx_rate"]),
        "fee_source": num(v["fee_source"]),
        f"gross_{dest_field}": num(v["gross_dest"]),
        f"fees_deducted_{dest_field}": num(v["fees_deducted_dest"]),
        "govt_incentive_rate": num(v["govt_incentive_rate"]),
        f"govt_incentive_added_{dest_field}": num(v["govt_incentive_dest"]),
        f"true_net_receive_{dest_field}": num(v["true_net_dest"]),
        # legacy key names (kept for API compatibility; only truthful for BDT dest)
        "gross_bdt": num(v["gross_dest"]) if dest == "BDT" else None,
        "fees_deducted_bdt": num(v["fees_deducted_dest"]) if dest == "BDT" else None,
        "govt_incentive_added_bdt": num(v["govt_incentive_dest"]) if dest == "BDT" else None,
        "true_net_receive_bdt": num(v["true_net_dest"]) if dest == "BDT" else None,
        "route": exact["route"],
        # exact decimal strings — authoritative values
        "gross_exact": str(v["gross_dest"]),
        "fees_deducted_exact": str(v["fees_deducted_dest"]),
        "govt_incentive_exact": str(v["govt_incentive_dest"]),
        "true_net_receive_exact": str(v["true_net_dest"]),
        "pricing_completeness": "incomplete" if exact["incomplete"] else "complete",
        "missing_fields": exact["missing"],
        "arithmetic": "exact-decimal (ROUND_HALF_UP at display edge)",
    }
    if exact["incomplete"]:
        breakdown["data_quality_note"] = (
            "Fee information missing for this route: fees are NOT assumed to be "
            "zero and no net figure is produced — the route is flagged ineligible "
            "for ranking until pricing is complete."
        )
    if settlement_time_hrs is not None:
        breakdown["settlement_time_hrs"] = settlement_time_hrs
    return breakdown
