import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from tencent_valuation.backtest import run_backtest
from tencent_valuation.paths import build_paths
from tencent_valuation.pipeline import load_context, run_all


class IntegrationPipelineTests(unittest.TestCase):
    def _setup_tmp_root(self) -> Path:
        repo_root = Path(__file__).resolve().parents[1]
        tmp_root = Path(tempfile.mkdtemp())
        shutil.copytree(repo_root / "config", tmp_root / "config")
        return tmp_root

    def _write_override_pack(self, tmp_root: Path, asof: str) -> None:
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
                {
                    "period": asof,
                    "segment": "VAS",
                    "revenue_hkd_bn": 230.0,
                    "total_revenue_hkd_bn": 700.0,
                    "segment_source": "override_csv",
                },
                {
                    "period": asof,
                    "segment": "Marketing Services",
                    "revenue_hkd_bn": 150.0,
                    "total_revenue_hkd_bn": 700.0,
                    "segment_source": "override_csv",
                },
                {
                    "period": asof,
                    "segment": "FinTech and Business Services",
                    "revenue_hkd_bn": 295.0,
                    "total_revenue_hkd_bn": 700.0,
                    "segment_source": "override_csv",
                },
                {
                    "period": asof,
                    "segment": "Others",
                    "revenue_hkd_bn": 25.0,
                    "total_revenue_hkd_bn": 700.0,
                    "segment_source": "override_csv",
                },
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

    def test_run_all_without_overrides_marks_not_investor_grade(self) -> None:
        tmp_root = self._setup_tmp_root()
        self.addCleanup(lambda: shutil.rmtree(tmp_root, ignore_errors=True))

        payload = run_all("2026-02-18", project_root=tmp_root, refresh=True, source_mode="synthetic")
        qa_path = Path(payload["qa_report"])
        self.assertTrue(qa_path.exists())

        with qa_path.open("r", encoding="utf-8") as handle:
            qa = json.load(handle)

        self.assertFalse(bool(qa["summary"].get("investor_grade")))
        checks = {item["check"]: item for item in qa["checks"]}
        self.assertEqual(checks["override_fundamentals_present"]["status"], "fail")

    def test_run_all_with_overrides_passes_override_checks(self) -> None:
        tmp_root = self._setup_tmp_root()
        self.addCleanup(lambda: shutil.rmtree(tmp_root, ignore_errors=True))
        asof = "2026-02-18"
        self._write_override_pack(tmp_root, asof)

        payload = run_all(asof, project_root=tmp_root, refresh=True, source_mode="synthetic")
        for key in [
            "wacc_components",
            "capm_apt_compare",
            "valuation_outputs",
            "sensitivity_wacc_g",
            "sensitivity_margin_growth",
            "scenario_assumptions_used",
            "qa_report",
            "report",
            "investment_memo",
        ]:
            self.assertIn(key, payload)
            self.assertTrue(Path(payload[key]).exists())

        valuation = pd.read_csv(payload["valuation_outputs"])
        base = float(valuation.loc[valuation["scenario"] == "base", "fair_value_hkd_per_share"].iloc[0])
        bad = float(valuation.loc[valuation["scenario"] == "bad", "fair_value_hkd_per_share"].iloc[0])
        extreme = float(valuation.loc[valuation["scenario"] == "extreme", "fair_value_hkd_per_share"].iloc[0])
        self.assertLessEqual(extreme, bad)
        self.assertLessEqual(bad, base)

        with open(payload["qa_report"], "r", encoding="utf-8") as handle:
            qa = json.load(handle)
        checks = {item["check"]: item for item in qa["checks"]}
        self.assertEqual(checks["override_fundamentals_present"]["status"], "pass")
        self.assertEqual(checks["fundamentals_ttm_method"]["status"], "pass")
        self.assertEqual(checks["peer_input_coverage"]["status"], "pass")

    def test_backtest_outputs_schema(self) -> None:
        tmp_root = self._setup_tmp_root()
        self.addCleanup(lambda: shutil.rmtree(tmp_root, ignore_errors=True))

        ctx = load_context(tmp_root)

        mock_prices = pd.Series(
            [300.0 + (0.05 * i) for i in range(2200)],
            index=pd.date_range(start="2020-01-01", periods=2200, freq="D"),
            name="0700.HK",
        )
        with mock.patch("tencent_valuation.backtest.fetch_close_series_for_ticker", return_value=mock_prices):
            artifacts = run_backtest(
                start="2024-01-01",
                end="2025-03-31",
                freq="quarterly",
                paths=ctx.paths,
                wacc_config=ctx.wacc_config,
                scenarios_config=ctx.scenarios_config,
                peers=ctx.peers,
                source_mode="synthetic",
            )

        summary = pd.read_csv(artifacts.summary)
        points = pd.read_csv(artifacts.point_results)

        for col in ["n_points", "hit_rate_6m", "hit_rate_12m", "calibration_mae_12m"]:
            self.assertIn(col, summary.columns)
        for col in ["asof", "base_mos", "forward_6m_return", "forward_12m_return", "direction_hit_12m"]:
            self.assertIn(col, points.columns)
        self.assertGreaterEqual(int(summary.iloc[0]["n_points"]), 1)


if __name__ == "__main__":
    unittest.main()
