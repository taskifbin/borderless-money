"""Financial-correctness tests — exact decimal math, eligibility, quote lifecycle.

Stdlib only (python3 backend/tests/test_financial.py). Complements test_core:
these target the edge cases and invariants that make net-receive numbers
trustworthy — missing data, expiry, binding, rounding boundaries, ranking.
"""
import random
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import config  # noqa: E402
from app.agent import orchestrator  # noqa: E402
from app.services import corridor as corridor_cfg  # noqa: E402
from app.services import incentive, quotes, routing_scorer, store  # noqa: E402
from app.services.money import D, MoneyValueError, quantize  # noqa: E402

TEXT = "Send 1,000 dirhams to my mother's bKash in Dhaka"


class TestMoneyPrimitives(unittest.TestCase):
    def test_float_conversion_uses_shortest_round_trip_repr(self):
        self.assertEqual(D(32.8), Decimal("32.8"))
        self.assertEqual(D(0.1), Decimal("0.1"))

    def test_exact_decimal_arithmetic_no_binary_drift(self):
        gross = D("0.1") + D("0.2")
        self.assertEqual(str(gross), "0.3")

    def test_rejects_nan_inf_and_garbage(self):
        for bad in (float("nan"), float("inf"), "abc", "1,000", True, None, {"a": 1}):
            with self.assertRaises(MoneyValueError, msg=repr(bad)):
                D(bad)

    def test_string_amounts_parse(self):
        self.assertEqual(D(" 12.50 "), Decimal("12.50"))

    def test_quantize_half_up_boundaries(self):
        self.assertEqual(quantize(D("2.005"), "BDT"), Decimal("2.01"))
        self.assertEqual(quantize(D("2.004"), "BDT"), Decimal("2.00"))
        self.assertEqual(quantize(D("-2.005"), "BDT"), Decimal("-2.01"))
        self.assertEqual(quantize(D("1.5"), "JPY"), Decimal("2"))  # 0-minor-unit ccy
        self.assertEqual(quantize(D("1.2349"), "KWD"), Decimal("1.235"))  # 3dp ccy


class TestTrueNetReceiveExact(unittest.TestCase):
    def test_reference_value_matches_documented_example(self):
        b = incentive.calculate_true_net_receive(1000, 32.80, 4.00)
        self.assertEqual(b["true_net_receive_exact"], "33488.80")
        self.assertEqual(b["true_net_receive_bdt"], 33488.80)
        self.assertEqual(b["pricing_completeness"], "complete")

    def test_rounding_boundary_is_half_up_not_bankers(self):
        # 1000 x 0.0325 x ... construct: principal 1, rate 0.3255 => gross 0.3255 -> 0.33
        b = incentive.calculate_true_net_receive(1, 0.3255, 0.0, govt_incentive_rate=0.0)
        self.assertEqual(b["gross_bdt"], 0.33)

    def test_fee_in_destination_currency_skips_conversion(self):
        src = incentive.calculate_true_net_receive(1000, 32.80, 100.0, fee_currency="DEST")
        self.assertEqual(src["fees_deducted_bdt"], 100.00)

    def test_fee_in_source_currency_is_converted(self):
        src = incentive.calculate_true_net_receive(1000, 32.80, 4.00, fee_currency="SOURCE")
        self.assertEqual(src["fees_deducted_bdt"], 131.20)

    def test_missing_fee_is_flagged_never_zeroed(self):
        b = incentive.calculate_true_net_receive(1000, 32.80, None)
        self.assertIsNone(b["true_net_receive_bdt"])
        self.assertIsNone(b["fee_source"])
        self.assertEqual(b["pricing_completeness"], "incomplete")
        self.assertIn("fee_source", b["missing_fields"])
        self.assertIn("NOT assumed to be zero", b["data_quality_note"])

    def test_zero_and_negative_principal_rejected(self):
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(0, 32.8, 4.0)
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(-50, 32.8, 4.0)

    def test_non_positive_fx_rejected(self):
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(100, 0, 4.0)
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(100, -32.8, 4.0)

    def test_nan_amount_rejected(self):
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(float("nan"), 32.8, 4.0)

    def test_negative_fee_rejected(self):
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(1000, 32.8, -4.0)

    def test_incentive_rate_validated(self):
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(1000, 32.8, 4.0, govt_incentive_rate=1.5)
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive(1000, 32.8, 4.0, govt_incentive_rate=-0.1)

    def test_incentive_applied_exactly_once(self):
        """Duplicate-incentive guard: the engine takes a single rate argument
        and applies it once — a caller cannot stack it by re-invoking."""
        once = incentive.calculate_true_net_receive(1000, 32.80, 4.0, govt_incentive_rate=0.025)
        explicit = incentive.calculate_true_net_receive(1000, 32.80, 4.0, govt_incentive_rate=None)
        self.assertEqual(once["govt_incentive_added_bdt"], explicit["govt_incentive_added_bdt"])

    def test_zero_rate_disables_incentive(self):
        b = incentive.calculate_true_net_receive(1000, 32.80, 4.0, govt_incentive_rate=0.0)
        self.assertEqual(b["govt_incentive_added_bdt"], 0.0)
        self.assertEqual(b["true_net_receive_bdt"], 32668.80)

    def test_very_large_but_valid_amount(self):
        # 1e9 x 32.80 = 32,800,000,000; fee 4 x 32.80 = 131.20;
        # incentive 2.5% = 820,000,000 → net = 33,619,999,868.80
        b = incentive.calculate_true_net_receive(1_000_000_000, 32.80, 4.0)
        self.assertEqual(b["true_net_receive_exact"], "33619999868.80")

    def test_reproducible_same_inputs_same_outputs(self):
        a = incentive.calculate_true_net_receive(7331.37, 32.8123, 4.97)
        b = incentive.calculate_true_net_receive(7331.37, 32.8123, 4.97)
        self.assertEqual(a, b)


