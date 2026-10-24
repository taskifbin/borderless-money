"""Quote lifecycle — persisted quotes with TTL, confirmation binding, revalidation.

A quote is what the user saw and confirmed. Execution must be bound to exactly
that quote: same route, same amount, still valid. This module gives every
quote a durable ID, an expiry (TTL from corridor config, default 60 minutes),
and a revalidation gate that execution cannot skip.

Error codes (surfaced verbatim to API callers):
  quote_not_found   — unknown quote ID
  quote_expired     — quote past its expires_at; a fresh quote must be requested
  route_not_in_quote — requested route was not part of the quoted set
  amount_mismatch   — execution amount differs from the quoted amount
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.services import store

DEFAULT_TTL_MINUTES = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def default_ttl_minutes(corridor_cfg: dict | None = None) -> int:
    if corridor_cfg and "quote_ttl_minutes" in corridor_cfg:
        return int(corridor_cfg["quote_ttl_minutes"])
    return DEFAULT_TTL_MINUTES


def create_quote(*, corridor: str, amount, payout_method: str, routes: list,
                 selected_route_name: str | None, decision: str,
                 ttl_minutes: int | None = None) -> dict:
    """Persist a quote artifact. `routes` is stored verbatim (display floats +
    exact strings) so the confirmation receipt is reproducible later. With no
    explicit selection the quote defaults to the best-ranked route."""
    ttl = int(ttl_minutes) if ttl_minutes is not None else DEFAULT_TTL_MINUTES
    if ttl <= 0:
        raise ValueError(f"quote ttl must be positive, got {ttl}")
    if not selected_route_name and routes:
        selected_route_name = routes[0].get("name")
    now = _now()
    quote = {
        "quote_id": "q_" + uuid.uuid4().hex[:12],
        "corridor": corridor,
        "amount": amount,
        "payout_method": payout_method,
        "route_names": [r["name"] for r in routes],
        "selected_route_name": selected_route_name,
        "decision": decision,
        "routes": routes,
        "status": "ACTIVE",
        "created_at": _iso(now),
        "expires_at": _iso(now + timedelta(minutes=ttl)),
        "ttl_minutes": ttl,
        "data_label": "fixture-snapshot" if all(
            r.get("pricing_completeness") == "complete" for r in routes) else "partial-pricing",
    }
    return store.save_quote(quote)


def get_quote(quote_id: str) -> dict | None:
    """Fetch a quote; expiry status is computed live, never trusted from storage."""
    quote = store.get_quote(quote_id)
    if quote is None:
        return None
    quote = {**quote, "status": _live_status(quote)}
    return quote


def _live_status(quote: dict) -> str:
    expires = datetime.strptime(quote["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return "EXPIRED" if _now() >= expires else "ACTIVE"


def revalidate(quote_id: str, *, selected_route_name: str | None = None,
               amount=None, payout_method: str | None = None) -> tuple[dict | None, str | None]:
    """Gate before execution. Returns (quote, error_code). error_code None ⇒ OK.
    A quote that was already consumed for execution is rejected (single use)."""
    quote = get_quote(quote_id)
    if quote is None:
        return None, "quote_not_found"
    if quote["status"] == "EXPIRED":
        return quote, "quote_expired"
    if quote.get("consumed_at"):
        return quote, "quote_already_used"
    if selected_route_name is not None and selected_route_name not in quote["route_names"]:
        return quote, "route_not_in_quote"
    if amount is not None and float(amount) != float(quote["amount"]):
        return quote, "amount_mismatch"
    if payout_method is not None and (payout_method or "").upper() != quote["payout_method"]:
        return quote, "payout_method_mismatch"
    return quote, None


def consume_quote(quote_id: str) -> dict | None:
    """Mark a quote as used by an execution (single-use: a confirmed quote
    cannot fund two transfers). Returns the updated quote."""
    quote = store.get_quote(quote_id)
    if quote is None:
        return None
    quote["consumed_at"] = _iso(_now())
    quote["status"] = "CONSUMED"
    return store.save_quote(quote)
