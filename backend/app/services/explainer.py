"""Grounded explanation generator (Step 3) — Bangla + English.

The explanation is composed from the orchestrator state (the decision log).
When an LLM is configured it may *paraphrase*, but a post-check rejects any
paraphrase containing a number that does not appear in the state — the
hallucination guard. Without an LLM the template itself is grounded by
construction (its only numbers are interpolated from state values).
"""
import re

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _canon(num: str) -> str:
    """Canonicalize a number string: '33,488.80' and '33488.80' and '33488.8' match."""
    value = float(num.replace(",", ""))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def allowed_numbers(state: dict) -> set[str]:
    """Every number the explanation is permitted to contain, derived from state."""
    allowed = set()
    tx = state.get("transaction") or {}
    best = state.get("selected_route")
    if isinstance(best, dict):
        best = [best]
    best = (best or state.get("routes") or [{}])[0] or {}
    breakdown = best.get("breakdown") or {}
    for value in (
        state.get("amount"), tx.get("amount_source"), breakdown.get("amount_source"),
        breakdown.get("fx_rate"), breakdown.get("fee_source"),
        breakdown.get("gross_bdt"), breakdown.get("fees_deducted_bdt"),
        breakdown.get("govt_incentive_added_bdt"), breakdown.get("true_net_receive_bdt"),
        tx.get("true_net_receive_bdt"), tx.get("govt_incentive_2_5_pct"),
        breakdown.get("settlement_time_hrs"),
    ):
        if value is not None:
            allowed.add(_canon(str(value)))
    allowed.add(_canon("2.5"))  # the incentive rate, quoted as a percent
    return allowed


def numbers_violation(text: str, allowed: set[str]) -> list[str]:
    return [n for n in _NUM_RE.findall(text) if _canon(n) not in allowed]


def _route_of(state: dict) -> dict:
    best = state.get("selected_route")
    if isinstance(best, dict):
        return best
    routes = state.get("routes") or [{}]
    return routes[0] or {}


def _money(value, suffix: str) -> str:
    """Render a money figure; unknown pricing renders as unknown — never 0.00,
    which would silently assert a fee-free transfer."""
    return f"— {suffix}" if value is None else f"{value:,.2f} {suffix}"


def _template_en(state: dict) -> str:
    decision = state.get("decision", "PENDING")
    if decision == "CLEAR":
        b = _route_of(state).get("breakdown", {})
        return (f"Routed via {_route_of(state).get('rail', 'the best rail')}: they receive "
                f"{_money(b.get('true_net_receive_bdt'), 'BDT')} — fees "
                f"{_money(b.get('fees_deducted_bdt'), 'BDT')} deducted and the "
                f"{2.5}% government incentive of "
                f"{_money(b.get('govt_incentive_added_bdt'), 'BDT')} added, arriving in about "
                f"{b.get('settlement_time_hrs', 2)} hours.")
    if decision in ("FUZZY_MATCH_REVIEW", "BLOCKED", "HIGH_RISK_REVIEW"):
        return ("We need to verify this transfer before any money moves. No funds "
                "have left your account; an analyst will review the flagged signal.")
    return "Quote generated. Nothing has been sent yet."


def _template_bn(state: dict) -> str:
    decision = state.get("decision", "PENDING")
    if decision == "CLEAR":
        b = _route_of(state).get("breakdown", {})
        rail = _route_of(state).get("rail", "সেরা রুট")
        return (f"{rail} দিয়ে পাঠানো হবে: প্রাপক পাবেন "
                f"{_money(b.get('true_net_receive_bdt'), 'টাকা')} — ফি "
                f"{_money(b.get('fees_deducted_bdt'), 'টাকা')} বাদ, সরকারি "
                f"{2.5}% প্রণোদনা {_money(b.get('govt_incentive_added_bdt'), 'টাকা')} যোগ, "
                f"প্রায় {b.get('settlement_time_hrs', 2)} ঘণ্টায় পৌঁছাবে।")
    if decision in ("FUZZY_MATCH_REVIEW", "BLOCKED", "HIGH_RISK_REVIEW"):
        return ("এই লেনদেনটি পাঠানোর আগে যাচাই করতে হবে। আপনার কোনো টাকা যায়নি; "
                "একজন কর্মকর্তা চিহ্নিত ঝুঁকিটি পর্যালোচনা করবেন।")
    return "কোটেশন তৈরি হয়েছে। এখনো কিছু পাঠানো হয়নি।"


def build_explanations(state: dict, llm_fn=None) -> dict:
    """Returns {en, bn, grounded, llm_paraphrased}. Both languages always present;
    the number guard runs on any LLM paraphrase and rejects it on violation."""
    allowed = allowed_numbers(state)
    result = {"en": _template_en(state), "bn": _template_bn(state),
              "grounded": True, "llm_paraphrased": False}
    if llm_fn is not None:
        prompt = (
            "Paraphrase this remittance explanation in one warm, simple sentence. "
            "STRICT RULE: you must not introduce, change, or round any number — "
            f"only numbers from the original may appear. EN: {result['en']}"
        )
        paraphrased, error = llm_complete(prompt, llm_fn)
        if paraphrased and not numbers_violation(paraphrased, allowed):
            result["en"], result["llm_paraphrased"] = paraphrased, True
        elif paraphrased:
            result["grounded"] = False  # kept the template; the paraphrase failed the guard
    return result


def llm_complete(prompt: str, llm_fn) -> tuple[str | None, str | None]:
    from app.services import llm

    return llm.complete_text(prompt, llm_fn=llm_fn)
