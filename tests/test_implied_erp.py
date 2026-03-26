"""Tests for _resolve_erp — Phase 2A."""
from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd

from tencent_valuation_v3.wacc import _resolve_erp


def _make_monthly(mkt_excess_values: list[float], rf_values: list[float]) -> pd.DataFrame:
    n = len(mkt_excess_values)
    dates = pd.date_range("2020-01-01", periods=n, freq="MS")
    return pd.DataFrame(
        {
            "date": dates,
            "MKT_EXCESS": mkt_excess_values,
            "RF": rf_values,
            "SMB": [0.001] * n,
            "HML": [0.001] * n,
        }
    )


class TestResolveErp(unittest.TestCase):
    def setUp(self) -> None:
        # Monthly excess returns ~ 0.4% → annualised 4.8% rolling
        self.monthly_values = [0.004] * 60
        self.rf_values = [0.002] * 60
        self.window = _make_monthly(self.monthly_values, self.rf_values)
        self.implied_erp = 0.055

    def test_implied_method_returns_config_default(self) -> None:
        cfg = {"erp_method": "implied", "implied_erp_default": self.implied_erp}
        result = _resolve_erp(self.window, cfg)
        self.assertTrue(math.isclose(result, self.implied_erp, rel_tol=1e-12))

    def test_implied_method_uses_fallback_when_key_missing(self) -> None:
        cfg = {"erp_method": "implied"}  # no implied_erp_default key
        result = _resolve_erp(self.window, cfg)
        # default fallback is 0.055 in code
        self.assertTrue(math.isclose(result, 0.055, rel_tol=1e-12))

    def test_blend_method_is_midpoint(self) -> None:
        cfg = {"erp_method": "blend", "implied_erp_default": self.implied_erp}
        result = _resolve_erp(self.window, cfg)
        rolling = float(np.mean(self.monthly_values) * 12)
        expected = 0.5 * self.implied_erp + 0.5 * rolling
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-9))

    def test_blend_is_between_implied_and_rolling(self) -> None:
        cfg = {"erp_method": "blend", "implied_erp_default": self.implied_erp}
        result = _resolve_erp(self.window, cfg)
        rolling = float(np.mean(self.monthly_values) * 12)
        lo = min(self.implied_erp, rolling)
        hi = max(self.implied_erp, rolling)
        self.assertGreaterEqual(result, lo - 1e-12)
        self.assertLessEqual(result, hi + 1e-12)

    def test_rolling_excess_return_matches_mean_times_12(self) -> None:
        cfg = {"erp_method": "rolling_excess_return"}
        result = _resolve_erp(self.window, cfg)
        expected = float(np.mean(self.monthly_values) * 12)
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_default_method_is_rolling_excess_return(self) -> None:
        cfg: dict = {}  # no erp_method key
        result = _resolve_erp(self.window, cfg)
        expected = float(np.mean(self.monthly_values) * 12)
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_unknown_method_falls_back_to_rolling(self) -> None:
        cfg = {"erp_method": "unknown_value"}
        result = _resolve_erp(self.window, cfg)
        expected = float(np.mean(self.monthly_values) * 12)
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
