"""Tests for _resolve_rd — Phase 2F."""
from __future__ import annotations

import math
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v3.wacc import _resolve_rd, calc_rd


class TestResolveRd(unittest.TestCase):
    def test_synthetic_spread_basic(self) -> None:
        rf = 0.04
        cfg = {
            "rd_method": "synthetic_spread",
            "rd_spread_bps": 150,
            "rd_floor": 0.015,
            "rd_ceiling": 0.12,
        }
        rd, method = _resolve_rd(rf, cfg, interest_expense=5.0, avg_gross_debt=100.0)
        expected = rf + 150 / 10000
        self.assertTrue(math.isclose(rd, expected, rel_tol=1e-12))
        self.assertEqual(method, "synthetic_spread")

    def test_synthetic_spread_respects_floor(self) -> None:
        # rf very low → rf + spread < floor → should return floor
        rf = 0.001
        cfg = {
            "rd_method": "synthetic_spread",
            "rd_spread_bps": 50,   # only 50bps above 0.001 = 0.0015 < floor 0.015
            "rd_floor": 0.015,
            "rd_ceiling": 0.12,
        }
        rd, method = _resolve_rd(rf, cfg, interest_expense=1.0, avg_gross_debt=100.0)
        self.assertEqual(rd, 0.015)
        self.assertEqual(method, "synthetic_spread")

    def test_synthetic_spread_respects_ceiling(self) -> None:
        # rf very high → rf + spread > ceiling
        rf = 0.20
        cfg = {
            "rd_method": "synthetic_spread",
            "rd_spread_bps": 500,
            "rd_floor": 0.015,
            "rd_ceiling": 0.12,
        }
        rd, method = _resolve_rd(rf, cfg, interest_expense=5.0, avg_gross_debt=100.0)
        self.assertEqual(rd, 0.12)
        self.assertEqual(method, "synthetic_spread")

    def test_historical_method_uses_calc_rd(self) -> None:
        cfg = {
            "rd_method": "historical",
            "rd_floor": 0.015,
            "rd_ceiling": 0.12,
        }
        interest = 8.0
        debt = 100.0
        rd, method = _resolve_rd(0.04, cfg, interest_expense=interest, avg_gross_debt=debt)
        expected = calc_rd(interest, debt, 0.015, 0.12)
        self.assertTrue(math.isclose(rd, expected, rel_tol=1e-12))
        self.assertEqual(method, "historical")

    def test_default_method_is_historical(self) -> None:
        cfg = {"rd_floor": 0.015, "rd_ceiling": 0.12}  # no rd_method key
        rd, method = _resolve_rd(0.04, cfg, interest_expense=8.0, avg_gross_debt=100.0)
        self.assertEqual(method, "historical")

    def test_rd_stored_in_wacc_components_synthetic(self) -> None:
        """Run pipeline with synthetic_spread config and verify rd column in wacc_components."""
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
            components = pd.read_csv(payload["wacc_components"])

            self.assertIn("rd", components.columns)
            self.assertIn("rd_method", components.columns)

            rd_val = float(components.iloc[0]["rd"])
            rd_method_val = str(components.iloc[0]["rd_method"])
            # config uses synthetic_spread with rd_spread_bps=150
            self.assertEqual(rd_method_val, "synthetic_spread")
            # rd = clamp(rf + 0.015, 0.015, 0.12), so should be in [0.015, 0.12]
            self.assertGreaterEqual(rd_val, 0.015)
            self.assertLessEqual(rd_val, 0.12)

        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
