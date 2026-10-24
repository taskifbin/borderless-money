"""Layer A — Compliance Gate.

OFAC sanctions screening with fuzzy matching (zero silent false rejections:
exact hit -> BLOCKED, >= 85% similarity -> human review, else CLEAR), plus an
ISO 20022 pacs.008 mapping attached to every executed transaction.
"""
import difflib
import json
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "ofac_sample.json"

FUZZY_REVIEW_THRESHOLD = 0.85


def _load_list() -> list[dict]:
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("entries", [])
    except (OSError, ValueError):  # pragma: no cover
        return []


_SDN_LIST = _load_list()


def _similarity(a: str, b: str) -> float:
    """Name similarity in [0,1]: best of full-string ratio and per-token ratios."""
    a_l, b_l = a.lower().strip(), b.lower().strip()
    full = difflib.SequenceMatcher(None, a_l, b_l).ratio()
    tokens_a, tokens_b = a_l.split(), b_l.split()
    token_scores = []
    for ta in tokens_a:
        best = max((difflib.SequenceMatcher(None, ta, tb).ratio() for tb in tokens_b), default=0.0)
        token_scores.append(best)
    token_avg = sum(token_scores) / len(token_scores) if token_scores else 0.0
    return max(full, token_avg)


def screen_party(name: str, role: str, entries: list[dict] | None = None) -> dict:
    """Screen one party against the (sample) sanctions list."""
    list_entries = _SDN_LIST if entries is None else entries
    best_name, best_score = None, 0.0
    for entry in list_entries:
        score = _similarity(name, entry["name"])
        if score > best_score:
            best_name, best_score = entry["name"], score

    if best_score >= 0.999:
        return {"role": role, "name": name, "status": "BLOCKED",
                "best_match": {"name": best_name, "similarity": round(best_score, 4)}}
    if best_score >= FUZZY_REVIEW_THRESHOLD:
        return {"role": role, "name": name, "status": "FUZZY_MATCH_REVIEW",
                "best_match": {"name": best_name, "similarity": round(best_score, 4)}}
    return {"role": role, "name": name, "status": "CLEAR", "best_match": None}


def screen_transaction(sender_name: str, recipient_name: str,
                       entries: list[dict] | None = None) -> dict:
    parties = [
        screen_party(sender_name, "sender", entries),
        screen_party(recipient_name, "recipient", entries),
    ]
    statuses = {p["status"] for p in parties}
    if "BLOCKED" in statuses:
        overall = "BLOCKED"
    elif "FUZZY_MATCH_REVIEW" in statuses:
        overall = "FUZZY_MATCH_REVIEW"
    else:
        overall = "CLEAR"
    return {"ofac_match_status": overall, "screened_parties": parties}


def to_pacs_008(transaction: dict) -> dict:
    """Map an executed transaction onto an ISO 20022 pacs.008-shaped payload."""
    msg_id = ("BM" + transaction["transaction_id"].replace("-", "")[:8]).upper()[:16]
    amount = transaction["breakdown"]["true_net_receive_bdt"]
    return {
        "MsgId": msg_id,
        "CreDtTm": transaction["created_at"],
        "Dbtr": transaction["sender_name"],
        "Cdtr": transaction["recipient_name"],
        "IntrBkSttlmAmt": {"Ccy": "BDT", "Value": f"{amount:.2f}"},
        "SttlmInf": {"SttlmMtd": "INGD", "ClrSys": "Stellar Hybrid Anchor"},
    }
