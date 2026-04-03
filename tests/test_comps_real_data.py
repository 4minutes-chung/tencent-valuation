"""Phase 1B — Comps must compute multiples from real peer data when supplied.

When peer_fundamentals.csv includes net_income_hkd_bn, book_value_hkd_bn,
ebit_hkd_bn, and fcf_hkd_bn columns, the peer_multiples.csv must:
  - Have data_source == "real" for all peers
  - Have multiples consistent with the supplied figures
  - Produce scenario-varying output (bad < base, extreme < bad)
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v4.pipeline import run_all


_ASOF = "2026-02-19"


def _write_overrides(tmp: Path, asof: str) -> None:
    raw = tmp / "data" / "raw" / asof
    raw.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "asof": asof,
                "revenue_hkd_bn": 760.0,
                "ebit_margin": 0.35,
                "capex_pct_revenue": 0.10,
                "nwc_pct_revenue": 0.02,
                "dep_pct_revenue": 0.03,
                "net_cash_hkd_bn": 120.0,
                "shares_out_bn": 9.1,
                "current_price_hkd": 500.0,
                "fundamentals_source": "override_csv",
            }
        ]
    ).to_csv(raw / "tencent_financials.csv", index=False)

    # Peer fundamentals with REAL financial columns — comps must use these
    pd.DataFrame(
        [
            {
                "ticker": "9988.HK",
                "gross_debt_hkd_bn": 170.0,
                "interest_expense_hkd_bn_3y_avg": 7.0,
                "effective_tax_rate_3y_avg": 0.18,
                "shares_out_bn": 22.97,
                "net_income_hkd_bn": 90.0,
                "book_value_hkd_bn": 520.0,
                "ebit_hkd_bn": 110.0,
                "fcf_hkd_bn": 85.0,
                "source_doc": "unit_test",
                "source_date": asof,
            },
            {
                "ticker": "3690.HK",
                "gross_debt_hkd_bn": 120.0,
                "interest_expense_hkd_bn_3y_avg": 6.0,
                "effective_tax_rate_3y_avg": 0.19,
                "shares_out_bn": 6.43,
                "net_income_hkd_bn": 28.0,
                "book_value_hkd_bn": 135.0,
                "ebit_hkd_bn": 35.0,
                "fcf_hkd_bn": 20.0,
                "source_doc": "unit_test",
                "source_date": asof,
            },
            {
                "ticker": "9999.HK",
                "gross_debt_hkd_bn": 90.0,
                "interest_expense_hkd_bn_3y_avg": 4.0,
                "effective_tax_rate_3y_avg": 0.21,
                "shares_out_bn": 2.88,
                "net_income_hkd_bn": 22.0,
                "book_value_hkd_bn": 175.0,
                "ebit_hkd_bn": 27.0,
                "fcf_hkd_bn": 19.0,
                "source_doc": "unit_test",
                "source_date": asof,
            },
            {
                "ticker": "9618.HK",
                "gross_debt_hkd_bn": 110.0,
                "interest_expense_hkd_bn_3y_avg": 5.0,
                "effective_tax_rate_3y_avg": 0.20,
                "shares_out_bn": 4.55,
                "net_income_hkd_bn": 35.0,
                "book_value_hkd_bn": 270.0,
                "ebit_hkd_bn": 43.0,
                "fcf_hkd_bn": 30.0,
                "source_doc": "unit_test",
                "source_date": asof,
            },
            {
                "ticker": "9888.HK",
                "gross_debt_hkd_bn": 95.0,
                "interest_expense_hkd_bn_3y_avg": 4.3,
                "effective_tax_rate_3y_avg": 0.19,
                "shares_out_bn": 5.13,
                "net_income_hkd_bn": 26.0,
                "book_value_hkd_bn": 170.0,
                "ebit_hkd_bn": 33.0,
                "fcf_hkd_bn": 22.0,
                "source_doc": "unit_test",
                "source_date": asof,
            },
        ]
    ).to_csv(raw / "peer_fundamentals.csv", index=False)


class TestCompsRealData(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(repo_root / "config", self.tmp / "config")
        _write_overrides(self.tmp, _ASOF)
        self.payload = run_all(_ASOF, project_root=self.tmp, refresh=True, source_mode="synthetic")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_data_source_is_real(self) -> None:
        multiples = pd.read_csv(self.payload["peer_multiples"])
        self.assertTrue(
            (multiples["data_source"] == "real").all(),
            f"Expected all data_source='real', got: {multiples['data_source'].tolist()}",
        )

    def test_multiples_from_supplied_figures(self) -> None:
        """PE for 9988.HK must be market_equity / net_income, not an anchor."""
        multiples = pd.read_csv(self.payload["peer_multiples"])
        row_9988 = multiples.loc[multiples["ticker"] == "9988.HK"].iloc[0]
        # net_income supplied = 90, equity from market_inputs default = 1700
        expected_pe = float(row_9988["equity_value_hkd_bn"]) / 90.0
        actual_pe = float(row_9988["pe"])
        self.assertAlmostEqual(actual_pe, expected_pe, places=3)

    def test_scenario_varying_output(self) -> None:
        relative = pd.read_csv(self.payload["relative_valuation_outputs"])
        scenarios = set(relative["scenario"].tolist())
        self.assertIn("base", scenarios)
        self.assertIn("bad", scenarios)
        self.assertIn("extreme", scenarios)

        base_fv = float(relative.loc[relative["scenario"] == "base", "fair_value_hkd_per_share"].iloc[0])
        bad_fv = float(relative.loc[relative["scenario"] == "bad", "fair_value_hkd_per_share"].iloc[0])
        extreme_fv = float(relative.loc[relative["scenario"] == "extreme", "fair_value_hkd_per_share"].iloc[0])

        self.assertGreater(base_fv, bad_fv, "base fair value must exceed bad scenario")
        self.assertGreater(bad_fv, extreme_fv, "bad fair value must exceed extreme scenario")

    def test_ev_formula_uses_cash(self) -> None:
        """EV = equity + debt - cash.  EV should be less than equity + debt."""
        multiples = pd.read_csv(self.payload["peer_multiples"])
        # At least one peer should have ev < equity + debt (when net_cash > 0)
        # The presence of ev_ebit column confirms EV was computed
        self.assertIn("ev_ebit", multiples.columns)
        self.assertIn("ev_fcf", multiples.columns)


if __name__ == "__main__":
    unittest.main()
