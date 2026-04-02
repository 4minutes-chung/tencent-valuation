"""Tests for Phase 4D: Real Options (Black-Scholes)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tencent_valuation_v3.real_options import RealOptionsArtifacts, black_scholes_call, run_real_options


WACC_CONFIG = {
    "real_options": {
        "cloud_ai_current_value_hkd_bn": 150.0,
        "investment_needed_hkd_bn": 80.0,
        "time_to_maturity_years": 7,
        "volatility": 0.40,
    }
}

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

FINANCIALS = {
    "revenue_hkd_bn": 600.0,
    "shares_out_bn": 9.6,
    "current_price_hkd": 380.0,
    "net_cash_hkd_bn": 150.0,
    "dep_pct_revenue": 0.03,
    "ebit_margin": 0.35,
    "capex_pct_revenue": 0.09,
    "nwc_pct_revenue": 0.02,
}


@pytest.fixture()
def ro_paths(tmp_path: Path) -> Path:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    model = tmp_path / "data" / "model"
    model.mkdir(parents=True)
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "reports").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)

    pd.DataFrame([FINANCIALS]).to_csv(processed / "tencent_financials.csv", index=False)
    pd.DataFrame([WACC_COMPONENTS]).to_csv(model / "wacc_components.csv", index=False)
    return tmp_path


def _get_paths(p: Path):
    from tencent_valuation_v3.paths import build_paths
    paths = build_paths(p)
    paths.ensure()
    return paths


class TestBlackScholesCall:
    def test_deep_itm_approaches_intrinsic(self):
        # S >> K: call ≈ S - K * exp(-rT)
        val = black_scholes_call(s=1000.0, k=1.0, t=1.0, r=0.05, sigma=0.30)
        assert val > 990.0

    def test_deep_otm_approaches_zero(self):
        val = black_scholes_call(s=1.0, k=1000.0, t=1.0, r=0.05, sigma=0.30)
        assert val < 0.01

    def test_atm_positive(self):
        val = black_scholes_call(s=100.0, k=100.0, t=1.0, r=0.05, sigma=0.30)
        assert val > 0

    def test_known_value(self):
        # From standard BS tables: S=100, K=100, T=1, r=0.05, sigma=0.20 ≈ 10.45
        val = black_scholes_call(s=100.0, k=100.0, t=1.0, r=0.05, sigma=0.20)
        assert abs(val - 10.45) < 0.30  # within 30 cents

    def test_higher_vol_gives_higher_value(self):
        v_low = black_scholes_call(100.0, 100.0, 1.0, 0.05, 0.20)
        v_high = black_scholes_call(100.0, 100.0, 1.0, 0.05, 0.40)
        assert v_high > v_low

    def test_longer_time_gives_higher_value(self):
        v_short = black_scholes_call(100.0, 100.0, 1.0, 0.05, 0.30)
        v_long = black_scholes_call(100.0, 100.0, 5.0, 0.05, 0.30)
        assert v_long > v_short


class TestRunRealOptions:
    def test_artifact_exists(self, ro_paths: Path):
        paths = _get_paths(ro_paths)
        artifacts = run_real_options("2025-03-31", paths, paths.data_model / "wacc_components.csv", WACC_CONFIG)
        assert isinstance(artifacts, RealOptionsArtifacts)
        assert artifacts.real_options_outputs.exists()

    def test_required_columns(self, ro_paths: Path):
        paths = _get_paths(ro_paths)
        run_real_options("2025-03-31", paths, paths.data_model / "wacc_components.csv", WACC_CONFIG)
        df = pd.read_csv(paths.data_model / "real_options_outputs.csv")
        assert "scenario" in df.columns
        assert "option_value_hkd_bn" in df.columns
        assert "option_value_hkd_per_share" in df.columns

    def test_base_option_value_positive(self, ro_paths: Path):
        paths = _get_paths(ro_paths)
        run_real_options("2025-03-31", paths, paths.data_model / "wacc_components.csv", WACC_CONFIG)
        df = pd.read_csv(paths.data_model / "real_options_outputs.csv")
        base = df[df["scenario"] == "base"].iloc[0]
        assert base["option_value_hkd_bn"] > 0

    def test_extreme_scenario_zero_or_lower(self, ro_paths: Path):
        paths = _get_paths(ro_paths)
        run_real_options("2025-03-31", paths, paths.data_model / "wacc_components.csv", WACC_CONFIG)
        df = pd.read_csv(paths.data_model / "real_options_outputs.csv")
        fv = df.set_index("scenario")["option_value_hkd_bn"]
        assert fv["extreme"] <= fv["base"] + 1e-6

    def test_no_scipy_dependency(self):
        """Verify the module does not import scipy."""
        import sys
        # Remove cached module if present
        mods = [k for k in sys.modules if "real_options" in k]
        for m in mods:
            del sys.modules[m]
        import tencent_valuation_v3.real_options as ro_mod
        import inspect
        source = inspect.getsource(ro_mod)
        assert "scipy" not in source
