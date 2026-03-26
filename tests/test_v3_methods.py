import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v3.ensemble import _normalize_weights
from tencent_valuation_v3.pipeline import run_all


class V3MethodTests(unittest.TestCase):
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
                    "revenue_hkd_bn": 760.0,
                    "ebit_margin": 0.35,
                    "capex_pct_revenue": 0.10,
                    "nwc_pct_revenue": 0.02,
                    "dep_pct_revenue": 0.03,
                    "net_cash_hkd_bn": 120.0,
                    "shares_out_bn": 9.1,
                    "current_price_hkd": 500.0,
                    "fundamentals_method": "ttm_4q_from_quarterly",
                    "fundamentals_source": "override_csv",
                }
            ]
        ).to_csv(raw_dir / "tencent_financials.csv", index=False)

        pd.DataFrame(
            [
                {"period": asof, "segment": "VAS", "revenue_hkd_bn": 250.0, "total_revenue_hkd_bn": 760.0},
                {
                    "period": asof,
                    "segment": "Marketing Services",
                    "revenue_hkd_bn": 170.0,
                    "total_revenue_hkd_bn": 760.0,
                },
                {
                    "period": asof,
                    "segment": "FinTech and Business Services",
                    "revenue_hkd_bn": 310.0,
                    "total_revenue_hkd_bn": 760.0,
                },
                {"period": asof, "segment": "Others", "revenue_hkd_bn": 30.0, "total_revenue_hkd_bn": 760.0},
            ]
        ).to_csv(raw_dir / "segment_revenue.csv", index=False)

        pd.DataFrame(
            [
                {
                    "ticker": "9988.HK",
                    "gross_debt_hkd_bn": 170.0,
                    "interest_expense_hkd_bn_3y_avg": 7.0,
                    "effective_tax_rate_3y_avg": 0.18,
                    "shares_out_bn": 22.97,
                    "source_doc": "unit_test",
                    "source_date": asof,
                },
                {
                    "ticker": "3690.HK",
                    "gross_debt_hkd_bn": 120.0,
                    "interest_expense_hkd_bn_3y_avg": 6.0,
                    "effective_tax_rate_3y_avg": 0.19,
                    "shares_out_bn": 6.43,
                    "source_doc": "unit_test",
                    "source_date": asof,
                },
                {
                    "ticker": "9999.HK",
                    "gross_debt_hkd_bn": 90.0,
                    "interest_expense_hkd_bn_3y_avg": 4.0,
                    "effective_tax_rate_3y_avg": 0.21,
                    "shares_out_bn": 2.88,
                    "source_doc": "unit_test",
                    "source_date": asof,
                },
                {
                    "ticker": "9618.HK",
                    "gross_debt_hkd_bn": 110.0,
                    "interest_expense_hkd_bn_3y_avg": 5.0,
                    "effective_tax_rate_3y_avg": 0.20,
                    "shares_out_bn": 4.55,
                    "source_doc": "unit_test",
                    "source_date": asof,
                },
                {
                    "ticker": "9888.HK",
                    "gross_debt_hkd_bn": 95.0,
                    "interest_expense_hkd_bn_3y_avg": 4.3,
                    "effective_tax_rate_3y_avg": 0.19,
                    "shares_out_bn": 5.13,
                    "source_doc": "unit_test",
                    "source_date": asof,
                },
            ]
        ).to_csv(raw_dir / "peer_fundamentals.csv", index=False)

    def test_weight_normalization(self) -> None:
        normalized = _normalize_weights({"a": 2.0, "b": 1.0, "c": 1.0})
        self.assertAlmostEqual(sum(normalized.values()), 1.0, places=12)
        self.assertGreater(normalized["a"], normalized["b"])

    def test_v3_output_contracts(self) -> None:
        tmp_root = self._setup_tmp_root()
        self.addCleanup(lambda: shutil.rmtree(tmp_root, ignore_errors=True))
        asof = "2026-02-19"
        self._write_override_pack(tmp_root, asof)

        payload = run_all(asof, project_root=tmp_root, refresh=True, source_mode="synthetic")

        reverse = pd.read_csv(payload["reverse_dcf_outputs"])
        self.assertIn("implied_terminal_g", reverse.columns)
        self.assertIn("implied_margin_shift_bps", reverse.columns)

        tvalue_stats = pd.read_csv(payload["tvalue_stat_diagnostics"])
        for col in ["factor", "beta", "lambda", "t_beta", "t_lambda", "stability_flag"]:
            self.assertIn(col, tvalue_stats.columns)

        ensemble = pd.read_csv(payload["valuation_ensemble"])
        for col in ["scenario", "ensemble_fair_value_hkd_per_share", "band_width_ratio"]:
            self.assertIn(col, ensemble.columns)


if __name__ == "__main__":
    unittest.main()
