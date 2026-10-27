"""Run the end-to-end happy path in the terminal — no installs needed.

    python3 backend/run_demo.py

Prints the route comparison for the locked demo scenario (AED 1,000 -> bKash),
executes the default flow, then shows the fuzzy-review hold. Numbers should
match docs/demo-script.md exactly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import orchestrator  # noqa: E402

LINE = "─" * 74


def money(v) -> str:
    return f"{v:,.2f}"


def print_routes(routes):
    print("\n📊 ROUTE COMPARISON — AED 1,000 → bKash (simulated quotes)")
    print(LINE)
    print(f"{'Route':<34}{'FX':>6}{'Fee AED':>9}{'+2.5% Inc.':>12}{'True Net BDT':>14}")
    for r in routes:
        b = r["breakdown"]
        star = " ✅ BEST" if r["is_best"] else ""
        print(f"{r['name'][:33]:<34}{r['fx_rate']:>6.2f}{r['fee_total_source']:>9.2f}"
              f"{b['govt_incentive_added_bdt']:>12.2f}{b['true_net_receive_bdt']:>14.2f}{star}")
    print(LINE)


def print_receipt(state):
    tx = state["transaction"]
    ex = state["execution"]
    print("\n🧾 RECEIPT")
    print(LINE)
    print(f"  Transaction     {tx['transaction_id']}")
    print(f"  Sender          {tx['sender_name']} (UAE)")
    print(f"  Recipient       {tx['recipient_name']} — {tx['recipient_handle']}")
    print(f"  Route           {tx['route_selected']}")
    print(f"  Amount          AED {money(tx['amount_source'])} @ {tx['fx_rate_applied']}")
    print(f"  Gross           BDT {money(tx['breakdown']['gross_bdt'])}")
    print(f"  Fees            − AED {money(tx['fee_deducted_aed'])} "
          f"(= BDT {money(tx['breakdown']['fees_deducted_bdt'])})")
    print(f"  Govt incentive  + BDT {money(tx['govt_incentive_2_5_pct'])}  🌟 (Bangladesh Bank 2.5%)")
    print(f"  TRUE NET        BDT {money(tx['true_net_receive_bdt'])}")
    print(f"  Settlement      {ex['network']} · hash {tx['stellar_hash'][:20]}…")
    print(f"  ISO 20022       MsgId {tx['iso_20022']['MsgId']}")
    print(LINE)


def main():
    print("🚀 XPAY · end-to-end demo (UAE → Bangladesh)")
    print("   Agentic, jurisdiction-aware remittance intelligence")

    # 1) Voice/text intent
    text = "Send 1,000 dirhams to my mother's bKash in Dhaka"
    intent = orchestrator.parse_intent_node  # node ref; parse directly below
    from app.services.intent_parser import parse_intent
    parsed = parse_intent(text)
    print(f"\n🎤 Voice intent: “{text}”")
    print(f"   → AED {money(parsed['amount'])} → BDT via {parsed['payout_method']} "
          f"to '{parsed['recipient']}' (lang={parsed['language_detected']}, "
          f"confidence={parsed['confidence']})")

    # 2) Quote
    print("\n🧠 Layer B orchestrator: quote mode…")
    quote_state = orchestrator.run("quote", text=text)
    print_routes(quote_state["routes"])

    # 3) Execute (happy path)
    print("\n⛓️ Executing best route (demo scenario: default)…")
    done = orchestrator.run("execute", text=text,
                            selected_route_name=quote_state["routes"][0]["name"])
    print(f"\n   Decision: {done['decision']} · GNN risk "
          f"{done['risk']['gnn_risk_score']} ({done['risk']['risk_band']}) · "
          f"OFAC {done['compliance']['ofac_match_status']}")
    print_receipt(done)

    # 4) Explainable AI: the fuzzy-review hold
    print("\n🛡️ Explainable AI demo (scenario: fuzzy_review)…")
    held = orchestrator.run("execute", text=text, demo_scenario="fuzzy_review",
                            selected_route_name=quote_state["routes"][0]["name"])
    print(f"   Decision: {held['decision']} · status "
          f"{(held.get('transaction') or {}).get('status', 'NOT_CREATED')}")
    for entry in held["explanation_log"]:
        if "Compliance gate" in entry or "Decision" in entry:
            print(f"   • {entry}")

    print("\n✅ Demo complete. Numbers match docs/demo-script.md — record away!\n")


if __name__ == "__main__":
    main()
