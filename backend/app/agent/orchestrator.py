"""Layer B — Agentic Orchestrator.

LangGraph state machine over deterministic Layer A tools. The agent never does
math itself: it parses intent, calls the routing scorer, the GNN RegTech and
the compliance gate, then *explains* their outputs in plain language.

Gate rule: `execute` runs only when mode == "execute" AND decision == "CLEAR".
Held or blocked transactions flow straight to the explainer.

If LangGraph isn't installed, an equivalent sequential orchestrator runs the
same node functions — identical behavior, no dependency required.
"""
from typing import TypedDict

from app import config
from app.services import compliance, gnn_risk, intent_parser, quotes, regulatory_rag, routing_scorer, stellar, store
from app.services import corridor as corridor_cfg
from app.services import explainer, llm

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback path
    LANGGRAPH_AVAILABLE = False


class AgentState(TypedDict, total=False):
    mode: str                  # "quote" | "execute"
    corridor: str              # corridor config code, e.g. "uae_bd"
    text: str | None
    llm_used: bool             # LLM fallback contributed to intent parsing
    explanation_en: str        # grounded explanation (number-guarded)
    explanation_bn: str
    explanation_meta: dict
    parsed_intent: dict | None
    amount: float | None
    payout_method: str
    recipient_name: str
    demo_scenario: str
    selected_route_name: str | None
    bound_quote_id: str | None  # caller-supplied: bind execution to this quote
    confirmed: bool | None      # explicit user confirmation of that exact quote
    quote_id: str | None        # this run's quote artifact (fresh or bound)
    quote_expires_at: str | None
    quote_binding: str | None  # "bound" | "fresh_unbound_demo" | None
    settlement_outcome: str    # "COMPLETED" (default) or injected "TIMEOUT"/"FAILED" for the demo
    routes: list
    selected_route: dict | None
    risk: dict | None
    compliance: dict | None
    decision: str
    execution: dict | None
    transaction: dict | None
    explanation_log: list
    error: str | None


# ---------------------------------------------------------------- node funcs
_RELATION_TITLES = {"Mother", "Father", "Wife", "Husband", "Brother", "Sister", "Son", "Daughter"}
FUZZY_DEMO_RECIPIENT = "Nasir Uddin Chowdhury"  # ≈ 'Nasir Uddin Chaudhury' on the sample SDN list


def _resolve_recipient(recipient: str | None, corr: dict | None = None) -> str:
    """Map a relation title ('Mother') or None onto the corridor payout registry."""
    registry = (corr or {}).get("demo_recipients", config.DEMO_RECIPIENTS)
    if recipient and recipient not in _RELATION_TITLES:
        return recipient
    if recipient:
        for name, info in registry.items():
            if info.get("relationship") == recipient:
                return name
    return (corr or {}).get("default_recipient", config.DEFAULT_RECIPIENT_NAME)


def parse_intent_node(state: AgentState) -> dict:
    log = list(state.get("explanation_log", []))
    parsed = None
    llm_used = False
    if state.get("text"):
        parsed = intent_parser.parse_intent(state["text"])
        amount = state.get("amount") or parsed["amount"]
        payout = state.get("payout_method") or parsed["payout_method"]
        recipient = state.get("recipient_name") or parsed["recipient"]

        # Bounded LLM fallback: only when the rule parser found no amount at all,
        # only when an API key is configured, schema-validated, never trusted.
        if parsed["amount"] is None and parsed["payout_method"] is None and llm.is_enabled():
            response, error = llm.complete_json(
                "Extract a remittance intent as strict JSON with keys corridor "
                "(string), amount (number > 0), currency (string, e.g. AED), "
                "recipient (string or null), urgency (\"normal\" or \"urgent\"). "
                f"Transcript: {state['text']}",
                llm.INTENT_SCHEMA,
            )
            if response is not None:
                amount = float(response["amount"])
                if response.get("currency"):
                    parsed["source_currency"] = str(response["currency"]).upper()
                if response.get("recipient") and not recipient:
                    recipient = response["recipient"]
                parsed["llm_fallback"] = True
                llm_used = True
                log.append("Intent parsed by schema-validated LLM fallback "
                           "(deterministic parser found no amount).")
            else:
                log.append("Could not understand the request deterministically and the "
                           "LLM fallback failed — please rephrase.")

        log.append(
            f"Intent parsed: send {amount if amount is not None else '?'} "
            f"{parsed['source_currency']} → {parsed['dest_currency']} via "
            f"{payout or 'default payout'} to '{recipient or 'unnamed recipient'}' "
            f"(confidence {parsed['confidence']:.2f})"
        )
        return {"parsed_intent": parsed, "amount": amount,
                "payout_method": payout, "recipient_name": recipient,
                "llm_used": llm_used, "explanation_log": log}
    return {"parsed_intent": None, "llm_used": False, "explanation_log": log}


