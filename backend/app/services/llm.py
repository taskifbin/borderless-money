"""Bounded LLM access (Step 3). The deterministic path is ALWAYS the default.

Design rules enforced here:
- No key → every LLM helper reports disabled and the caller uses the
  deterministic path (the API behavior is identical; /api/health shows the
  state and the UI labels it).
- LLM output is never trusted: strict JSON-schema validation, bounded types,
  and any failure returns (None, reason) so callers fall back.
- Live calls time out fast and log only metadata (never raw prompts — they may
  contain user names).
- Tests inject `llm_fn` stubs; nothing in the test suite touches the network.
"""
import json
import logging
import os
import re
import urllib.request

logger = logging.getLogger("xpay.llm")

DEFAULT_TIMEOUT_S = 6

INTENT_SCHEMA = {
    "corridor": str,
    "amount": (int, float),
    "currency": str,
    "recipient": (str, type(None)),
    "urgency": str,
}
ALLOWED_URGENCY = {"normal", "urgent"}


def is_enabled() -> bool:
    """True only when an API key is configured. No key = deterministic mode."""
    return bool(os.environ.get("XPAY_LLM_API_KEY"))


def _extract_json(raw: str) -> str:
    """Pull the first JSON object out of a (possibly markdown-fenced) reply."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        return fence.group(1)
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    return brace.group(0) if brace else raw


def _call_live(prompt: str) -> str:
    """OpenAI-compatible chat completion. Only called when is_enabled()."""
    base = os.environ.get("XPAY_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("XPAY_LLM_MODEL", "gpt-4o-mini")
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode(),
        headers={"Authorization": f"Bearer {os.environ['XPAY_LLM_API_KEY']}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_S) as resp:
        body = json.loads(resp.read().decode())
    return body["choices"][0]["message"]["content"]


def validate_schema(data, schema: dict) -> str | None:
    """Strict validation; returns an error string or None. Bools are rejected
    where numeric/str types are expected (bool subclasses int in Python)."""
    if not isinstance(data, dict):
        return "not-an-object"
    for key, types in schema.items():
        allowed = types if isinstance(types, tuple) else (types,)
        if key not in data:
            return f"missing:{key}"
        value = data[key]
        if value is None and type(None) in allowed:
            continue
        if isinstance(value, bool) and bool not in allowed:
            return f"bad-type:{key}"
        if not isinstance(value, allowed):
            return f"bad-type:{key}"
    amount = data.get("amount")
    if amount is not None and (isinstance(amount, bool) or amount <= 0):
        return "bad-amount"
    if data.get("urgency") is not None and data["urgency"] not in ALLOWED_URGENCY:
        return "bad-urgency"
    return None


def complete_text(prompt: str, *, llm_fn=None, timeout: int = DEFAULT_TIMEOUT_S) -> tuple[str | None, str | None]:
    """Bounded text completion. Returns (text, None) or (None, reason)."""
    if llm_fn is None:
        if not is_enabled():
            return None, "llm-disabled"
        llm_fn = lambda p: _call_live(p)  # noqa: E731
    try:
        raw = llm_fn(prompt)
        return raw.strip(), None
    except Exception as exc:  # noqa: BLE001 — bounded fallback by design
        logger.info("llm call failed: %s", type(exc).__name__)
        return None, f"llm-error:{type(exc).__name__}"


def complete_json(prompt: str, schema: dict, *, llm_fn=None,
                  timeout: int = DEFAULT_TIMEOUT_S) -> tuple[dict | None, str | None]:
    """Ask the LLM for JSON, validate against `schema`, never raise.
    Returns (data, None) on success or (None, reason) on any failure."""
    if llm_fn is None:
        if not is_enabled():
            return None, "llm-disabled"
        llm_fn = lambda p: _call_live(p)  # noqa: E731
    try:
        raw = llm_fn(prompt)
    except Exception as exc:  # noqa: BLE001 — bounded fallback by design
        logger.info("llm call failed: %s", type(exc).__name__)
        return None, f"llm-error:{type(exc).__name__}"
    try:
        data = json.loads(_extract_json(raw))
    except (ValueError, TypeError):
        logger.info("llm reply was not parseable JSON")
        return None, "invalid-json"
    error = validate_schema(data, schema)
    if error:
        logger.info("llm reply failed schema: %s", error)
        return None, error
    return data, None
