"""Smoke test — Step 0 gate. Run with the stdlib interpreter OR a fresh venv:

    python3 backend/tests/test_smoke.py                 # bare python: skips FastAPI layer
    make smoke                                          # fresh venv + requirements-lite + this test

Every module in the package must import; the default pipeline must run end-to-end
and produce the locked demo numbers (AED 1,000 -> bKash = 33,488.80 BDT).
"""
import importlib
import pkgutil
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


class TestImports(unittest.TestCase):
    def test_every_service_module_imports(self):
        import app.services as services

        names = [m.name for m in pkgutil.iter_modules(services.__path__)]
        self.assertIn("routing_scorer", names, "routing_scorer.py missing from services")
        for name in names:
            importlib.import_module(f"app.services.{name}")
        self.assertGreaterEqual(len(names), 11, f"expected >=11 service modules, got {names}")

    def test_agent_and_config_import(self):
        for mod in ("app.agent.orchestrator", "app.config", "app.services.corridor"):
            importlib.import_module(mod)

    def test_fastapi_layer_imports(self):
        try:
            importlib.import_module("app.main")
        except ImportError as exc:
            self.skipTest(f"FastAPI layer not installed in this interpreter (fine on bare python): {exc}")


class TestDefaultPipeline(unittest.TestCase):
    def test_end_to_end_default_scenario(self):
        from app.agent import orchestrator

        state = orchestrator.run("execute", text="Send 1,000 dirhams to my mother's bKash in Dhaka")
        self.assertEqual(state["decision"], "CLEAR")
        tx = state["transaction"]
        self.assertEqual(tx["true_net_receive_bdt"], 33488.80)
        self.assertEqual(tx["govt_incentive_2_5_pct"], 820.00)
        self.assertEqual(tx["status"], "COMPLETED")
        self.assertEqual(state["execution"]["network"], "SIMULATED")
        self.assertTrue(state["risk"].get("regulatory_basis") is not None)

    def test_held_payment_moves_no_money(self):
        from app.agent import orchestrator

        state = orchestrator.run("execute", text="Send 1,000 dirhams to my mother's bKash",
                                 demo_scenario="fuzzy_review")
        self.assertEqual(state["decision"], "FUZZY_MATCH_REVIEW")
        self.assertIsNone(state["execution"], "held payment must not produce an execution")
        self.assertEqual(state["transaction"]["status"], "COMPLIANCE_REVIEW")
        self.assertIsNone(state["transaction"]["stellar_hash"], "held payment must have no ledger hash")


if __name__ == "__main__":
    unittest.main(verbosity=2)