def score_routes_node(state: AgentState) -> dict:
    log = list(state.get("explanation_log", []))
    amount = state.get("amount")
    if amount is None:
        amount = config.DEFAULT_AMOUNT
        log.append(f"No amount detected — applying corridor demo default: AED {amount:,.0f}")
    payout = state.get("payout_method") or config.DEFAULT_PAYOUT
    if state.get("payout_method") is None:
        log.append(f"No payout rail detected — defaulting to {payout}")

    routes = routing_scorer.score_routes(amount, payout,
                                         corridor_code=state.get("corridor", corridor_cfg.DEFAULT_CORRIDOR))
    best = routes[0]
    priced = [r for r in routes if r["breakdown"]["true_net_receive_bdt"] is not None]
    worst = priced[-1] if priced else best
    log.append(
        f"Scored {len(routes)} viable corridor paths ({len(routes) - len(priced)} flagged "
        f"ineligible/incomplete); best = {best['name']}: "
        f"True Net Receive {best['breakdown']['true_net_receive_bdt']:,.2f} BDT "
        f"(incl. +{best['breakdown']['govt_incentive_added_bdt']:,.2f} BDT govt incentive) — "
        f"advantage over worst priced: "
        f"{best['breakdown']['true_net_receive_bdt'] - worst['breakdown']['true_net_receive_bdt']:,.2f} BDT"
    )
    selected = best
    if state.get("selected_route_name"):
        match = next((r for r in routes if r["name"] == state["selected_route_name"]), None)
        if match is None:
            return {"routes": routes, "amount": amount, "payout_method": payout,
                    "error": f"Unknown route '{state['selected_route_name']}'",
                    "explanation_log": log}
        selected = match
        log.append(f"User selected route: {selected['name']}")

    # Persist the quote artifact: this is the object the user confirms, and the
    # object execution must later be bound to (ID + TTL + exact numbers).
    corr = corridor_cfg.load_corridor(state.get("corridor", corridor_cfg.DEFAULT_CORRIDOR))
    quote = quotes.create_quote(
        corridor=corr["code"], amount=amount, payout_method=payout, routes=routes,
        selected_route_name=selected["name"], decision=state.get("decision", "PENDING"),
        ttl_minutes=quotes.default_ttl_minutes(corr),
    )
    log.append(f"Quote {quote['quote_id']} issued — valid until {quote['expires_at']} "
               f"(TTL {quote['ttl_minutes']} min). Execution must reference this ID.")
    return {"routes": routes, "amount": amount, "payout_method": payout,
            "selected_route": selected, "quote_id": quote["quote_id"],
            "quote_expires_at": quote["expires_at"], "explanation_log": log}


def _refuse_execute(log: list, code: str, message: str) -> dict:
    log.append(message)
    return {"error": code, "execution": None, "transaction": None,
            "explanation_log": log}


