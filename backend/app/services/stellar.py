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


def simulate_settlement(route_name: str, amount_source: float) -> dict:
    """Deterministic, clearly-labeled simulated settlement result."""
    tx_seed = uuid.uuid4().hex
    return {
        "status": "COMPLETED",
        "stellar_hash": _simulated_hash(tx_seed),
        "network": "SIMULATED",
        "simulated": True,
        "memo": _memo(tx_seed),
        "fallback_reason": "simulated by design — no funded testnet credentials configured",
        "explorer_url": None,
    }
