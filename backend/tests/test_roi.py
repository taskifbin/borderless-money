"""ROI model tests — every derived number checked against hand computation.

Stdlib only (python3 backend/tests/test_roi.py).
"""
import sys
import unittest
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.money import MoneyValueError  # noqa: E402
from app.services.roi import calculate_roi  # noqa: E402

BASE = dict(
    monthly_transfers=5000, avg_principal=1000,
    baseline_all_in_cost_pct=0.015, proposed_all_in_cost_pct=0.009,
    eligibility_share=0.80, adoption_rate=0.50,
    api_price_per_tx=1.00, api_monthly_fee=0,
    customer_cost_bearing_share=1.0, customer_monthly_costs=500,
    vendor_variable_cost_per_tx=0.25, horizon_months=12,
)


def dec(x):
    return Decimal(x)


class TestRoiHandComputed(unittest.TestCase):
    def setUp(self):
        self.r = calculate_roi(**BASE)

    def test_volume_funnel(self):
        self.assertEqual(self.r["monthly"]["eligible_transfers"], dec("4000.00"))
        self.assertEqual(self.r["monthly"]["adopted_transfers"], dec("2000.00"))
        self.assertEqual(self.r["monthly"]["principal_moved"], dec("2000000.00"))

    def test_benefit_and_savings(self):
        # gap = 1.5% - 0.9% = 0.6% of 2,000,000 = 12,000
        self.assertEqual(self.r["monthly"]["gross_recipient_benefit"], dec("12000.00"))
        self.assertEqual(self.r["monthly"]["customer_cost_savings"], dec("12000.00"))

    def test_revenue_net_and_cost_per_tx(self):
        self.assertEqual(self.r["monthly"]["api_revenue"], dec("2000.00"))
        self.assertEqual(self.r["monthly"]["customer_net_benefit"], dec("9500.00"))
        self.assertEqual(self.r["monthly"]["customer_cost_per_transaction"], dec("1.00"))

    def test_vendor_margin_only_with_cost_inputs(self):
        # (2000 - 2000*0.25) / 2000 = 75%
        self.assertEqual(self.r["monthly"]["vendor_gross_margin_pct"], dec("75.00"))
        r = calculate_roi(**{**BASE, "vendor_variable_cost_per_tx": None})
        self.assertIsNone(r["monthly"]["vendor_gross_margin_pct"])

    def test_recipient_benefit_is_never_vendor_revenue(self):
        self.assertNotEqual(self.r["monthly"]["api_revenue"],
                            self.r["monthly"]["gross_recipient_benefit"])

    def test_horizon_scales_linearly(self):
        self.assertEqual(self.r["horizon"]["customer_net_benefit"], dec("114000.00"))
        self.assertEqual(self.r["horizon"]["months"], 12)

    def test_break_even_hand_computed(self):
        # 500 / (0.8 * 0.5 * (1000*0.006*1 - 1)) = 500 / 2 = 250
        self.assertEqual(self.r["break_even"]["monthly_transfers"], dec("250.00"))

    def test_scenarios(self):
        s = self.r["scenarios"]
        self.assertEqual(s["conservative"]["adopted_transfers"], dec("800.00"))
        self.assertEqual(s["conservative"]["customer_net_benefit"], dec("3500.00"))
        self.assertEqual(s["optimistic"]["adopted_transfers"], dec("3000.00"))
        self.assertEqual(s["optimistic"]["customer_net_benefit"], dec("14500.00"))
        self.assertEqual(s["base"]["customer_net_benefit"], dec("9500.00"))

    def test_assumptions_labeled_not_measurements(self):
        self.assertEqual(self.r["labels"]["all_derived_values"], "modeled_estimate")
        self.assertEqual(self.r["labels"]["adoption_rate"], "user_assumption")
        self.assertIn("never counted as vendor revenue", self.r["disclaimer"])


class TestRoiEdgeCases(unittest.TestCase):
    def test_bearing_share_below_one_cuts_savings(self):
        r = calculate_roi(**{**BASE, "customer_cost_bearing_share": 0.5})
        self.assertEqual(r["monthly"]["customer_cost_savings"], dec("6000.00"))
        self.assertEqual(r["monthly"]["gross_recipient_benefit"], dec("12000.00"))
        self.assertEqual(r["monthly"]["customer_net_benefit"], dec("3500.00"))

    def test_no_positive_breakeven_when_saving_below_price(self):
        r = calculate_roi(**{**BASE, "api_price_per_tx": 10.0})
        self.assertIsNone(r["break_even"]["monthly_transfers"])
        self.assertIn("no positive break-even", r["break_even"]["note"])

    def test_zero_adoption_with_no_costs_is_trivially_profitable(self):
        r = calculate_roi(**{**BASE, "adoption_rate": 0, "customer_monthly_costs": 0})
        self.assertEqual(r["break_even"]["monthly_transfers"], dec("0"))

    def test_monthly_fee_raises_breakeven(self):
        r = calculate_roi(**{**BASE, "api_monthly_fee": 1000})
        # 1500 / 2 = 750
        self.assertEqual(r["break_even"]["monthly_transfers"], dec("750.00"))

    def test_input_validation(self):
        with self.assertRaises(MoneyValueError):
            calculate_roi(**{**BASE, "monthly_transfers": 0})
        with self.assertRaises(MoneyValueError):
            calculate_roi(**{**BASE, "adoption_rate": 1.5})
        with self.assertRaises(MoneyValueError):
            calculate_roi(**{**BASE, "baseline_all_in_cost_pct": -0.1})
        with self.assertRaises(MoneyValueError):
            calculate_roi(**{**BASE, "proposed_all_in_cost_pct": 0.02})  # above baseline
        with self.assertRaises(MoneyValueError):
            calculate_roi(**{**BASE, "avg_principal": 0})
        with self.assertRaises(MoneyValueError):
            calculate_roi(**{**BASE, "api_price_per_tx": -1})

    def test_reproducible(self):
        self.assertEqual(calculate_roi(**BASE), calculate_roi(**BASE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
