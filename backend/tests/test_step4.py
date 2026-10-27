"""Step 4 tests — incentive eligibility as routing logic, EV ranking with the
naive baseline, deadline filtering, multi-hop, sourced data, corridor e2e."""
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.agent import orchestrator  # noqa: E402
from app.services import routing_scorer  # noqa: E402
from app.services.horizon import probe  # noqa: E402


class TestIncentiveEligibility(unittest.TestCase):
    def setUp(self):
        self.routes = routing_scorer.score_routes(1000, "BKASH")

    def test_teaser_rail_gets_no_incentive(self):
        teaser = next(r for r in self.routes if "Cash Pickup" in r["rail"])
        self.assertFalse(teaser["incentive_eligible"])
        self.assertEqual(teaser["breakdown"]["govt_incentive_added_bdt"], 0.0)

    def test_incentive_flag_flips_the_winner(self):
        """On raw pricing (best FX, lowest fee) the teaser rail beats every
        eligible rail — the winner any incentive-blind rate table would crown.
        The 2.5% gate, applied only to eligible rails, is what keeps the
        Stellar rail on top."""
        teaser = next(r for r in self.routes if "Cash Pickup" in r["rail"])
        stellar = next(r for r in self.routes if r["rail"] == "Stellar Hybrid Anchor")
        stellar_net_ex_incentive = (stellar["breakdown"]["true_net_receive_bdt"]
                                    - stellar["breakdown"]["govt_incentive_added_bdt"])
        self.assertGreater(teaser["breakdown"]["true_net_receive_bdt"],
                           stellar_net_ex_incentive,
                           "test setup: teaser must win the incentive-blind comparison")
        self.assertGreater(stellar["breakdown"]["true_net_receive_bdt"],
                           teaser["breakdown"]["true_net_receive_bdt"],
                           "incentive eligibility must flip the ranking")
        self.assertEqual(self.routes[0]["rail"], "Stellar Hybrid Anchor")

    def test_baseline_is_naive_cheapest_fee_and_loses(self):
        baseline = routing_scorer.naive_baseline(self.routes)
        self.assertIn("Cash Pickup", baseline["name"])
        best = self.routes[0]
        self.assertLess(baseline["reliability_adjusted_net"], best["reliability_adjusted_net"])


class TestEVRanking(unittest.TestCase):
    def test_ranked_by_reliability_adjusted_net(self):
        routes = routing_scorer.score_routes(1000, "BKASH")
        evs = [r["reliability_adjusted_net"] for r in routes]
        self.assertEqual(evs, sorted(evs, reverse=True))
        self.assertTrue(routes[0]["is_best"])
        self.assertIn("reliability-adjusted net", routes[0]["ranking_rationale"])

    def test_deadline_filters(self):
        routes = routing_scorer.score_routes(1000, "BKASH", deadline_hours=3)
        self.assertTrue(all(r["settlement_time_hrs"] <= 3 for r in routes))
        with self.assertRaises(ValueError):
            routing_scorer.score_routes(1000, "BKASH", deadline_hours=0.5)

    def test_multi_hop_present(self):
        routes = routing_scorer.score_routes(1000, "BKASH")
        hop = next(r for r in routes if "Multi-hop" in r["rail"])
        self.assertEqual(hop["breakdown"]["hops"], ["AED", "USD", "BDT"])


class TestDataSources(unittest.TestCase):
    def test_horizon_probe_reports_timestamped_truth(self):
        result = probe()
        self.assertIn("reachable", result)
        self.assertTrue(result["checked_at"].endswith("Z"))
        self.assertIn("detail", result)


class TestCorridorEndToEnd(unittest.TestCase):
    """Step 8: a NEW corridor config works end-to-end with zero code changes."""

    def test_ksa_corridor_full_pipeline(self):
        state = orchestrator.run("execute", text="send 1000 sar to my mother's bkash",
                                 corridor="ksa_bd")
        self.assertIsNone(state["error"])
        self.assertEqual(state["decision"], "CLEAR")
        self.assertTrue(state["routes"])
        # Regression: receipts must record the corridor's actual source currency
        # (this used to be hardcoded 'AED', mislabeling SAR transfers).
        self.assertEqual(state["transaction"]["currency_source"], "SAR")

    def test_unknown_corridor_rejected(self):
        state = orchestrator.run("quote", text="send 100 aed", corridor="mars_bd")
        self.assertTrue(state["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
