"""Live Stellar Horizon probe — connectivity truth, never fake settlement data.

Step 4/5 honesty: the demo does not query a real order book for corridor assets
(no AED/BDT issuers exist on testnet), so rail rates remain labeled static
samples. What IS live is the Horizon reachability probe below — it reports,
with a timestamp, whether the Stellar testnet API is reachable from here.
"""
import json
import urllib.request
from datetime import datetime, timezone

HORIZON_TESTNET = "https://horizon-testnet.stellar.org"


def probe(timeout: int = 3) -> dict:
    result = {
        "service": "stellar-horizon-testnet",
        "url": HORIZON_TESTNET,
        "reachable": False,
        "detail": "",
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        with urllib.request.urlopen(HORIZON_TESTNET, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            result["reachable"] = resp.status == 200
            result["detail"] = f"horizon version {body.get('core_version', 'unknown')}"
    except Exception as exc:  # noqa: BLE001 — a probe reports, it never raises
        result["detail"] = f"unreachable: {type(exc).__name__}"
    return result
