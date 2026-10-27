"""xPay core tests — stdlib only (python3 backend/tests/test_core.py).

No pytest, no installs: run directly. The FastAPI layer is exercised via the
orchestrator, which the API wraps 1:1.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from app import config  # noqa: E402
from app.agent import orchestrator  # noqa: E402
from app.services import compliance, gnn_risk, incentive, intent_parser, routing_scorer, store  # noqa: E402


class TestIncentiveMath(unittest.TestCase):
    """The killer feature: True Net Receive incl. the 2.5% BD incentive."""

    def test_stellar_hybrid_best(self):
        b = incentive.calculate_true_net_receive(1000, 32.80, 4.00, route="Stellar Hybrid Anchor → BKASH")
        self.assertEqual(b["gross_bdt"], 32800.00)
        self.assertEqual(b["fees_deducted_bdt"], 131.20)
        self.assertEqual(b["govt_incentive_added_bdt"], 820.00)
        self.assertEqual(b["true_net_receive_bdt"], 33488.80)

    def test_exchange_house_mto(self):
        b = incentive.calculate_true_net_receive(1000, 32.30, 12.00)
        self.assertEqual(b["govt_incentive_added_bdt"], 807.50)
        self.assertEqual(b["true_net_receive_bdt"], 32719.90)

    def test_traditional_swift(self):
        b = incentive.calculate_true_net_receive(1000, 32.40, 24.00)
        self.assertEqual(b["govt_incentive_added_bdt"], 810.00)
        self.assertEqual(b["true_net_receive_bdt"], 32432.40)

    def test_advantage_over_swift(self):
        routes = routing_scorer.score_routes(1000, "BKASH")
        by_name = {r["name"]: r for r in routes}
        delta = (by_name["Stellar Hybrid Anchor → BKASH"]["breakdown"]["true_net_receive_bdt"]
                 - by_name["Traditional SWIFT → BKASH"]["breakdown"]["true_net_receive_bdt"])
        # Both routes carry the AED 2.00 platform fee; the BDT delta shrinks
        # slightly vs the pre-platform-fee 1,056.40 because Swift's worse FX
        # converts the same AED 2.00 into 0.80 BDT more cost.
        self.assertEqual(round(delta, 2), 1055.60)


class TestRoutingScorer(unittest.TestCase):
    def test_ranking_and_flags(self):
        routes = routing_scorer.score_routes(1000, "BKASH")
        self.assertEqual(len(routes), 5)
        evs = [r["expected_value_bdt"] for r in routes]
        self.assertEqual(evs, sorted(evs, reverse=True))
        self.assertTrue(routes[0]["is_best"])
        self.assertEqual(routes[0]["name"], "Stellar Hybrid Anchor → BKASH")
        self.assertEqual(routes[0]["advantage_bdt_vs_best"], 0.0)
        self.assertGreater(routes[-1]["advantage_bdt_vs_best"], 0)

    def test_all_payouts_have_paths(self):
        for payout in ("BKASH", "NAGAD", "BANK"):
            routes = routing_scorer.score_routes(500, payout)
            self.assertEqual(len(routes), 5, payout)


class TestIntentParser(unittest.TestCase):
    def test_default_demo_sentence(self):
        p = intent_parser.parse_intent("Send 1,000 dirhams to my mother's bKash in Dhaka")
        self.assertEqual(p["amount"], 1000.0)
        self.assertEqual(p["source_currency"], "AED")
        self.assertEqual(p["dest_currency"], "BDT")
        self.assertEqual(p["payout_method"], "BKASH")
        self.assertEqual(p["recipient"], "Mother")
        self.assertEqual(p["language_detected"], "en")
        self.assertEqual(p["confidence"], 0.9)

    def test_bengali_numerals_and_words(self):
        p = intent_parser.parse_intent("আমার মায়ের বিকাশে ২ হাজার টাকা পাঠাও")
        self.assertEqual(p["amount"], 2000.0)
        self.assertEqual(p["payout_method"], "BKASH")
        self.assertEqual(p["recipient"], "Mother")
        self.assertEqual(p["language_detected"], "bn")

    def test_missing_fields_get_defaults(self):
        p = intent_parser.parse_intent("send money home")
        self.assertIsNone(p["amount"])
        self.assertEqual(p["source_currency"], "AED")  # corridor default applied
        self.assertIn("currency", p["defaults_applied"])

    def test_nagad_and_bank(self):
        self.assertEqual(intent_parser.parse_intent("send 500 aed to nagad")["payout_method"], "NAGAD")
        self.assertEqual(intent_parser.parse_intent("send 500 aed to my brother's bank")["payout_method"], "BANK")


class TestCompliance(unittest.TestCase):
    def test_clear_party(self):
        result = compliance.screen_party("Ayesha Begum", "recipient")
        self.assertEqual(result["status"], "CLEAR")
        self.assertIsNone(result["best_match"])

    def test_fuzzy_match_review(self):
        result = compliance.screen_party("Nasir Uddin Chowdhury", "recipient")
        self.assertEqual(result["status"], "FUZZY_MATCH_REVIEW")
        self.assertGreaterEqual(result["best_match"]["similarity"], 0.85)
        self.assertEqual(result["best_match"]["name"], "Nasir Uddin Chaudhury")

    def test_exact_hit_blocks(self):
        result = compliance.screen_party("Jahangir Alam", "sender")
        self.assertEqual(result["status"], "BLOCKED")

    def test_pacs008_mapping(self):
        tx = {
            "transaction_id": "tx-20261024-abcdef123456",
            "created_at": "2026-10-24T14:30:05Z",
            "sender_name": "Mohammed Rafiq",
            "recipient_name": "Ayesha Begum",
            "breakdown": {"true_net_receive_bdt": 33488.8, "govt_incentive_added_bdt": 820.0},
        }
        msg = compliance.to_pacs_008(tx)
        self.assertEqual(msg["IntrBkSttlmAmt"]["Ccy"], "BDT")
        # settlement amount = gross - fees = true net MINUS the incentive,
        # which the government pays separately (docs/pacs008-subset.md)
        self.assertEqual(msg["IntrBkSttlmAmt"]["Value"], "32668.80")
        self.assertEqual(msg["GovtIncentiveAmt"]["Value"], "820.00")
        self.assertLessEqual(len(msg["MsgId"]), 16)


class TestGnnRisk(unittest.TestCase):
    def test_default_scenario_low_risk(self):
        f = gnn_risk.demo_features("default", 1000, config.DEMO_SENDER, "Ayesha Begum")
        risk = gnn_risk.pre_settlement_check(f)
        self.assertEqual(risk["risk_band"], "LOW")
        self.assertLess(risk["gnn_risk_score"], 0.1)
        self.assertFalse(risk["requires_manual_review"])
        self.assertEqual(len(risk["graph_nodes_evaluated"]), 4)

    def test_high_risk_scenario_flags_review(self):
        f = gnn_risk.demo_features("high_risk", 5000, config.DEMO_SENDER, "New Person")
        risk = gnn_risk.pre_settlement_check(f)
        self.assertGreaterEqual(risk["gnn_risk_score"], 0.8)
        self.assertTrue(risk["requires_manual_review"])

    def test_pyg_model_defined_or_graceful(self):
        # The production GCN must be importable when PyG is installed; when it
        # is not, the module must degrade to the stand-in without raising.
        self.assertTrue(gnn_risk.PYG_AVAILABLE or gnn_risk.RemittanceGNN is None)


class TestOrchestratorEndToEnd(unittest.TestCase):
    TEXT = "Send 1,000 dirhams to my mother's bKash in Dhaka"

    def test_quote_full_state(self):
        state = orchestrator.run("quote", text=self.TEXT)
        self.assertIsNone(state["error"])
        self.assertEqual(len(state["routes"]), 5)
        self.assertEqual(state["decision"], "CLEAR")
        self.assertIsNone(state["execution"])
        self.assertIn("govt_incentive_added_bdt", state["routes"][0]["breakdown"])
        self.assertGreater(len(state["explanation_log"]), 2)

    def test_execute_happy_path(self):
        state = orchestrator.run("execute", text=self.TEXT)
        self.assertEqual(state["decision"], "CLEAR")
        tx = state["transaction"]
        self.assertEqual(tx["true_net_receive_bdt"], 33423.20)
        self.assertEqual(tx["govt_incentive_2_5_pct"], 820.00)
        self.assertEqual(tx["status"], "COMPLETED")
        self.assertEqual(state["execution"]["network"], "SIMULATED")
        self.assertTrue(state["execution"]["stellar_hash"])
        self.assertIn("iso_20022", tx)

    def test_fuzzy_review_holds_payment(self):
        state = orchestrator.run("execute", text=self.TEXT, demo_scenario="fuzzy_review")
        self.assertEqual(state["decision"], "FUZZY_MATCH_REVIEW")
        self.assertIsNone(state["execution"])
        self.assertEqual(state["transaction"]["status"], "COMPLIANCE_REVIEW")

    def test_high_risk_holds_payment(self):
        state = orchestrator.run("execute", text=self.TEXT, demo_scenario="high_risk",
                                 recipient_name="Totally New Person")
        self.assertEqual(state["decision"], "HIGH_RISK_REVIEW")
        self.assertIsNone(state["execution"])

    def test_unknown_route_rejected(self):
        state = orchestrator.run("execute", text=self.TEXT, selected_route_name="Nope Rail")
        self.assertTrue(state["error"])


class TestStore(unittest.TestCase):
    def test_save_and_get(self):
        tx = {"transaction_id": "test-tx-1", "status": "COMPLETED",
              "created_at": "2026-10-24T00:00:00Z", "true_net_receive_bdt": 33488.8}
        store.save_transaction(tx)
        self.assertEqual(store.get_transaction("test-tx-1")["true_net_receive_bdt"], 33488.8)
        self.assertIsNone(store.get_transaction("missing-tx"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
