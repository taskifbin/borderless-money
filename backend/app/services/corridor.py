"""Corridor configuration loader.

Every corridor's rules — FX snapshot, incentive rate, rails, last-mile fees,
sanctions list, demo persona — live in backend/config/corridors/<code>.json.
Adding a corridor is adding a file; no code changes.

JSON (not YAML) keeps the loader stdlib-only so the test suite runs on a bare
Python install.
"""
import json
from functools import lru_cache
from pathlib import Path

CORRIDOR_DIR = Path(__file__).resolve().parents[2] / "config" / "corridors"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DEFAULT_CORRIDOR = "uae_bd"


@lru_cache(maxsize=8)
def load_corridor(code: str = DEFAULT_CORRIDOR) -> dict:
    path = CORRIDOR_DIR / f"{code}.json"
    if not path.exists():
        raise ValueError(f"Unknown corridor '{code}' (no config at {path})")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    required = ("code", "label", "source_currency", "dest_currency", "mid_market_rate",
                "govt_incentive_rate", "rails", "last_mile", "payout_methods")
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Corridor '{code}' config missing keys: {missing}")
    return cfg


@lru_cache(maxsize=8)
def load_sanctions(code: str = DEFAULT_CORRIDOR) -> list[dict]:
    """Sanctions entries for a corridor (local JSON sample in this demo)."""
    cfg = load_corridor(code)
    path = DATA_DIR / cfg.get("sanctions_list", "ofac_sample.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("entries", [])
    except (OSError, ValueError):
        return []


def available_corridors() -> list[str]:
    return sorted(p.stem for p in CORRIDOR_DIR.glob("*.json"))
