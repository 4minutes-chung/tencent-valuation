"""Tests for _resolve_rf — Phase 2B."""
from __future__ import annotations

import math
import unittest

import pandas as pd

from tencent_valuation_v3.wacc import _resolve_rf


def _make_monthly(rf_values: list[float]) -> pd.DataFrame:
    n = len(rf_values)
    dates = pd.date_range("2020-01-01", periods=n, freq="MS")
    return pd.DataFrame(
        {
            "date": dates,
            "RF": rf_values,
            "MKT_EXCESS": [0.004] * n,
            "SMB": [0.001] * n,
            "HML": [0.001] * n,
        }
    )


class TestResolveRf(unittest.TestCase):
    def setUp(self) -> None:
        # Increasing RF values so last != mean
        self.rf_values = [0.001 + i * 0.0001 for i in range(60)]
        self.window = _make_monthly(self.rf_values)

    def test_current_10y_returns_last_obs_times_12(self) -> None:
        cfg = {"rf_method": "current_10y"}
        result = _resolve_rf(self.window, cfg)
        expected = self.rf_values[-1] * 12.0
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_current_10y_differs_from_rolling_mean(self) -> None:
        cfg_current = {"rf_method": "current_10y"}
        cfg_rolling = {"rf_method": "rolling_mean"}
        r_current = _resolve_rf(self.window, cfg_current)
        r_rolling = _resolve_rf(self.window, cfg_rolling)
        # With increasing series, last > mean → current > rolling
        self.assertGreater(r_current, r_rolling)

    def test_rolling_mean_returns_mean_times_12(self) -> None:
        cfg = {"rf_method": "rolling_mean"}
        result = _resolve_rf(self.window, cfg)
        expected = float(pd.Series(self.rf_values).mean() * 12.0)
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_default_method_is_rolling_mean(self) -> None:
        cfg: dict = {}  # no rf_method key
        result = _resolve_rf(self.window, cfg)
        expected = float(pd.Series(self.rf_values).mean() * 12.0)
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_current_10y_uses_last_row_exactly(self) -> None:
        # Flat except for last observation
        rf_vals = [0.002] * 59 + [0.010]
        window = _make_monthly(rf_vals)
        cfg = {"rf_method": "current_10y"}
        result = _resolve_rf(window, cfg)
        self.assertTrue(math.isclose(result, 0.010 * 12.0, rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