class TestEligibilityAndRanking(unittest.TestCase):
    def test_missing_fee_data_route_cannot_win(self):
        corr = corridor_cfg.load_corridor()
        patched = {**corr, "rails": [
            {**corr["rails"][1], "fee_source": None},  # Stellar Hybrid, no pricing
            *corr["rails"][2:],
        ]}
        routes = self._score_with(patched, 1000)
        broken = next(r for r in routes if "Stellar Hybrid" in r["rail"])
        self.assertFalse(broken["eligibility"]["eligible"])
        self.assertEqual(broken["eligibility"]["reason"], "missing_fee_data")
        self.assertIsNone(broken["expected_value_bdt"])
        self.assertFalse(broken["is_best"], "an unpriced route must never win")

    def test_ineligible_or_unpriced_never_wins_property(self):
        """Invariant: the winner is the max-EV route among ELIGIBLE candidates.
        Swept over seeded random amounts (property-style, stdlib only)."""
        rng = random.Random(42)
        for _ in range(200):
            amount = round(rng.uniform(1, 100_000), 2)
            routes = routing_scorer.score_routes(amount, "BKASH")
            best = routes[0]
            eligible = [r for r in routes if r["eligibility"]["eligible"]]
            self.assertTrue(eligible)
            self.assertTrue(best["eligibility"]["eligible"], amount)
            self.assertEqual(
                Decimal(best["expected_value_exact"]),
                max(Decimal(r["expected_value_exact"]) for r in eligible),
                f"amount={amount}: winner must be the max-EV eligible route")

    def test_identical_candidates_keep_stable_config_order(self):
        corr = corridor_cfg.load_corridor()
        twin = dict(corr["rails"][1])  # Stellar Hybrid Anchor
        routes = self._score_with({**corr, "rails": [corr["rails"][1], twin, *corr["rails"][2:]]}, 1000)
        names = [r["name"] for r in routes]
        self.assertEqual(names[0], names[1])  # same rail name twice, original order
        self.assertEqual(routes[0]["breakdown"]["true_net_receive_bdt"],
                         routes[1]["breakdown"]["true_net_receive_bdt"])

    def test_malformed_rail_fx_is_surfaced_not_swallowed(self):
        corr = corridor_cfg.load_corridor()
        patched = {**corr, "rails": [{**corr["rails"][0], "fx": "not-a-number"}]}
        with self.assertRaises(ValueError):
            self._score_with(patched, 1000)

    def _score_with(self, patched_cfg, amount):
        original_dir = corridor_cfg.CORRIDOR_DIR
        corridor_cfg.load_corridor.cache_clear()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                corridor_cfg.CORRIDOR_DIR = Path(tmp)
                import json
                Path(tmp, "uae_bd.json").write_text(json.dumps(patched_cfg))
                return routing_scorer.score_routes(amount, "BKASH")
        finally:
            corridor_cfg.CORRIDOR_DIR = original_dir
            corridor_cfg.load_corridor.cache_clear()


