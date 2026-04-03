"""Phase 1D — Backtest must not mutate the main project's data files.

Each backtest iteration runs in an isolated temp directory.  After the
backtest completes, the main project's wacc_components.csv and
valuation_outputs.csv must be byte-for-byte identical to what they were
before the backtest ran.
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v4.backtest import run_backtest
from tencent_valuation_v4.config import load_yaml
from tencent_valuation_v4.factors import run_factors
from tencent_valuation_v4.paths import build_paths
from tencent_valuation_v4.wacc import run_wacc


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


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


class TestBacktestIsolation(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(repo_root / "config", self.tmp / "config")
        _write_overrides(self.tmp, _ASOF)

        self.paths = build_paths(self.tmp)
        self.paths.ensure()
        self.wacc_config = load_yaml(self.paths.config / "wacc.yaml")
        peers_cfg = load_yaml(self.paths.config / "peers.yaml")
        self.peers = [str(p) for p in peers_cfg.get("peers", [])]
        self.scenarios_config = load_yaml(self.paths.config / "scenarios.yaml")

        # Build the main project files first
        factor_artifacts = run_factors(
            _ASOF,
            self.paths,
            self.peers,
            self.wacc_config,
            refresh=True,
            source_mode="synthetic",
        )
        run_wacc(_ASOF, self.paths, factor_artifacts, self.peers, self.wacc_config)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_wacc_components_unchanged_after_backtest(self) -> None:
        wacc_path = self.paths.data_model / "wacc_components.csv"
        self.assertTrue(wacc_path.exists(), "wacc_components.csv must exist before backtest")
        md5_before = _md5(wacc_path)

        run_backtest(
            start="2025-09-01",
            end="2026-02-19",
            freq="quarterly",
            paths=self.paths,
            wacc_config=self.wacc_config,
            scenarios_config=self.scenarios_config,
            peers=self.peers,
            source_mode="synthetic",
        )

        md5_after = _md5(wacc_path)
        self.assertEqual(
            md5_before,
            md5_after,
            "wacc_components.csv was modified during backtest — isolation broken",
        )

    def test_monthly_factors_unchanged_after_backtest(self) -> None:
        monthly_path = self.paths.data_processed / "monthly_factors.csv"
        self.assertTrue(monthly_path.exists())
        md5_before = _md5(monthly_path)

        run_backtest(
            start="2025-09-01",
            end="2026-02-19",
            freq="quarterly",
            paths=self.paths,
            wacc_config=self.wacc_config,
            scenarios_config=self.scenarios_config,
            peers=self.peers,
            source_mode="synthetic",
        )

        self.assertEqual(
            md5_before,
            _md5(monthly_path),
            "monthly_factors.csv was modified during backtest — isolation broken",
        )

    def test_backtest_output_files_created(self) -> None:
        run_backtest(
            start="2025-09-01",
            end="2026-02-19",
            freq="quarterly",
            paths=self.paths,
            wacc_config=self.wacc_config,
            scenarios_config=self.scenarios_config,
            peers=self.peers,
            source_mode="synthetic",
        )
        self.assertTrue((self.paths.data_model / "backtest_point_results.csv").exists())
        self.assertTrue((self.paths.data_model / "backtest_summary.csv").exists())
        self.assertTrue((self.paths.data_model / "backtest_regime_breakdown.csv").exists())


if __name__ == "__main__":
    unittest.main()
