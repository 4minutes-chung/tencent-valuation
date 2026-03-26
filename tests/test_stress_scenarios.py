"""Tests for Phase 6B: Named stress scenario valuations."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tencent_valuation_v3.stress import StressArtifacts, run_stress_scenarios


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
    "stress_scenarios": {
        "gaming_crackdown": {
            "description": "Severe gaming regulation",
            "probability": 0.05,
            "revenue_growth_override": [-0.15, -0.10, -0.05, 0.00, 0.02, 0.03, 0.03],
            "ebit_margin_override": [0.28, 0.27, 0.27, 0.28, 0.29, 0.30, 0.30],
        },
        "wacc_shock": {
            "description": "WACC shock +200bps",
            "probability": 0.10,
            "wacc_adder_bps": 200,
        },
    },
}


@pytest.fixture()
def stress_paths(tmp_path: Path) -> Path:
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


class TestRunStressScenarios:
    def test_artifact_exists(self, stress_paths: Path):
        paths = _get_paths(stress_paths)
        artifacts = run_stress_scenarios(
            "2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv"
        )
        assert isinstance(artifacts, StressArtifacts)
        assert artifacts.stress_scenario_outputs.exists()

    def test_two_scenarios_in_output(self, stress_paths: Path):
        paths = _get_paths(stress_paths)
        run_stress_scenarios("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv")
        df = pd.read_csv(paths.data_model / "stress_scenario_outputs.csv")
        assert len(df) == 2
        assert set(df["stress_scenario"]) == {"gaming_crackdown", "wacc_shock"}

    def test_crackdown_lower_fv_than_wacc_shock(self, stress_paths: Path):
        """Gaming crackdown with severe revenue declines should produce lower FV than just a WACC shock."""
        paths = _get_paths(stress_paths)
        run_stress_scenarios("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv")
        df = pd.read_csv(paths.data_model / "stress_scenario_outputs.csv")
        fv = df.set_index("stress_scenario")["fair_value_hkd_per_share"]
        assert fv["gaming_crackdown"] < fv["wacc_shock"]

    def test_wacc_adder_increases_wacc(self, stress_paths: Path):
        paths = _get_paths(stress_paths)
        run_stress_scenarios("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv")
        df = pd.read_csv(paths.data_model / "stress_scenario_outputs.csv")
        shock_wacc = float(df[df["stress_scenario"] == "wacc_shock"]["wacc"].iloc[0])
        base_wacc = WACC_COMPONENTS["wacc"]
        assert abs(shock_wacc - (base_wacc + 0.02)) < 1e-6

    def test_probabilities_stored(self, stress_paths: Path):
        paths = _get_paths(stress_paths)
        run_stress_scenarios("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv")
        df = pd.read_csv(paths.data_model / "stress_scenario_outputs.csv")
        probs = df.set_index("stress_scenario")["probability"]
        assert abs(probs["gaming_crackdown"] - 0.05) < 1e-6
        assert abs(probs["wacc_shock"] - 0.10) < 1e-6

    def test_no_stress_scenarios_produces_empty_csv(self, stress_paths: Path):
        paths = _get_paths(stress_paths)
        cfg_no_stress = {**SCENARIOS_CONFIG}
        cfg_no_stress.pop("stress_scenarios", None)
        run_stress_scenarios("2025-03-31", paths, cfg_no_stress, paths.data_model / "wacc_components.csv")
        df = pd.read_csv(paths.data_model / "stress_scenario_outputs.csv")
        assert len(df) == 0

    def test_probabilities_sum_below_one(self, stress_paths: Path):
        paths = _get_paths(stress_paths)
        run_stress_scenarios("2025-03-31", paths, SCENARIOS_CONFIG, paths.data_model / "wacc_components.csv")
        df = pd.read_csv(paths.data_model / "stress_scenario_outputs.csv")
        total = df["probability"].sum()
        assert total < 1.0
