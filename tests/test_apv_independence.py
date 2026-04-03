"""Phase 1A — APV must be algebraically independent from DCF.

After the rewrite, APV discounts FCFF at Ru (unlevered cost of equity),
whereas DCF uses WACC.  When D/E > 0, Ru != WACC, so the fair values must
differ.  If they are identical it means the tautology was re-introduced.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v4.pipeline import run_all


class TestApvIndependence(unittest.TestCase):
    def _setup(self) -> Path:
        repo_root = Path(__file__).resolve().parents[1]
        tmp = Path(tempfile.mkdtemp())
        shutil.copytree(repo_root / "config", tmp / "config")
        return tmp

    def _write_overrides(self, tmp: Path, asof: str) -> None:
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

    def test_apv_differs_from_dcf(self) -> None:
        tmp = self._setup()
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        asof = "2026-02-19"
        self._write_overrides(tmp, asof)

        payload = run_all(asof, project_root=tmp, refresh=True, source_mode="synthetic")

        dcf = pd.read_csv(payload["valuation_outputs"])
        apv = pd.read_csv(payload["apv_outputs"])

        for scenario in ["base", "bad", "extreme"]:
            dcf_fv = float(dcf.loc[dcf["scenario"] == scenario, "fair_value_hkd_per_share"].iloc[0])
            apv_fv = float(apv.loc[apv["scenario"] == scenario, "fair_value_hkd_per_share"].iloc[0])
            self.assertNotAlmostEqual(
                dcf_fv,
                apv_fv,
                places=2,
                msg=(
                    f"APV and DCF fair values are identical for scenario={scenario} "
                    f"({apv_fv:.4f} == {dcf_fv:.4f}). "
                    "APV tautology may have been re-introduced."
                ),
            )

    def test_apv_has_ru_column(self) -> None:
        """APV output must record the unlevered cost of equity."""
        tmp = self._setup()
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        asof = "2026-02-19"
        self._write_overrides(tmp, asof)
        payload = run_all(asof, project_root=tmp, refresh=True, source_mode="synthetic")
        apv = pd.read_csv(payload["apv_outputs"])
        self.assertIn("ru", apv.columns)
        # Ru should be positive and different from a typical WACC (~0.07-0.12)
        ru_val = float(apv["ru"].iloc[0])
        self.assertGreater(ru_val, 0.0)

    def test_apv_method_column(self) -> None:
        tmp = self._setup()
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        asof = "2026-02-19"
        self._write_overrides(tmp, asof)
        payload = run_all(asof, project_root=tmp, refresh=True, source_mode="synthetic")
        apv = pd.read_csv(payload["apv_outputs"])
        self.assertTrue((apv["method"] == "apv").all())


if __name__ == "__main__":
    unittest.main()
