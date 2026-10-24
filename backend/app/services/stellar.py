"""Execution layer — clearly-labeled SIMULATED settlement only.

Step 5 honesty note: an earlier version "attempted" a testnet path payment from
the project's own account to itself using self-issued AED/BDT assets with equal
send/destination amounts. That cannot work — it requires trustlines, an offer,
and a counterparty — and would always have failed silently into the simulated
fallback, which misrepresented the system. This module now simulates by design
and NEVER shows a TESTNET state unless a real settlement hash has been recorded
(see REAL_VS_SIMULATED.md for the exact steps a real demo requires).
"""
import hashlib
import uuid


def _memo(tx_seed: str) -> str:
    return "BM-" + hashlib.sha256(tx_seed.encode()).hexdigest()[:8].upper()


def _simulated_hash(tx_seed: str) -> str:
    return hashlib.sha256(("borderless-money:" + tx_seed).encode()).hexdigest()


def simulate_settlement(route_name: str, amount_source: float,
                        outcome: str = "COMPLETED") -> dict:
    """Deterministic, clearly-labeled simulated settlement result.

    `outcome` exists so the demo/eval can exercise the uncertain-settlement
    path honestly: TIMEOUT/FAILED are returned as exactly that — never
    relabeled as success downstream. Only COMPLETED carries a hash."""
    tx_seed = uuid.uuid4().hex
    if outcome == "COMPLETED":
        return {
            "status": "COMPLETED",
            "stellar_hash": _simulated_hash(tx_seed),
            "network": "SIMULATED",
            "simulated": True,
            "memo": _memo(tx_seed),
            "fallback_reason": "simulated by design — no funded testnet credentials configured",
            "explorer_url": None,
        }
    if outcome in ("TIMEOUT", "FAILED"):
        return {
            "status": outcome,
            "stellar_hash": None,
            "network": "SIMULATED",
            "simulated": True,
            "memo": _memo(tx_seed),
            "fallback_reason": (
                f"simulated {outcome.lower()} injected by the demo harness — "
                "execution status is UNCERTAIN and must be reconciled; "
                "this is never a success"),
            "explorer_url": None,
            "reconciliation_required": True,
        }
    raise ValueError(f"unknown settlement outcome: {outcome!r}")
