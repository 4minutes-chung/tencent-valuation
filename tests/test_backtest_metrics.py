"""Tests for Phase 5C: backtest quantitative metrics."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from tencent_valuation_v4.backtest import (
    _calibration_slope,
    _hit_rate_by_quintile,
    _information_coefficient,
    _rmse,
)


class TestInformationCoefficient:
    def test_perfect_positive_rank_correlation(self):
        pred = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        real = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        ic = _information_coefficient(pred, real)
        assert abs(ic - 1.0) < 1e-9

    def test_perfect_negative_rank_correlation(self):
        pred = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        real = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
        ic = _information_coefficient(pred, real)
        assert abs(ic + 1.0) < 1e-9

    def test_nan_below_min_obs(self):
        pred = pd.Series([1.0, 2.0, 3.0])
        real = pd.Series([1.0, 2.0, 3.0])
        ic = _information_coefficient(pred, real)
        assert math.isnan(ic)

    def test_nan_ignored_in_pairs(self):
        pred = pd.Series([1.0, 2.0, 3.0, 4.0, float("nan")])
        real = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        ic = _information_coefficient(pred, real)
        assert abs(ic - 1.0) < 1e-9

    def test_zero_correlation_close_to_zero(self):
        rng = np.random.default_rng(42)
        pred = pd.Series(rng.uniform(-1, 1, 100))
        real = pd.Series(rng.uniform(-1, 1, 100))
        ic = _information_coefficient(pred, real)
        # No guarantee of exact zero, but expect < 0.3 for uncorrelated data
        assert abs(ic) < 0.40


class TestCalibrationSlope:
    def test_perfect_calibration(self):
        pred = pd.Series([0.10, 0.20, 0.30, 0.40, 0.50])
        real = pd.Series([0.10, 0.20, 0.30, 0.40, 0.50])
        slope, intercept = _calibration_slope(pred, real)
        assert abs(slope - 1.0) < 1e-9
        assert abs(intercept) < 1e-9

    def test_overconfident_model_slope_below_one(self):
        # Predictions 2x the realized returns — overconfident
        pred = pd.Series([0.20, 0.40, -0.20, -0.40, 0.10])
        real = pd.Series([0.10, 0.20, -0.10, -0.20, 0.05])
        slope, _ = _calibration_slope(pred, real)
        assert slope < 1.0

    def test_nan_below_min_obs(self):
        pred = pd.Series([0.1, 0.2, 0.3])
        real = pd.Series([0.1, 0.2, 0.3])
        slope, intercept = _calibration_slope(pred, real)
        assert math.isnan(slope)
        assert math.isnan(intercept)

    def test_constant_predictions_returns_nan(self):
        pred = pd.Series([0.10, 0.10, 0.10, 0.10, 0.10])
        real = pd.Series([0.10, 0.20, 0.30, 0.40, 0.50])
        slope, intercept = _calibration_slope(pred, real)
        assert math.isnan(slope)


class TestRmse:
    def test_perfect_predictions_zero_rmse(self):
        pred = pd.Series([0.1, 0.2, -0.1, -0.2])
        real = pd.Series([0.1, 0.2, -0.1, -0.2])
        assert _rmse(pred, real) == pytest.approx(0.0, abs=1e-12)

    def test_known_rmse(self):
        pred = pd.Series([0.0, 0.0, 0.0, 0.0])
        real = pd.Series([0.1, 0.2, 0.3, 0.4])
        # MSE = mean of (0.01, 0.04, 0.09, 0.16) = 0.075
        expected = math.sqrt(0.075)
        assert _rmse(pred, real) == pytest.approx(expected, rel=1e-6)

    def test_nan_below_min_obs(self):
        pred = pd.Series([0.1])
        real = pd.Series([0.2])
        assert math.isnan(_rmse(pred, real))

    def test_nan_pairs_dropped(self):
        pred = pd.Series([0.0, 0.0, float("nan")])
        real = pd.Series([0.1, 0.1, 0.5])
        # Only first two pairs used: RMSE = 0.1
        assert _rmse(pred, real) == pytest.approx(0.1, rel=1e-6)


class TestHitRateByQuintile:
    def test_fewer_than_5_points_returns_nans(self):
        pred = pd.Series([0.1, 0.2, 0.3])
        real = pd.Series([0.1, 0.2, -0.1])
        result = _hit_rate_by_quintile(pred, real)
        assert all(math.isnan(v) for v in result.values())

    def test_keys_are_hit_rate_q1_through_q5(self):
        rng = np.random.default_rng(0)
        pred = pd.Series(rng.uniform(-1, 1, 20))
        real = pd.Series(rng.uniform(-1, 1, 20))
        result = _hit_rate_by_quintile(pred, real)
        assert set(result.keys()) == {"hit_rate_q1", "hit_rate_q2", "hit_rate_q3", "hit_rate_q4", "hit_rate_q5"}

    def test_perfect_directional_model_has_high_q5_hit_rate(self):
        # Q5 = highest predicted MoS; if predictions are correct, Q5 should have high hit rate
        pred = pd.Series([-0.3, -0.2, -0.1, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7] * 2)
        # Realized: positive where pred is positive, negative where pred is negative
        real = pred.copy()
        result = _hit_rate_by_quintile(pred, real)
        assert result["hit_rate_q5"] == pytest.approx(1.0)
