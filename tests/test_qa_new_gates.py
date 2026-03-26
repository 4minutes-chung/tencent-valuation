"""Tests for Phase 6C: new QA gates (CRP, ERP, beta adjustment, stress coverage)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


def _write_config(tmp_path: Path) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(exist_ok=True)
    return cfg_dir


def _build_qa_inputs(
    tmp_path: Path,
    wacc_overrides: dict | None = None,
    n_stress: int = 2,
    beta_adjustment: str = "vasicek",
) -> tuple:
    """Scaffold minimum files for run_qa and return (paths, wacc_config, qa_gates, scenarios_config)."""
    from tencent_valuation_v3.paths import build_paths

    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    model = tmp_path / "data" / "model"
    model.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)

    # Write minimal tencent_financials.csv
    fin = {
        "asof": "2025-03-31",
        "revenue_hkd_bn": 600.0,
        "ebit_margin": 0.35,
        "capex_pct_revenue": 0.09,
        "nwc_pct_revenue": 0.02,
        "dep_pct_revenue": 0.03,
        "net_cash_hkd_bn": 150.0,
        "shares_out_bn": 9.6,
        "current_price_hkd": 380.0,
    }
    pd.DataFrame([fin]).to_csv(processed / "tencent_financials.csv", index=False)

    # Write wacc_components.csv with optional overrides
    wacc_base = {
        "asof": "2025-03-31",
        "wacc": 0.08,
        "rf_annual": 0.04,
        "erp_annual": 0.055,
        "crp": 0.0125,
        "beta_l_adjusted": 1.0,
        "re": 0.095,
        "re_capm": 0.095,
        "re_apt_guardrailed": 0.093,
        "rd": 0.035,
        "tax_rate_tencent": 0.15,
        "de_ratio": 0.10,
        "debt_to_equity_target": 0.10,
        "capm_apt_gap_bps": 100.0,
        "apt_is_unstable": False,
        "apt_unstable_reason_codes": "",
        "beta_stability_score": 0.9,
    }
    if wacc_overrides:
        wacc_base.update(wacc_overrides)
    pd.DataFrame([wacc_base]).to_csv(model / "wacc_components.csv", index=False)

    # Build scenarios_config with n_stress stress scenarios
    stress = {}
    if n_stress >= 1:
        stress["gaming_crackdown"] = {"description": "test", "probability": 0.05,
                                       "revenue_growth_override": [0.0] * 7, "ebit_margin_override": [0.3] * 7}
    if n_stress >= 2:
        stress["wacc_shock"] = {"description": "test2", "probability": 0.08, "wacc_adder_bps": 100}

    scenarios_config = {
        "forecast_years": 7,
        "scenarios": {
            "base": {"terminal_g": 0.025, "revenue_growth": [0.08] * 7, "ebit_margin": [0.35] * 7,
                     "capex_pct_revenue": [0.09] * 7, "nwc_pct_revenue": [0.02] * 7},
        },
        "stress_scenarios": stress,
    }

    wacc_config = {
        "capm_apt_alert_bps": 150,
        "apt_unstable_gap_bps": 400,
        "max_de_ratio": 2.0,
        "investor_grade_require_override": False,
        "source_recency_warn_days": 30,
        "source_recency_fail_days": 90,
        "beta_adjustment": beta_adjustment,
    }
    qa_gates = {
        "backtest": {"min_points": 4, "min_hit_rate_12m": 0.45, "max_calibration_mae_12m": 0.35,
                     "min_interval_coverage_12m": 0.40, "min_ic_12m": 0.10, "max_calibration_slope_deviation": 0.50},
        "scenario_bounds": {"growth_min": -0.50, "growth_max": 0.50, "margin_min": 0.0, "margin_max": 0.80,
                             "capex_min": 0.0, "capex_max": 0.40, "nwc_min": -0.10, "nwc_max": 0.20},
        "headline": {"fail_on_nan": False, "max_band_width_ratio": 3.5},
    }

    paths = build_paths(tmp_path)
    paths.ensure()
    return paths, wacc_config, qa_gates, scenarios_config


def _run_qa_and_load(paths, wacc_config, qa_gates, scenarios_config, asof="2025-03-31"):
    from tencent_valuation_v3.qa import run_qa
    artifacts = run_qa(asof, paths, wacc_config, qa_gates, peers=[], scenarios_config=scenarios_config)
    with artifacts.qa_report_json.open(encoding="utf-8") as f:
        return json.load(f)


def _get_check(report: dict, name: str) -> dict | None:
    for c in report["checks"]:
        if c["check"] == name:
            return c
    return None


class TestErpReasonablenessGate:
    def test_erp_in_bounds_passes(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, wacc_overrides={"erp_annual": 0.055})
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "erp_reasonableness")
        assert check is not None
        assert check["status"] == "pass"

    def test_erp_below_min_warns(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, wacc_overrides={"erp_annual": 0.01})
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "erp_reasonableness")
        assert check is not None
        assert check["status"] == "warn"

    def test_erp_above_max_warns(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, wacc_overrides={"erp_annual": 0.15})
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "erp_reasonableness")
        assert check is not None
        assert check["status"] == "warn"


class TestCrpReasonablenessGate:
    def test_crp_in_bounds_passes(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, wacc_overrides={"crp": 0.0125})
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "crp_reasonableness")
        assert check is not None
        assert check["status"] == "pass"

    def test_crp_above_max_warns(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, wacc_overrides={"crp": 0.10})
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "crp_reasonableness")
        assert check is not None
        assert check["status"] == "warn"


class TestBetaAdjustmentGate:
    def test_vasicek_passes(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, beta_adjustment="vasicek")
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "beta_adjustment_applied")
        assert check is not None
        assert check["status"] == "pass"

    def test_blume_passes(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, beta_adjustment="blume")
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "beta_adjustment_applied")
        assert check is not None
        assert check["status"] == "pass"

    def test_none_warns(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, beta_adjustment="none")
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "beta_adjustment_applied")
        assert check is not None
        assert check["status"] == "warn"


class TestStressCoverageGate:
    def test_two_scenarios_passes(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, n_stress=2)
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "stress_scenario_coverage")
        assert check is not None
        assert check["status"] == "pass"

    def test_one_scenario_warns(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, n_stress=1)
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "stress_scenario_coverage")
        assert check is not None
        assert check["status"] == "warn"

    def test_zero_scenarios_warns(self, tmp_path: Path):
        paths, wc, qg, sc = _build_qa_inputs(tmp_path, n_stress=0)
        report = _run_qa_and_load(paths, wc, qg, sc)
        check = _get_check(report, "stress_scenario_coverage")
        assert check is not None
        assert check["status"] == "warn"