class TestQuoteLifecycle(unittest.TestCase):
    def test_quote_has_id_and_ttl(self):
        q = quotes.create_quote(corridor="uae_bd", amount=1000, payout_method="BKASH",
                                routes=routing_scorer.score_routes(1000, "BKASH"),
                                selected_route_name=None, decision="PENDING")
        self.assertTrue(q["quote_id"].startswith("q_"))
        self.assertEqual(q["status"], "ACTIVE")
        created = datetime.strptime(q["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(q["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(expires - created, timedelta(minutes=60))

    def test_revalidate_happy_path(self):
        q = self._make_quote()
        got, err = quotes.revalidate(q["quote_id"], amount=1000)
        self.assertIsNone(err)
        self.assertEqual(got["quote_id"], q["quote_id"])

    def test_revalidate_expired_quote(self):
        q = self._make_quote()
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        store.save_quote({**q, "expires_at": past})
        got, err = quotes.revalidate(q["quote_id"], amount=1000)
        self.assertEqual(err, "quote_expired")
        self.assertEqual(got["status"], "EXPIRED")

    def test_revalidate_unknown_quote(self):
        got, err = quotes.revalidate("q_does_not_exist", amount=1000)
        self.assertEqual(err, "quote_not_found")

    def test_revalidate_amount_mismatch(self):
        q = self._make_quote()
        got, err = quotes.revalidate(q["quote_id"], amount=2000)
        self.assertEqual(err, "amount_mismatch")

    def test_revalidate_route_not_in_quote(self):
        q = self._make_quote()
        got, err = quotes.revalidate(q["quote_id"], amount=1000,
                                     selected_route_name="Nonexistent Rail → BKASH")
        self.assertEqual(err, "route_not_in_quote")

    def test_quote_single_use(self):
        q = self._make_quote()
        quotes.consume_quote(q["quote_id"])
        got, err = quotes.revalidate(q["quote_id"], amount=1000)
        self.assertEqual(err, "quote_already_used")

    def test_ttl_must_be_positive(self):
        with self.assertRaises(ValueError):
            quotes.create_quote(corridor="uae_bd", amount=1, payout_method="BKASH",
                                routes=[], selected_route_name=None, decision="PENDING",
                                ttl_minutes=0)

    def _make_quote(self):
        return quotes.create_quote(
            corridor="uae_bd", amount=1000, payout_method="BKASH",
            routes=routing_scorer.score_routes(1000, "BKASH"),
            selected_route_name=None, decision="PENDING")


class TestExecuteBindingSafety(unittest.TestCase):
    """Execution must never move money on stale, mismatched or unconfirmed quotes."""

    def test_bound_execution_matches_quote_numbers(self):
        q = self._quote()
        state = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                 confirmed=True, amount=1000)
        self.assertIsNone(state["error"])
        quoted_best = next(r for r in q["routes"] if r["is_best"])
        self.assertEqual(state["transaction"]["true_net_receive_bdt"],
                         quoted_best["breakdown"]["true_net_receive_bdt"])
        self.assertEqual(state["transaction"]["quote_id"], q["quote_id"])
        self.assertEqual(state["transaction"]["quote_binding"], "bound")

    def test_unconfirmed_binding_refused(self):
        q = self._quote()
        state = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                 confirmed=False, amount=1000)
        self.assertEqual(state["error"], "confirmation_required")
        self.assertIsNone(state["transaction"])

    def test_expired_quote_refused_no_transaction(self):
        q = self._quote()
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        store.save_quote({**q, "expires_at": past})
        state = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                 confirmed=True, amount=1000)
        self.assertEqual(state["error"], "quote_expired")
        self.assertIsNone(state["transaction"])
        self.assertIsNone(state["execution"])

    def test_wrong_amount_on_bound_quote_refused(self):
        q = self._quote()
        state = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                 confirmed=True, amount=2000)
        self.assertEqual(state["error"], "amount_mismatch")
        self.assertIsNone(state["transaction"])

    def test_route_outside_quote_refused(self):
        """A route known to the fresh scorer but ABSENT from the bound quote
        set must be refused — the quote defines what may settle."""
        stellar_only = [r for r in routing_scorer.score_routes(1000, "BKASH")
                        if r["rail"] == "Stellar Hybrid Anchor"]
        q = quotes.create_quote(corridor="uae_bd", amount=1000, payout_method="BKASH",
                                routes=stellar_only, selected_route_name=None,
                                decision="PENDING")
        state = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                 confirmed=True, amount=1000,
                                 selected_route_name="Traditional SWIFT → BKASH")
        self.assertEqual(state["error"], "route_not_in_quote")
        self.assertIsNone(state["transaction"])

    def test_quote_consumed_after_settlement(self):
        q = self._quote()
        first = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                 confirmed=True, amount=1000)
        self.assertIsNone(first["error"])
        second = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                  confirmed=True, amount=1000)
        self.assertEqual(second["error"], "quote_already_used")
        self.assertIsNone(second["transaction"])

    def test_unbound_demo_path_still_settles_and_labels_itself(self):
        state = orchestrator.run("execute", text=TEXT)
        self.assertIsNone(state["error"])
        self.assertEqual(state["transaction"]["quote_binding"], "fresh_unbound_demo")
        self.assertTrue(state["transaction"]["quote_id"])

    def test_uncertain_settlement_never_reports_success(self):
        state = orchestrator.run("execute", text=TEXT, settlement_outcome="TIMEOUT")
        self.assertIsNone(state["error"])
        tx = state["transaction"]
        self.assertEqual(tx["status"], "RECONCILIATION_REQUIRED")
        self.assertTrue(tx["reconciliation_required"])
        self.assertIsNone(tx["stellar_hash"])
        self.assertIsNone(state["execution"]["stellar_hash"])

    def test_unpriced_route_refused_at_settlement(self):
        """A route with missing fee data may be DISPLAYED (flagged) but can
        never settle — execution is refused, no receipt, no pacs.008."""
        from app.services import compliance
        corr = corridor_cfg.load_corridor()
        patched = {**corr, "rails": [
            {**corr["rails"][1], "fee_source": None}, *corr["rails"][2:]]}
        original_dir = corridor_cfg.CORRIDOR_DIR
        corridor_cfg.load_corridor.cache_clear()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                corridor_cfg.CORRIDOR_DIR = Path(tmp)
                import json
                Path(tmp, "uae_bd.json").write_text(json.dumps(patched))
                routes = routing_scorer.score_routes(1000, "BKASH")
                broken = next(r for r in routes if "Stellar Hybrid" in r["rail"])
                q = quotes.create_quote(corridor="uae_bd", amount=1000,
                                        payout_method="BKASH", routes=routes,
                                        selected_route_name=broken["name"], decision="CLEAR")
                state = orchestrator.run("execute", text=TEXT, bound_quote_id=q["quote_id"],
                                         confirmed=True, amount=1000,
                                         selected_route_name=broken["name"])
        finally:
            corridor_cfg.CORRIDOR_DIR = original_dir
            corridor_cfg.load_corridor.cache_clear()
        self.assertEqual(state["error"], "incomplete_pricing")
        self.assertIsNone(state["transaction"])
        with self.assertRaises(ValueError):
            compliance.to_pacs_008({"transaction_id": "tx-1", "created_at": "2026-01-01T00:00:00Z",
                                    "sender_name": "A", "recipient_name": "B",
                                    "breakdown": {"true_net_receive_bdt": None}})

    def _quote(self):
        return quotes.create_quote(
            corridor="uae_bd", amount=1000, payout_method="BKASH",
            routes=routing_scorer.score_routes(1000, "BKASH"),
            selected_route_name=None, decision="PENDING")


