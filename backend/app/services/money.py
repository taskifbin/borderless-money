"""Exact-decimal money helpers — the arithmetic substrate for all financial math.

Money never passes through binary floating point inside the engines: amounts
arrive from JSON/HTTP (float) and are converted ONCE via the shortest
round-trip decimal representation (repr(float)), after which every operation is
exact Decimal arithmetic. Quantization (presentation rounding) happens only at
the edges, always ROUND_HALF_UP, at the currency's minor unit.

Rounding rules (docs/FINANCIAL_MODEL.md):
  - intermediate results stay at full Decimal precision (28 significant digits)
  - only displayed/settled values are quantized, to the currency minor unit
  - ROUND_HALF_UP everywhere (never banker's rounding for display amounts)
"""
import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# ISO 4217 minor-unit exponents for currencies this product touches or may
# touch next. Anything unlisted defaults to 2 (the overwhelmingly common case).
CURRENCY_EXPONENTS = {
    "AED": 2, "BDT": 2, "USD": 2, "SAR": 2, "EUR": 2, "GBP": 2, "INR": 2,
    "JPY": 0, "KRW": 0, "KWD": 3, "BHD": 3, "OMR": 3,
}
DEFAULT_EXPONENT = 2


class MoneyValueError(ValueError):
    """Raised for amounts that cannot be money: NaN, ±inf, negative, malformed."""


def D(value) -> Decimal:
    """Convert to Decimal exactly. Floats go through their shortest round-trip
    decimal repr (so 32.8 becomes Decimal('32.8'), not the binary expansion).
    Rejects NaN/inf and non-numeric types — silently coercing garbage into a
    monetary value is how financial bugs are born."""
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, bool):  # bool is an int subclass — reject explicitly
        raise MoneyValueError(f"boolean is not a monetary value: {value!r}")
    elif isinstance(value, int):
        d = Decimal(value)
    elif isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise MoneyValueError(f"non-finite monetary value: {value!r}")
        d = Decimal(repr(value))
    elif isinstance(value, str):
        try:
            d = Decimal(value.strip())
        except InvalidOperation as exc:
            raise MoneyValueError(f"malformed monetary value: {value!r}") from exc
    else:
        raise MoneyValueError(f"unsupported monetary type: {type(value).__name__}")
    if not d.is_finite():
        raise MoneyValueError(f"non-finite monetary value: {value!r}")
    return d


def exponent_for(currency: str) -> int:
    return CURRENCY_EXPONENTS.get((currency or "").upper(), DEFAULT_EXPONENT)


def quantize(value: Decimal, currency: str = "BDT") -> Decimal:
    """Round to the currency's minor unit, ROUND_HALF_UP (2.005 -> 2.01)."""
    exp = Decimal(1).scaleb(-exponent_for(currency))
    return D(value).quantize(exp, rounding=ROUND_HALF_UP)


def to_number(value: Decimal) -> float:
    """Display serialization for the API/UI layer: a float the client can
    format. The exact value always travels alongside as a string (*_exact
    fields) — the float is presentation, the string is the truth."""
    return float(value)
