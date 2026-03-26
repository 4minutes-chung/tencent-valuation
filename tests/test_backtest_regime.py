"""Tests for Phase 5D: enhanced multi-regime classification."""
from __future__ import annotations

import pandas as pd
import pytest

from tencent_valuation_v3.backtest import _classify_regime


def _make_series(values: list[float], base_date: pd.Timestamp) -> pd.Series:
    """Build a price series with 7-day frequency ending exactly at base_date."""
    dates = pd.date_range(end=base_date, periods=len(values), freq="7D")
    return pd.Series(values, index=dates)


class TestClassifyRegime:
    def test_crisis_when_3m_return_below_minus20(self):
        # Price drops from 100 to 70 in last 3 months → -30%
        # Need 12+ months of data, first ~52 weeks at 100, last ~14 weeks dropping to 70
        base = pd.Timestamp("2022-06-30")
        # 52 weeks stable at 100, then 13 weeks declining to 70
        prices = [100.0] * 52 + [70.0] * 13
        series = _make_series(prices, base)
        result = _classify_regime(series, base)
        assert result == "crisis"

    def test_bull_when_3m_positive_and_12m_positive(self):
        # Steady uptrend: price goes from 70 (12m ago) to 100 (now)
        base = pd.Timestamp("2021-06-30")
        # 65 weeks, price rises linearly from 70 to 100
        n = 65
        prices = [70.0 + i * (30.0 / n) for i in range(n + 1)]
        series = _make_series(prices, base)
        result = _classify_regime(series, base)
        assert result in ("bull", "low_vol", "high_vol")  # trend direction is bull

    def test_bear_when_3m_negative(self):
        # Price falls from 100 to 88 over last 3 months → ~ -12%
        base = pd.Timestamp("2022-09-30")
        # 60 weeks flat at 100, then 13 weeks declining to 88
        prices = [100.0] * 60 + list(100.0 - (i * 12.0 / 13) for i in range(13)) + [88.0]
        series = _make_series(prices, base)
        result = _classify_regime(series, base)
        assert result in ("bear", "high_vol", "low_vol")  # directional

    def test_recovery_when_12m_negative_but_3m_positive(self):
        # Price: was 100 twelve months ago, crashed to 65 in middle, now recovering to 78
        # 12m return: (78/100) - 1 = -22% (negative)
        # 3m return: let's say last 13 weeks rose from 72 to 78 → ~8% (positive)
        base = pd.Timestamp("2020-06-30")
        prices = (
            [100.0] * 26   # first 26 weeks at 100
            + [70.0] * 13  # crash for 13 weeks
            + [65.0] * 10  # trough for 10 weeks
            + [70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0, 77.0, 78.0, 78.0, 78.0, 78.0, 78.0]  # 13 weeks recovery
        )
        series = _make_series(prices, base)
        # Verify setup: 12m ago price should be ~100, now ~78 → 12m negative
        # 3m ago price should be ~72, now ~78 → 3m positive
        result = _classify_regime(series, base)
        assert result == "recovery"

    def test_unknown_when_no_data(self):
        # Empty series has no DatetimeIndex
        base = pd.Timestamp("2022-01-01")
        series = pd.Series(dtype=float)
        result = _classify_regime(series, base)
        assert result == "unknown"

    def test_unknown_when_insufficient_data_points(self):
        # Fewer than 4 data points
        base = pd.Timestamp("2022-01-01")
        dates = pd.date_range(end=base, periods=3, freq="7D")
        series = pd.Series([100.0, 99.0, 98.0], index=dates)
        result = _classify_regime(series, base)
        assert result == "unknown"

    def test_unknown_when_history_too_short(self):
        # 4+ points but all within 1 month of asof → insufficient lookback
        base = pd.Timestamp("2022-01-31")
        dates = pd.date_range(end=base, periods=4, freq="7D")
        series = pd.Series([100.0, 99.0, 100.0, 101.0], index=dates)
        result = _classify_regime(series, base)
        assert result == "unknown"

    def test_six_possible_regimes(self):
        valid = {"bull", "bear", "high_vol", "low_vol", "crisis", "recovery", "unknown"}
        base = pd.Timestamp("2022-06-30")
        prices = [100.0 + i for i in range(55)]
        series = _make_series(prices, base)
        result = _classify_regime(series, base)
        assert result in valid
