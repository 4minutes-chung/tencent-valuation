from __future__ import annotations

import json

import pandas as pd

from tencent_valuation_v4.paths import build_paths
from tencent_valuation_v4.report import write_report


def _write_minimum_report_inputs(tmp_path, asof: str) -> None:
    paths = build_paths(tmp_path)
    paths.ensure()

    pd.DataFrame(
        [
            {
                "asof": asof,
                "wacc": 0.085,
                "re_capm": 0.098,
                "re_apt_guardrailed": 0.094,
                "capm_apt_gap_bps": 40.0,
                "apt_is_unstable": False,
            }
        ]
    ).to_csv(paths.data_model / "wacc_components.csv", index=False)

    pd.DataFrame(
        [
            {
                "asof": asof,
                "scenario": "base",
                "fair_value_hkd_per_share": 620.0,
                "margin_of_safety": 0.15,
                "market_price_hkd": 540.0,
            },
            {
                "asof": asof,
                "scenario": "bad",
                "fair_value_hkd_per_share": 510.0,
                "margin_of_safety": -0.06,
                "market_price_hkd": 540.0,
            },
            {
                "asof": asof,
                "scenario": "extreme",
                "fair_value_hkd_per_share": 430.0,
                "margin_of_safety": -0.20,
                "market_price_hkd": 540.0,
            },
        ]
    ).to_csv(paths.data_model / "valuation_outputs.csv", index=False)

    pd.DataFrame(
        [
            {
                "n_points": 12,
                "hit_rate_12m": 0.58,
                "information_coefficient_12m": 0.21,
                "calibration_slope_12m": 0.94,
                "rmse_12m": 0.33,
                "information_coefficient_12m_calibration": 0.12,
                "information_coefficient_12m_validation": 0.25,
            }
        ]
    ).to_csv(paths.data_model / "backtest_summary.csv", index=False)

    (paths.reports / f"qa_{asof}.json").write_text(
        json.dumps(
            {
                "asof": asof,
                "summary": {"warnings": 0, "failures": 0, "total_checks": 1, "investor_grade": True},
                "checks": [],
            }
        ),
        encoding="utf-8",
    )


def test_write_report_reads_split_ic_columns(tmp_path):
    asof = "2026-04-03"
    _write_minimum_report_inputs(tmp_path, asof)
    paths = build_paths(tmp_path)

    out = write_report(asof, paths)
    content = out.read_text(encoding="utf-8")

    assert "IC (calibration split): `0.1200`" in content
    assert "IC (validation split): `0.2500`" in content