def check_compliance_node(state: AgentState) -> dict:
    log = list(state.get("explanation_log", []))
    amount = state.get("amount") or config.DEFAULT_AMOUNT
    recipient = state.get("recipient_name")
    scenario = state.get("demo_scenario") or "default"
    corr = corridor_cfg.load_corridor(state.get("corridor", corridor_cfg.DEFAULT_CORRIDOR))
    sender = corr.get("demo_sender", config.DEMO_SENDER)

    if recipient and recipient not in _RELATION_TITLES:
        pass  # concrete name from the caller — screen exactly what was given
    elif scenario == "fuzzy_review":
        recipient = FUZZY_DEMO_RECIPIENT
        log.append(
            f"Demo scenario fuzzy_review: screening recipient '{recipient}' "
            f"(near-match case)."
        )
    else:
        recipient = _resolve_recipient(recipient, corr)

    features = gnn_risk.demo_features(scenario, amount, sender, recipient)
    risk = gnn_risk.pre_settlement_check(features, sender_id=sender.get("id", "demo_sender"),
                                         corridor=corr.get("geo_code", "AE->BD"))
    screening = compliance.screen_transaction(sender["name"], recipient,
                                              entries=corridor_cfg.load_sanctions(corr["code"]))
    log.append(
        f"Predictive RegTech: GNN risk {risk['gnn_risk_score']:.2f} ({risk['risk_band']}) — "
        f"{risk['ai_explanation']}"
    )
    if screening["ofac_match_status"] == "CLEAR":
        log.append("Compliance gate: OFAC CLEAR for all parties.")
    else:
        flagged = next(p for p in screening["screened_parties"] if p["status"] != "CLEAR")
        match = flagged["best_match"]
        log.append(
            f"Compliance gate: {flagged['status']} on {flagged['role']} "
            f"'{flagged['name']}' — {match['similarity']:.0%} similar to list entry "
            f"'{match['name']}'. Payment held for human review; no silent rejection."
        )

    if screening["ofac_match_status"] == "BLOCKED":
        decision = "BLOCKED"
    elif screening["ofac_match_status"] == "FUZZY_MATCH_REVIEW":
        decision = "FUZZY_MATCH_REVIEW"
    elif risk["requires_manual_review"]:
        decision = "HIGH_RISK_REVIEW"
    else:
        decision = "CLEAR"

    # Ground the decision in the regulatory corpus (citations only, no generation)
    if decision in ("FUZZY_MATCH_REVIEW", "BLOCKED"):
        rag_query = "OFAC sanctions screening fuzzy name matching potential match hold review"
    elif decision == "HIGH_RISK_REVIEW":
        rag_query = "sanctions screening risk-based approach transaction monitoring review"
    else:
        rag_query = ("remittance cash incentive 2.5% formal channel government payout "
                     "exchange rate application taka")
    risk["regulatory_basis"] = regulatory_rag.retrieve(rag_query)["passages"]

    return {"risk": risk, "compliance": screening, "recipient_name": recipient,
            "decision": decision, "explanation_log": log}