class TestIdempotencyStore(unittest.TestCase):
    def test_first_response_wins(self):
        key = "test-key-1"
        first = {"transaction": {"transaction_id": "tx-A"}}
        store.save_idempotent_response(key, first)
        second = {"transaction": {"transaction_id": "tx-B"}}
        replayed = store.save_idempotent_response(key, second)
        self.assertEqual(replayed["transaction"]["transaction_id"], "tx-A")
        self.assertEqual(store.get_idempotent_response(key)["transaction"]["transaction_id"], "tx-A")


class TestPlatformFee(unittest.TestCase):
    """The AED 2.00 xPay sender fee: an explicit line item, subtracted exactly
    once, never masking missing rail pricing (Phase 1.5 regression)."""

    def test_platform_fee_subtracted_exactly_once(self):
        base = incentive.calculate_true_net_receive(1000, 32.80, 4.00)
        with_fee = incentive.calculate_true_net_receive(1000, 32.80, 4.00, platform_fee_source=2.00)
        self.assertEqual(with_fee["true_net_receive_exact"], "33423.20")
        self.assertEqual(with_fee["true_net_receive_bdt"], 33423.20)
        delta = (Decimal(str(with_fee["true_net_receive_bdt"]))
                 - Decimal(str(base["true_net_receive_bdt"])))
        self.assertEqual(delta, Decimal("-65.60"))  # exactly 2.00 x 32.80, once

    def test_platform_fee_is_a_visible_line_item(self):
        b = incentive.calculate_true_net_receive(1000, 32.80, 4.00, platform_fee_source=2.00)
        self.assertEqual(b["platform_fee_source"], 2.00)
        self.assertEqual(b["platform_fee_exact"], "2.00")
        self.assertEqual(b["fees_deducted_bdt"], 196.80)  # (4.00 + 2.00) x 32.80

    def test_platform_fee_never_masks_missing_rail_fee(self):
        b = incentive.calculate_true_net_receive(1000, 32.80, None, platform_fee_source=2.00)
        self.assertEqual(b["pricing_completeness"], "incomplete")
        self.assertIsNone(b["true_net_receive_bdt"])

    def test_negative_platform_fee_rejected(self):
        with self.assertRaises(MoneyValueError):
            incentive.calculate_true_net_receive_exact(1000, 32.80, 4.00, platform_fee_source=-1)

    def test_scorer_reports_fee_composition(self):
        routes = routing_scorer.score_routes(1000, "BKASH")
        stellar = next(r for r in routes if r["rail"] == "Stellar Hybrid Anchor")
        comp = stellar["fee_source_components"]
        self.assertEqual(comp["platform_fee_source"], 2.0)
        self.assertEqual(comp["rail_fee_source"] + comp["last_mile_fee_source"]
                         + comp["platform_fee_source"], stellar["fee_aed"])
        self.assertEqual(stellar["breakdown"]["platform_fee_source"], 2.0)
        self.assertEqual(stellar["breakdown"]["true_net_receive_bdt"], 33423.20)


