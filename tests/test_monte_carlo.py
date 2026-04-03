"""Tests for Phase 4A: Monte Carlo simulation."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tencent_valuation_v4.monte_carlo import MonteCarloArtifacts, run_monte_carlo


WACC_COMPONENTS = {
    "wacc": 0.08,
    "rf_annual": 0.04,
    "erp_annual": 0.055,
    "beta_l_adjusted": 1.0,
    "re": 0.095,
    "rd": 0.035,
    "tax_rate_tencent": 0.15,
    "de_ratio": 0.1,
    "crp": 0.0,
}

SCENARIOS_CONFIG = {
    "forecast_years": 7,
    "mid_year_discounting": True,
    "scenarios": {
        "base": {
            "terminal_g": 0.025,
            "revenue_growth": [0.08, 0.08, 0.07, 0.07, 0.06, 0.06, 0.05],
            "ebit_margin": [0.35, 0.355, 0.36, 0.362, 0.365, 0.368, 0.37],
            "capex_pct_revenue": [0.09] * 7,
            "nwc_pct_revenue": [0.02] * 7,
        }
    },
    "monte_carlo": {
        "n_simulations": 200,
        "growth_std": 0.02,
        "margin_std": 0.015,
        "wacc_std": 0.005,
        "terminal_g_std": 0.003,
        "correlation_growth_margin": -0.3,
    },
}

FINANCIALS = {
    "revenue_hkd_bn": 600.0,
    "ebit_hkd_bn": 210.0,
    "net_cash_hkd_bn": 150.0,
    "shares_out_bn": 9.6,
    "current_price_hkd": 380.0,
    "dep_pct_revenue": 0.03,
    "book_value_hkd_bn": 600.0,
    "net_income_hkd_bn": 180.0,
    "ebit_margin": 0.35,
    "capex_pct_revenue": 0.09,
    "nwc_pct_revenue": 0.02,
    "sbc_pct_revenue": 0.014,
}


@pytest.fixture()
def mc_paths(tmp_path: Path) -> Path:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    model = tmp_path / "data" / "model"
    model.mkdir(parents=True)
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "reports").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)

    fin_df = pd.DataFrame([FINANCIALS])
    fin_df.to_csv(processed / "tencent_financials.csv", index=False)

    wacc_df = pd.DataFrame([WACC_COMPONENTS])
    wacc_df.to_csv(model / "wacc_components.csv", index=False)

    return tmp_path


def _get_paths(tmp_path: Path):
    from tencent_valuation_v4.paths import build_paths
    paths = build_paths(tmp_path)
    paths.ensure()
    return paths


class TestRunMonteCarlo:
    def test_outputs_exist(self, mc_paths: Path):
        paths = _get_paths(mc_paths)
        artifacts = run_monte_carlo("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv", seed=42)
        assert isinstance(artifacts, MonteCarloArtifacts)
        assert artifacts.monte_carlo_outputs.exists()
        assert artifacts.monte_carlo_percentiles.exists()

    def test_output_has_n_rows(self, mc_paths: Path):
        paths = _get_paths(mc_paths)
        run_monte_carlo("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv", seed=42)
        df = pd.read_csv(paths.data_model / "monte_carlo_outputs.csv")
        assert len(df) == 200  # n_simulations

    def test_output_columns(self, mc_paths: Path):
        paths = _get_paths(mc_paths)
        run_monte_carlo("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv", seed=42)
        df = pd.read_csv(paths.data_model / "monte_carlo_outputs.csv")
        assert "sim_id" in df.columns
        assert "fair_value_hkd_per_share" in df.columns
        assert "wacc" in df.columns
        assert "terminal_g" in df.columns

    def test_percentiles_are_monotone(self, mc_paths: Path):
        paths = _get_paths(mc_paths)
        run_monte_carlo("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv", seed=42)
        df = pd.read_csv(paths.data_model / "monte_carlo_percentiles.csv")
        vals = df.set_index("percentile")["fair_value_hkd_per_share"]
        pcts = sorted(vals.index)
        for i in range(len(pcts) - 1):
            assert vals[pcts[i]] <= vals[pcts[i + 1]] + 1e-6

    def test_median_positive(self, mc_paths: Path):
        paths = _get_paths(mc_paths)
        run_monte_carlo("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv", seed=42)
        df = pd.read_csv(paths.data_model / "monte_carlo_percentiles.csv")
        p50 = df.loc[df["percentile"] == 50, "fair_value_hkd_per_share"].iloc[0]
        assert p50 > 0

    def test_deterministic_with_seed(self, mc_paths: Path, tmp_path: Path):
        paths1 = _get_paths(mc_paths)
        run_monte_carlo("2025-03-31", paths1, SCENARIOS_CONFIG, paths1.data_model / "wacc_components.csv", seed=7)
        df1 = pd.read_csv(paths1.data_model / "monte_carlo_outputs.csv")

        # Second run in a fresh dir with same seed
        mc_paths2 = tmp_path / "run2"
        mc_paths2.mkdir()
        import shutil
        shutil.copytree(mc_paths / "data", mc_paths2 / "data")
        (mc_paths2 / "config").mkdir(exist_ok=True)
        (mc_paths2 / "reports").mkdir(exist_ok=True)
        paths2 = _get_paths(mc_paths2)
        run_monte_carlo("2025-03-31", paths2, SCENARIOS_CONFIG, paths2.data_model / "wacc_components.csv", seed=7)
        df2 = pd.read_csv(paths2.data_model / "monte_carlo_outputs.csv")

        assert list(df1["fair_value_hkd_per_share"]) == pytest.approx(list(df2["fair_value_hkd_per_share"]), rel=1e-6)

    def test_fair_values_spread_across_range(self, mc_paths: Path):
        paths = _get_paths(mc_paths)
        run_monte_carlo("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv", seed=99)
        df = pd.read_csv(paths.data_model / "monte_carlo_outputs.csv")
        # Distribution should have meaningful spread
        assert df["fair_value_hkd_per_share"].std() > 10.0
