"""Layer A — Compliance Gate (v2, corrected matcher).

v1 averaged per-token best matches, so any query whose tokens all appeared in a
listed name scored 1.0 ("Salim" -> BLOCKED) while real variants ("Md Salim",
"Mohammad Salim Hossain") fell under the review threshold. v2 fixes this:

1. Normalize both sides: casefold, strip punctuation, drop connectors
   (bin/binti/binte/ibn, single letters from "s/o"/"d/o"), map the many
   Mohammad spellings to one canonical token, then sort tokens so token-order
   swaps compare equal.
2. Score the normalized FULL names with Jaro-Winkler, plus a token-coverage
   check in both directions.
3. Decision policy (tunable thresholds, see THRESHOLDS):
      BLOCK  only on canonical full-name equality (never on a single-token
             or partial match)
      REVIEW on high full-name similarity, on the query covering all of a
             listed name's tokens (added surname/middle name), or on a
             single-token query that closely matches a listed token
      CLEAR  otherwise
4. Every party result carries a rationale object and is logged.

The sanctions list ships as a local sample (data/ofac_sample.json); production
would load the official SDN export. Excerpts and thresholds are labeled demo.
"""
import difflib
import json
import logging
import re
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "ofac_sample.json"

logger = logging.getLogger("xpay.compliance")

# Tunable decision thresholds (documented in docs/kpis.md and eval output)
THRESHOLDS = {
    "review_full_name": 0.90,   # plain Jaro on normalized full names -> REVIEW
    "review_single_token": 0.90,  # single-token query vs best listed token -> REVIEW
    "token_match": 0.92,        # two tokens considered "the same" for coverage
}

_ALIAS = {
    "md": "mohammad", "mohd": "mohammad", "muhammad": "mohammad",
    "mohammed": "mohammad", "mohamed": "mohammad", "mohammad": "mohammad",
    "mahomed": "mohammad", "mahmad": "mohammad", "mohemmed": "mohammad",
    # corporate suffixes normalize to one token so "Ltd./Co./Company" compare equal
    "co": "company", "ltd": "company", "limited": "company",
    "corp": "company", "corporation": "company", "inc": "company",
}
_CONNECTORS = {"bin", "binti", "binte", "ibn", "bn"}


def normalize_name(name: str) -> str:
    """Canonical form (order-insensitive): see normalize_parts."""
    return normalize_parts(name)[1]


def normalize_parts(name: str) -> tuple[str, str]:
    """Returns (original_order, canonical_sorted). Both lowercase, punctuation
    stripped, aliases mapped, connectors and single letters dropped. The
    original order preserves the common case where the misspelling sits at the
    END of the name (Jaro has no prefix bonus to hide it there); the canonical
    sorted form makes token-order swaps compare equal."""
    s = re.sub(r"[^a-z0-9\s]", " ", str(name).casefold())
    tokens = []
    for tok in s.split():
        if len(tok) == 1 or tok in _CONNECTORS:  # initials + bin/binti/s/o/d/o remnants
            continue
        tokens.append(_ALIAS.get(tok, tok))
    return " ".join(tokens), " ".join(sorted(tokens))


def jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if not len1 or not len2:
        return 0.0
    window = max(len1, len2) // 2 - 1
    window = max(window, 0)
    match1 = [False] * len1
    match2 = [False] * len2
    matches = 0
    transpositions = 0
    for i, ch in enumerate(s1):
        lo, hi = max(i - window, 0), min(i + window + 1, len2)
        for j in range(lo, hi):
            if not match2[j] and s2[j] == ch:
                match1[i] = match2[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    k = 0
    for i in range(len1):
        if match1[i]:
            while not match2[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
    transpositions //= 2
    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0


def jaro_winkler(s1: str, s2: str, prefix_scale: float = 0.1, max_prefix: int = 4) -> float:
    base = jaro(s1, s2)
    if base <= 0.7:
        return base
    prefix = 0
    for a, b in zip(s1, s2):
        if a != b or prefix == max_prefix:
            break
        prefix += 1
    return base + prefix * prefix_scale * (1.0 - base)


def _coverage(query_tokens: list[str], entry_tokens: list[str]) -> tuple[float, float]:
    """(entry_coverage, query_coverage): fraction of each side's tokens matched
    by some token on the other side at >= token_match similarity."""
    def covered(src: list[str], dst: list[str]) -> float:
        if not src:
            return 0.0
        hits = 0
        for t in src:
            best = max((jaro_winkler(t, u) for u in dst), default=0.0)
            hits += best >= THRESHOLDS["token_match"]
        return hits / len(src)

    return covered(entry_tokens, query_tokens), covered(query_tokens, entry_tokens)


def _load_list() -> list[dict]:
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("entries", [])
    except (OSError, ValueError):  # pragma: no cover
        return []


_SDN_LIST = _load_list()


def screen_party(name: str, role: str, entries: list[dict] | None = None) -> dict:
    """Screen one party; returns {role, name, status, best_match, rationale}.

    Full-name score = max(plain Jaro on the normalized original order, on the
    canonical sorted order). Plain Jaro — no Winkler prefix boost — because
    shared leading tokens (the collapsed "mohammad", common surnames) inflate
    the prefix term and over-flag unrelated names.
    """
    norm_query, canonical_query = normalize_parts(name)
    query_tokens = canonical_query.split()
    list_entries = _SDN_LIST if entries is None else entries

    def full_score(norm_entry: str, canonical_entry: str) -> float:
        return max(jaro(norm_query, norm_entry), jaro(canonical_query, canonical_entry))

    best = {"entry": None, "norm": "", "norm_orig": "", "jw": 0.0, "entry_cov": 0.0, "query_cov": 0.0}
    best_single_token = 0.0
    for entry in list_entries:
        norm_entry, canonical_entry = normalize_parts(entry["name"])
        entry_tokens = canonical_entry.split()
        score = full_score(norm_entry, canonical_entry)
        entry_cov, query_cov = _coverage(query_tokens, entry_tokens)
        if (score, entry_cov) > (best["jw"], best["entry_cov"]):
            best = {"entry": entry["name"], "norm": canonical_entry, "norm_orig": norm_entry,
                    "jw": score, "entry_cov": entry_cov, "query_cov": query_cov}
        for tok in entry_tokens:
            best_single_token = max(best_single_token, jaro_winkler(norm_query, tok))

    exact = best["entry"] is not None and canonical_query == best["norm"] and canonical_query != ""
    single_token = len(query_tokens) < 2

    if exact:
        status = "BLOCKED"
        why = "canonical full-name equality after normalization"
    elif best["entry"] is None:
        status = "CLEAR"
        why = "no list entry"
    elif single_token:
        # never hard-block a single-token or partial match
        status = ("FUZZY_MATCH_REVIEW" if best_single_token >= THRESHOLDS["review_single_token"] else "CLEAR")
        why = f"single-token query; best listed-token JW {best_single_token:.3f} (across all entries)"
    elif best["entry_cov"] >= 0.99 or best["jw"] >= THRESHOLDS["review_full_name"]:
        status = "FUZZY_MATCH_REVIEW"
        why = (f"full-name Jaro {best['jw']:.3f}, list-name coverage "
               f"{best['entry_cov']:.0%} (added/variant tokens)")
    else:
        status = "CLEAR"
        why = f"full-name Jaro {best['jw']:.3f} below review threshold"

    rationale = {
        "matched_field": best["entry"],
        "normalized_query": canonical_query,
        "normalized_list": best["norm"],
        "score": round(best["jw"], 4),
        "algorithm": "plain jaro v2 on normalized full names (max of original/canonical order) + token coverage",
        "thresholds": dict(THRESHOLDS),
        "decision_rule": why,
    }
    logger.info("sanctions screen role=%s decision=%s rationale=%s", role, status, rationale)

    return {
        "role": role,
        "name": name,
        "status": status,
        "best_match": ({"name": best["entry"], "similarity": round(best["jw"], 4)}
                       if best["entry"] and status != "CLEAR" else None),
        "rationale": rationale,
    }


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
    """Map an executed transaction onto an ISO 20022 pacs.008-shaped payload.

    Shape subset documented in docs/pacs008-subset.md. The interbank settlement
    amount is the amount that actually settles bank-to-bank — gross minus fees.
    The government incentive is paid separately by the government, so it is
    carried in a documented extension field, not in IntrBkSttlmAmt.
    """
    msg_id = ("BM" + transaction["transaction_id"].replace("-", "")[:8]).upper()[:16]
    breakdown = transaction["breakdown"]
    net = breakdown.get("true_net_receive_bdt")
    if net is None:
        # An ISO message with a made-up amount would be worse than none: an
        # unpriced route must never reach settlement (orchestrator refuses it).
        raise ValueError(
            "cannot produce pacs.008: settlement amount unknown (incomplete pricing)")
    settlement = round(
        net - (breakdown.get("govt_incentive_added_bdt") or 0.0), 2
    )
    incentive = round(breakdown.get("govt_incentive_added_bdt") or 0.0, 2)
    return {
        "MsgId": msg_id,
        "CreDtTm": transaction["created_at"],
        "Dbtr": transaction["sender_name"],
        "Cdtr": transaction["recipient_name"],
        "IntrBkSttlmAmt": {"Ccy": "BDT", "Value": f"{settlement:.2f}"},
        "GovtIncentiveAmt": {"Ccy": "BDT", "Value": f"{incentive:.2f}"},
        "SttlmInf": {"SttlmMtd": "INGD", "ClrSys": "Stellar Hybrid Anchor"},
    }
