"""Corridor + demo settings.

Values are derived from the default corridor config (config/corridors/uae_bd.json)
so there is a single source of truth. Adding a corridor never touches this file.
"""
import os

from app.services.corridor import DEFAULT_CORRIDOR, load_corridor

_c = load_corridor(DEFAULT_CORRIDOR)

# --- Corridor ---------------------------------------------------------------
CORRIDOR = {
    "source": _c["source_currency"],
    "dest": _c["dest_currency"],
    "source_country": _c["source_country"],
    "dest_country": _c["dest_country"],
    "label": _c["label"],
}

# Bangladesh Bank official cash incentive on inbound formal remittance
# (SME & Remittance Department circulars). The killer differentiator.
GOVT_INCENTIVE_RATE = _c["govt_incentive_rate"]

# --- Demo defaults (locked scenario: 1,000 AED -> mother's bKash) -----------
DEFAULT_AMOUNT = _c["default_amount"]
DEFAULT_PAYOUT = _c["default_payout"]
DEFAULT_RECIPIENT_NAME = _c["default_recipient"]

DEMO_SENDER = _c["demo_sender"]

DEMO_RECIPIENTS = _c["demo_recipients"]

# --- Storage ----------------------------------------------------------------
# In-memory by default; set BORDERLESS_MONEY_DB_PATH=/path/file.sqlite for persistence.
DB_PATH = os.environ.get("BORDERLESS_MONEY_DB_PATH", "")

# --- CORS -------------------------------------------------------------------
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "BORDERLESS_MONEY_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
