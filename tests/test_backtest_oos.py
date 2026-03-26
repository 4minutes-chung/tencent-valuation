"""Tests for Phase 5E: out-of-sample split and vintage config loading."""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from tencent_valuation_v3.backtest import _load_vintage_config, _compute_metrics


FALLBACK = {"forecast_years": 7, "scenarios": {"base": {"terminal_g": 0.025}}}


class TestLoadVintageConfig:
    def test_loads_matching_year(self, tmp_path: Path):
        vintages_dir = tmp_path / "backtest_vintages"
        vintages_dir.mkdir()
        config = {"forecast_years": 7, "vintage": "2022", "scenarios": {"base": {}}}
        import yaml
        (vintages_dir / "2022.yaml").write_text(yaml.dump(config), encoding="utf-8")
        result = _load_vintage_config("2022-03-31", tmp_path, FALLBACK)
        assert result["vintage"] == "2022"

    def test_falls_back_to_earlier_year(self, tmp_path: Path):
        vintages_dir = tmp_path / "backtest_vintages"
        vintages_dir.mkdir()
        config = {"forecast_years": 7, "vintage": "2020", "scenarios": {"base": {}}}
        import yaml
        (vintages_dir / "2020.yaml").write_text(yaml.dump(config), encoding="utf-8")
        # No 2022.yaml, no 2021.yaml — should find 2020.yaml
        result = _load_vintage_config("2022-06-30", tmp_path, FALLBACK)
        assert result["vintage"] == "2020"

    def test_falls_back_to_fallback_when_no_vintage(self, tmp_path: Path):
        # No vintages directory at all
        result = _load_vintage_config("2022-06-30", tmp_path, FALLBACK)
        assert result is FALLBACK

    def test_year_extracted_from_asof_string(self, tmp_path: Path):
        vintages_dir = tmp_path / "backtest_vintages"
        vintages_dir.mkdir()
        config = {"forecast_years": 7, "vintage": "2019", "scenarios": {"base": {}}}
        import yaml
        (vintages_dir / "2019.yaml").write_text(yaml.dump(config), encoding="utf-8")
        result = _load_vintage_config("2019-12-31", tmp_path, FALLBACK)
        assert result["vintage"] == "2019"

    def test_empty_vintages_dir_uses_fallback(self, tmp_path: Path):
        vintages_dir = tmp_path / "backtest_vintages"
        vintages_dir.mkdir()
        result = _load_vintage_config("2023-09-30", tmp_path, FALLBACK)
        assert result is FALLBACK


class TestComputeMetrics:
    def _make_df(self, n: int = 10) -> pd.DataFrame:
        import numpy as np
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "asof": [f"202{i % 4}-0{(i % 12) + 1:02d}-30" for i in range(n)],
            "base_mos": rng.uniform(-0.3, 0.3, n),
            "forward_6m_return": rng.uniform(-0.2, 0.2, n),
            "forward_12m_return": rng.uniform(-0.3, 0.3, n),
            "direction_hit_6m": rng.choice([True, False], n),
            "direction_hit_12m": rng.choice([True, False], n),
            "bucket_abs_error_12m": rng.uniform(0, 0.2, n),
            "interval_hit_12m": rng.choice([True, False], n),
        })
        return df

    def test_returns_n_points(self):
        df = self._make_df(10)
        metrics = _compute_metrics(df)
        assert metrics["n_points"] == 10

    def test_suffixed_keys_present(self):
        df = self._make_df(10)
        metrics = _compute_metrics(df, suffix="calibration")
        assert "n_points_calibration" in metrics
        assert "information_coefficient_12m_calibration" in metrics
        assert "hit_rate_12m_calibration" in metrics

    def test_quintile_keys_present(self):
        df = self._make_df(20)
        metrics = _compute_metrics(df)
        for q in range(1, 6):
            assert f"hit_rate_q{q}" in metrics

    def test_empty_df_returns_nan_metrics(self):
        import numpy as np
        df = pd.DataFrame(columns=["base_mos", "forward_6m_return", "forward_12m_return",
                                    "direction_hit_6m", "direction_hit_12m", "bucket_abs_error_12m",
                                    "interval_hit_12m"])
        metrics = _compute_metrics(df)
        assert metrics["n_points"] == 0
        assert math.isnan(metrics["information_coefficient_12m"])

    def test_oos_split_is_60_40(self):
        """Verify calibration subset is first ~60% of sorted dates."""
        import numpy as np
        dates = pd.date_range("2018-03-31", periods=20, freq="QE")
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "asof": [d.date().isoformat() for d in dates],
            "base_mos": rng.uniform(-0.2, 0.2, 20),
            "forward_6m_return": rng.uniform(-0.2, 0.2, 20),
            "forward_12m_return": rng.uniform(-0.2, 0.2, 20),
            "direction_hit_6m": rng.choice([True, False], 20),
            "direction_hit_12m": rng.choice([True, False], 20),
            "bucket_abs_error_12m": rng.uniform(0, 0.2, 20),
            "interval_hit_12m": rng.choice([True, False], 20),
        })
        sorted_asofs = sorted(df["asof"].unique())
        cutoff_idx = max(1, int(len(sorted_asofs) * 0.60))
        cutoff_date = sorted_asofs[cutoff_idx - 1]
        calib_df = df[df["asof"] <= cutoff_date]
        valid_df = df[df["asof"] > cutoff_date]
        # 60% of 20 = 12 calibration, 8 validation
        assert len(calib_df) == 12
        assert len(valid_df) == 8
        # No overlap
        assert len(set(calib_df["asof"]) & set(valid_df["asof"])) == 0
