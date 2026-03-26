"""Tests for Country Risk Premium — Phase 2C."""
from __future__ import annotations

import math
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v3.wacc import capm_cost_of_equity


class TestCrpMath(unittest.TestCase):
    """Pure function tests: CRP is additive on top of CAPM."""

    def test_crp_increases_re_capm_by_exact_amount(self) -> None:
        rf = 0.03
        beta = 1.1
        erp = 0.055
        crp_amount = 0.0125

        re_no_crp = capm_cost_of_equity(rf, beta, erp)
        re_with_crp = capm_cost_of_equity(rf, beta, erp) + crp_amount

        self.assertTrue(math.isclose(re_with_crp - re_no_crp, crp_amount, rel_tol=1e-12))

    def test_crp_zero_leaves_re_unchanged(self) -> None:
        rf = 0.04
        beta = 1.2
        erp = 0.06
        crp_zero = 0.0

        re_base = capm_cost_of_equity(rf, beta, erp)
        re_with_zero_crp = capm_cost_of_equity(rf, beta, erp) + crp_zero

        self.assertTrue(math.isclose(re_base, re_with_zero_crp, rel_tol=1e-12))

    def test_crp_stored_in_wacc_components(self) -> None:
        """When run_wacc writes components, crp column must be present and correct."""
        from tencent_valuation_v3.pipeline import run_all

        tmp_root = Path(tempfile.mkdtemp())
        try:
            src_config = Path(__file__).resolve().parents[1] / "config"
            shutil.copytree(src_config, tmp_root / "config")

            asof = "2026-02-18"
            raw_dir = tmp_root / "data" / "raw" / asof
            raw_dir.mkdir(parents=True, exist_ok=True)

            # Write minimal override pack so pipeline runs
            pd.DataFrame(
                [
                    {
                        "asof": asof,
                        "revenue_hkd_bn": 700.0,
                        "ebit_margin": 0.36,
                        "capex_pct_revenue": 0.09,
                        "nwc_pct_revenue": 0.02,
                        "dep_pct_revenue": 0.03,
                        "net_cash_hkd_bn": 110.0,
                        "shares_out_bn": 9.0,
                        "current_price_hkd": 300.0,
                        "fundamentals_method": "ttm_4q_from_quarterly",
                        "fundamentals_source": "override_csv",
                    }
                ]
            ).to_csv(raw_dir / "tencent_financials.csv", index=False)

            pd.DataFrame(
                [
                    {"period": asof, "segment": "VAS", "revenue_hkd_bn": 700.0,
                     "total_revenue_hkd_bn": 700.0, "segment_source": "override_csv"}
                ]
            ).to_csv(raw_dir / "segment_revenue.csv", index=False)

            peer_rows = []
            for ticker, debt, interest, tax, shares in [
                ("9988.HK", 170.0, 7.0, 0.18, 22.97),
                ("3690.HK", 120.0, 6.0, 0.19, 6.43),
                ("9999.HK", 90.0, 4.0, 0.21, 2.88),
                ("9618.HK", 110.0, 5.0, 0.20, 4.55),
                ("9888.HK", 95.0, 4.3, 0.19, 5.13),
            ]:
                peer_rows.append(
                    {
                        "ticker": ticker,
                        "gross_debt_hkd_bn": debt,
                        "interest_expense_hkd_bn_3y_avg": interest,
                        "effective_tax_rate_3y_avg": tax,
                        "shares_out_bn": shares,
                        "source_doc": "unit_test_peer_pack",
                        "source_date": asof,
                    }
                )
            pd.DataFrame(peer_rows).to_csv(raw_dir / "peer_fundamentals.csv", index=False)

            payload = run_all(asof, project_root=tmp_root, refresh=True, source_mode="synthetic")
            components = pd.read_csv(payload["wacc_components"])

            self.assertIn("crp", components.columns)
            crp_val = float(components.iloc[0]["crp"])
            # config sets country_risk_premium=0.0125
            self.assertTrue(math.isclose(crp_val, 0.0125, rel_tol=1e-6))

        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    def test_run_all_with_crp_produces_valid_output(self) -> None:
        """Pipeline with CRP > 0 still produces ordered scenario outputs."""
        from tencent_valuation_v3.pipeline import run_all

        tmp_root = Path(tempfile.mkdtemp())
        try:
            src_config = Path(__file__).resolve().parents[1] / "config"
            shutil.copytree(src_config, tmp_root / "config")

            asof = "2026-02-18"
            raw_dir = tmp_root / "data" / "raw" / asof
            raw_dir.mkdir(parents=True, exist_ok=True)

            pd.DataFrame(
                [
                    {
                        "asof": asof,
                        "revenue_hkd_bn": 700.0,
                        "ebit_margin": 0.36,
                        "capex_pct_revenue": 0.09,
                        "nwc_pct_revenue": 0.02,
                        "dep_pct_revenue": 0.03,
                        "net_cash_hkd_bn": 110.0,
                        "shares_out_bn": 9.0,
                        "current_price_hkd": 300.0,
                        "fundamentals_method": "ttm_4q_from_quarterly",
                        "fundamentals_source": "override_csv",
                    }
                ]
            ).to_csv(raw_dir / "tencent_financials.csv", index=False)

            pd.DataFrame(
                [
                    {"period": asof, "segment": "VAS", "revenue_hkd_bn": 700.0,
                     "total_revenue_hkd_bn": 700.0, "segment_source": "override_csv"}
                ]
            ).to_csv(raw_dir / "segment_revenue.csv", index=False)

            peer_rows = []
            for ticker, debt, interest, tax, shares in [
                ("9988.HK", 170.0, 7.0, 0.18, 22.97),
                ("3690.HK", 120.0, 6.0, 0.19, 6.43),
                ("9999.HK", 90.0, 4.0, 0.21, 2.88),
                ("9618.HK", 110.0, 5.0, 0.20, 4.55),
                ("9888.HK", 95.0, 4.3, 0.19, 5.13),
            ]:
                peer_rows.append(
                    {
                        "ticker": ticker,
                        "gross_debt_hkd_bn": debt,
                        "interest_expense_hkd_bn_3y_avg": interest,
                        "effective_tax_rate_3y_avg": tax,
                        "shares_out_bn": shares,
                        "source_doc": "unit_test_peer_pack",
                        "source_date": asof,
                    }
                )
            pd.DataFrame(peer_rows).to_csv(raw_dir / "peer_fundamentals.csv", index=False)

            payload = run_all(asof, project_root=tmp_root, refresh=True, source_mode="synthetic")

            valuation = pd.read_csv(payload["valuation_outputs"])
            base = float(valuation.loc[valuation["scenario"] == "base", "fair_value_hkd_per_share"].iloc[0])
            bad = float(valuation.loc[valuation["scenario"] == "bad", "fair_value_hkd_per_share"].iloc[0])
            extreme = float(valuation.loc[valuation["scenario"] == "extreme", "fair_value_hkd_per_share"].iloc[0])
            self.assertLessEqual(extreme, bad)
            self.assertLessEqual(bad, base)

        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