def execute_node(state: AgentState) -> dict:
    log = list(state.get("explanation_log", []))
    amount = state.get("amount") or config.DEFAULT_AMOUNT

    # ---- Quote binding gate (skippable only by the unbound demo path) --------
    quote_binding = "fresh_unbound_demo"
    route = state.get("selected_route") or {}
    receipt_quote_id = state.get("quote_id")  # fresh quote scored this run
    if state.get("bound_quote_id"):
        if not state.get("confirmed"):
            return _refuse_execute(
                log, "confirmation_required",
                "Execution refused: a bound quote requires explicit "
                "confirmation (confirmed=true) of the exact quoted amount and route.")
        quote, err = quotes.revalidate(
            state["bound_quote_id"], selected_route_name=state.get("selected_route_name"),
            amount=amount, payout_method=state.get("payout_method"))
        if err == "quote_expired":
            return _refuse_execute(
                log, "quote_expired",
                f"Execution refused: quote {state['bound_quote_id']} EXPIRED — "
                "stale pricing can never settle. Request a fresh quote.")
        if err:
            return _refuse_execute(
                log, err, f"Execution refused: quote revalidation failed ({err}).")
        # Bind the receipt to the exact numbers the user saw in that quote.
        bound_name = state.get("selected_route_name") or quote["selected_route_name"]
        bound_route = next((r for r in quote["routes"] if r["name"] == bound_name), None)
        if bound_route is None:
            return _refuse_execute(
                log, "route_not_in_quote",
                "Execution refused: selected route missing from the quoted set.")
        route = bound_route
        quote_binding = "bound"
        receipt_quote_id = quote["quote_id"]
        quotes.consume_quote(quote["quote_id"])
        log.append(f"Bound to confirmed quote {quote['quote_id']} "
                   f"(expires {quote['expires_at']}); receipt uses the quoted numbers verbatim.")
    else:
        log.append("No bound quote supplied — running the unbound DEMO path: numbers "
                   f"come from quote {receipt_quote_id} scored moments ago. B2B callers "
                   "must bind and confirm a quote_id; this path exists so the demo runs "
                   "without pre-quote state.")

    breakdown = route.get("breakdown", {})

    # A route with unknown fees cannot settle: refusing is the only honest move.
    if breakdown.get("true_net_receive_bdt") is None or route.get("pricing_completeness") == "incomplete":
        return _refuse_execute(
            log, "incomplete_pricing",
            f"Execution refused: route '{route.get('name')}' has incomplete pricing "
            "(missing fee data) — it can be displayed as flagged but never settled.")

    execution = stellar.simulate_settlement(route.get("name", ""), amount,
                                            outcome=state.get("settlement_outcome", "COMPLETED"))
    if execution["status"] == "COMPLETED":
        log.append(f"Execution: route {route.get('name')} settled via SIMULATED hash "
                   f"(labeled; no testnet credentials configured — see REAL_VS_SIMULATED.md).")
    else:
        log.append(f"Execution: route {route.get('name')} settlement returned "
                   f"{execution['status']} — status is UNCERTAIN. NOT reporting success; "
                   f"transaction parked for reconciliation. (Simulated outcome, labeled.)")

    corr = corridor_cfg.load_corridor(state.get("corridor", corridor_cfg.DEFAULT_CORRIDOR))
    sender = corr.get("demo_sender", config.DEMO_SENDER)
    recipient = state.get("recipient_name") or corr.get("default_recipient", config.DEFAULT_RECIPIENT_NAME)
    registry = corr.get("demo_recipients", config.DEMO_RECIPIENTS).get(recipient, {})
    import datetime as _dt
    settled = execution["status"] == "COMPLETED"
    tx = {
        "transaction_id": _dt.datetime.now(_dt.timezone.utc).strftime("tx-%Y%m%d-") + uuid4_short(),
        "sender_id": sender.get("id", "demo_sender"),
        "sender_name": sender["name"],
        "recipient_name": recipient,
        "recipient_handle": registry.get("handle", f"unsaved recipient ({state.get('payout_method', 'BKASH')})"),
        "amount_source": float(amount),
        "currency_source": corr["source_currency"],
        "fx_rate_applied": route.get("fx_rate"),
        "fee_deducted_source": breakdown.get("fee_source"),
        "govt_incentive_2_5_pct": breakdown.get("govt_incentive_added_bdt"),
        "true_net_receive_bdt": breakdown.get("true_net_receive_bdt"),
        "route_selected": route.get("name"),
        "quote_id": receipt_quote_id,
        "quote_binding": quote_binding,
        "stellar_hash": execution.get("stellar_hash"),
        "status": "COMPLETED" if settled else "RECONCILIATION_REQUIRED",
        "created_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "breakdown": breakdown,
    }
    # Legacy display key: only truthful when the source currency really is AED.
    if corr["source_currency"] == "AED":
        tx["fee_deducted_aed"] = breakdown.get("fee_source")
    if not settled:
        tx["reconciliation_required"] = True
        tx["execution_status"] = execution["status"]
    tx["iso_20022"] = compliance.to_pacs_008(tx)
    store.save_transaction(tx)
    if settled:
        fee_val = tx["fee_deducted_source"] or 0
        log.append(
            f"Receipt: recipient gets {tx['true_net_receive_bdt']:,.2f} BDT "
            f"(gross {tx['breakdown'].get('gross_bdt', 0):,.2f} − fees "
            f"{fee_val:,.2f} {tx['currency_source']} + incentive "
            f"{tx['govt_incentive_2_5_pct'] or 0:,.2f} BDT). Hash {tx['stellar_hash'][:16]}…")
    else:
        log.append("Receipt: no settlement confirmation — no success claim, no hash. "
                   "Reconcile the transfer before any payout is reported.")
    return {"execution": execution, "transaction": tx, "quote_binding": quote_binding,
            "explanation_log": log}