class TestCorridorConfigInvariants(unittest.TestCase):
    """Hard invariants every corridor config must satisfy. A customer FX rate
    above mid-market is not a legal quote (the provider would be paying the
    customer to trade); the scorer must never see one."""

    def test_every_rail_fx_is_at_or_below_mid_market(self):
        for code in corridor_cfg.available_corridors():
            cfg = corridor_cfg.load_corridor(code)
            mid = D(cfg["mid_market_rate"])
            for rail in cfg["rails"]:
                self.assertLessEqual(
                    D(rail["fx"]), mid,
                    f"{code}/{rail['name']}: rail FX {rail['fx']} exceeds "
                    f"mid-market {cfg['mid_market_rate']} — not a legal quote")
                self.assertGreater(D(rail["fx"]), 0, f"{code}/{rail['name']}")

    def test_every_rail_fee_and_success_rate_are_sane(self):
        for code in corridor_cfg.available_corridors():
            cfg = corridor_cfg.load_corridor(code)
            for rail in cfg["rails"]:
                self.assertGreaterEqual(D(rail["fee_source"]), 0, f"{code}/{rail['name']}")
                self.assertTrue(0 < float(rail["success_rate"]) <= 1.0, f"{code}/{rail['name']}")
                self.assertGreater(float(rail["hours"]), 0, f"{code}/{rail['name']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
