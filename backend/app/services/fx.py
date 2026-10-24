"""FX reference data. Demo snapshot; swap for Chainlink feed in production."""
import json
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "fx_rates.json"


def _load() -> dict:
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"mid_market": {"AED_BDT": 33.15}, "updated": "static-fallback"}


_SNAPSHOT = _load()


def get_mid_market(source: str = "AED", dest: str = "BDT") -> float:
    """Mid-market rate for the corridor (demo snapshot)."""
    mid = _SNAPSHOT.get("mid_market", 33.15)
    if isinstance(mid, dict):  # defensive: keyed form {"AED_BDT": 33.15}
        mid = mid.get(f"{source}_{dest}", 33.15)
    return float(mid)


def snapshot_meta() -> dict:
    return {"pair": "AED/BDT", "mid_market": get_mid_market(), "updated": _SNAPSHOT.get("updated"), "source": _SNAPSHOT.get("source")}