def record_hold_node(state: AgentState) -> dict:
    """Execute mode + held/blocked: persist an audit record, move no money."""
    if state.get("mode") != "execute" or state.get("decision") == "CLEAR":
        return {}
    route = state.get("selected_route") or {}
    corr = corridor_cfg.load_corridor(state.get("corridor", corridor_cfg.DEFAULT_CORRIDOR))
    recipient = state.get("recipient_name") or corr.get("default_recipient", config.DEFAULT_RECIPIENT_NAME)
    registry = corr.get("demo_recipients", config.DEMO_RECIPIENTS).get(recipient, {})
    import datetime as _dt
    tx = {
        "transaction_id": _dt.datetime.now(_dt.timezone.utc).strftime("tx-%Y%m%d-") + uuid4_short(),
        "sender_id": corr.get("demo_sender", config.DEMO_SENDER)["id"],
        "sender_name": corr.get("demo_sender", config.DEMO_SENDER)["name"],
        "recipient_name": recipient,
        "recipient_handle": registry.get("handle", f"unsaved recipient ({state.get('payout_method', 'BKASH')})"),
        "amount_source": state.get("amount") or config.DEFAULT_AMOUNT,
        "currency_source": corr["source_currency"],
        "fx_rate_applied": route.get("fx_rate"),
        "fee_deducted_source": (route.get("breakdown") or {}).get("fee_source"),
        "govt_incentive_2_5_pct": (route.get("breakdown") or {}).get("govt_incentive_added_bdt"),
        "true_net_receive_bdt": (route.get("breakdown") or {}).get("true_net_receive_bdt"),
        "route_selected": route.get("name"),
        "stellar_hash": None,
        "status": "BLOCKED" if state.get("decision") == "BLOCKED" else "COMPLIANCE_REVIEW",
        "created_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "breakdown": route.get("breakdown", {}),
        "hold_reason": state.get("decision"),
    }
    store.save_transaction(tx)
    return {"transaction": tx}


def explain_decision_node(state: AgentState) -> dict:
    log = list(state.get("explanation_log", []))
    decision = state.get("decision", "CLEAR")
    if state.get("error"):
        log.append(f"Flow stopped: {state['error']}")
    elif decision == "CLEAR":
        log.append("Decision: CLEAR — all engines passed. Funds released to the selected rail.")
    elif decision == "BLOCKED":
        log.append("Decision: BLOCKED — hard sanctions match. Transaction refused and logged.")
    elif decision == "FUZZY_MATCH_REVIEW":
        log.append("Decision: payment HELD — near-match to a sanctions entry needs human sign-off.")
    elif decision == "HIGH_RISK_REVIEW":
        log.append("Decision: payment HELD — GNN risk above threshold needs human sign-off.")
    elif state.get("transaction", {}) and state["transaction"].get("status") == "RECONCILIATION_REQUIRED":
        log.append("Decision: settlement outcome UNCERTAIN — no success is reported; "
                   "the transaction waits in reconciliation with a full audit record.")

    explanations = explainer.build_explanations(
        state, llm_fn=(lambda p: llm.complete_text(p)[0]) if llm.is_enabled() else None
    )
    log.append("Explanation generated from the decision log; every number is "
               "ground-checked against the quote.")
    return {"explanation_log": log, "explanation_en": explanations["en"],
            "explanation_bn": explanations["bn"], "explanation_meta": {
                "grounded": explanations["grounded"],
                "llm_paraphrased": explanations["llm_paraphrased"],
            }}


def uuid4_short() -> str:
    import uuid as _uuid

    return _uuid.uuid4().hex[:12]


def _should_execute(state: AgentState) -> str:
    if state.get("mode") != "execute" or state.get("error"):
        return "explain"
    if state.get("decision") == "CLEAR":
        return "execute"
    return "record_hold"


# ---------------------------------------------------------------- runners
def _run_sequential(state: AgentState) -> AgentState:
    state = {**state, **parse_intent_node(state)}
    state = {**state, **score_routes_node(state)}
    state = {**state, **check_compliance_node(state)}
    branch = _should_execute(state)
    if branch == "execute":
        state = {**state, **execute_node(state)}
    elif branch == "record_hold":
        state = {**state, **record_hold_node(state)}
    state = {**state, **explain_decision_node(state)}
    return state


def _build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("score_routes", score_routes_node)
    workflow.add_node("check_compliance", check_compliance_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("record_hold", record_hold_node)
    workflow.add_node("explain_decision", explain_decision_node)
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "score_routes")
    workflow.add_edge("score_routes", "check_compliance")
    workflow.add_conditional_edges(
        "check_compliance", _should_execute,
        {"execute": "execute", "record_hold": "record_hold", "explain": "explain_decision"},
    )
    workflow.add_edge("execute", "explain_decision")
    workflow.add_edge("record_hold", "explain_decision")
    workflow.add_edge("explain_decision", END)
    return workflow.compile()


_COMPILED = _build_graph() if LANGGRAPH_AVAILABLE else None


def run(mode: str, *, text: str | None = None, amount: float | None = None,
        payout_method: str | None = None, selected_route_name: str | None = None,
        recipient_name: str | None = None, demo_scenario: str = "default",
        corridor: str = corridor_cfg.DEFAULT_CORRIDOR,
        bound_quote_id: str | None = None, confirmed: bool | None = None,
        settlement_outcome: str = "COMPLETED") -> AgentState:
    """Run the full agent. mode: 'quote' (no money moves) or 'execute'.

    Execution safety: pass `bound_quote_id` (the quote_id from a previous
    quote response) with `confirmed=True` to bind execution to the exact
    quote the user saw — expired/mismatched/unconfirmed quotes are refused.
    Without it the unbound demo path runs (fresh numbers, labeled as such)."""
    state: AgentState = {
        "mode": mode, "corridor": corridor, "text": text, "amount": amount,
        "payout_method": payout_method, "recipient_name": recipient_name,
        "selected_route_name": selected_route_name, "demo_scenario": demo_scenario,
        "bound_quote_id": bound_quote_id, "confirmed": confirmed,
        "settlement_outcome": settlement_outcome,
        "explanation_log": [], "decision": "PENDING", "error": None,
        "parsed_intent": None, "routes": [], "selected_route": None,
        "risk": None, "compliance": None, "execution": None, "transaction": None,
    }
    if _COMPILED is not None:
        try:
            return _COMPILED.invoke(state)
        except ValueError as exc:  # corridor/config errors → surfaced, not raised
            return {**state, "error": str(exc), "decision": "ERROR"}
    try:
        return _run_sequential(state)
    except ValueError as exc:
        return {**state, "error": str(exc), "decision": "ERROR"}
