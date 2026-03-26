"""Tests for 3E: segment-level revenue growth blending."""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from tencent_valuation_v3.dcf import DcfError, _blend_segment_growth


def _make_segment_df(shares: dict[str, float], period: str = "2025-09-30") -> pd.DataFrame:
    """Build a minimal segment_revenue DataFrame from {segment: revenue} dict."""
    total = sum(shares.values())
    rows = [
        {"period": period, "segment": seg, "revenue_hkd_bn": rev, "total_revenue_hkd_bn": total}
        for seg, rev in shares.items()
    ]
    return pd.DataFrame(rows)


class TestBlendSegmentGrowth:
    def test_single_segment_returns_its_growth(self):
        df = _make_segment_df({"VAS": 100.0})
        overrides = {"VAS": [0.08, 0.07, 0.06]}
        result = _blend_segment_growth(df, overrides, years=3)
        assert result == pytest.approx([0.08, 0.07, 0.06])

    def test_equal_weight_two_segments(self):
        df = _make_segment_df({"A": 50.0, "B": 50.0})
        overrides = {"A": [0.10], "B": [0.06]}
        result = _blend_segment_growth(df, overrides, years=1)
        assert result == pytest.approx([0.08])  # (0.10 + 0.06) / 2

    def test_weighted_blend(self):
        # A has 3x the revenue of B → blended ≈ 0.75*A + 0.25*B
        df = _make_segment_df({"A": 75.0, "B": 25.0})
        overrides = {"A": [0.08], "B": [0.04]}
        result = _blend_segment_growth(df, overrides, years=1)
        expected = 0.75 * 0.08 + 0.25 * 0.04
        assert result == pytest.approx([expected])

    def test_partial_override_normalises(self):
        # Only VAS (60%) provided — result normalised to VAS growth
        df = _make_segment_df({"VAS": 60.0, "FinTech": 40.0})
        overrides = {"VAS": [0.08]}
        result = _blend_segment_growth(df, overrides, years=1)
        # total_weight = 0.6; blended[0] = 0.6*0.08 = 0.048; normalised = 0.048/0.6 = 0.08
        assert result == pytest.approx([0.08])

    def test_uses_latest_period(self):
        # Two periods — only the most recent should be used
        rows = [
            {"period": "2024-09-30", "segment": "A", "revenue_hkd_bn": 100.0, "total_revenue_hkd_bn": 200.0},
            {"period": "2024-09-30", "segment": "B", "revenue_hkd_bn": 100.0, "total_revenue_hkd_bn": 200.0},
            {"period": "2025-09-30", "segment": "A", "revenue_hkd_bn": 80.0, "total_revenue_hkd_bn": 100.0},
            {"period": "2025-09-30", "segment": "B", "revenue_hkd_bn": 20.0, "total_revenue_hkd_bn": 100.0},
        ]
        df = pd.DataFrame(rows)
        overrides = {"A": [0.10], "B": [0.02]}
        result = _blend_segment_growth(df, overrides, years=1)
        # 2025: A=80%, B=20% → 0.8*0.10 + 0.2*0.02 = 0.084
        assert result == pytest.approx([0.084])

    def test_unknown_segment_raises(self):
        df = _make_segment_df({"VAS": 100.0})
        with pytest.raises(DcfError, match="no recognised segments"):
            _blend_segment_growth(df, {"NonExistent": [0.08]}, years=3)

    def test_years_shorter_than_path_truncates(self):
        df = _make_segment_df({"VAS": 100.0})
        overrides = {"VAS": [0.10, 0.09, 0.08, 0.07]}
        result = _blend_segment_growth(df, overrides, years=2)
        assert len(result) == 2
        assert result == pytest.approx([0.10, 0.09])

    def test_years_longer_than_path_extends_last_value(self):
        df = _make_segment_df({"VAS": 100.0})
        overrides = {"VAS": [0.10, 0.08]}
        result = _blend_segment_growth(df, overrides, years=4)
        assert result == pytest.approx([0.10, 0.08, 0.08, 0.08])

    def test_real_tencent_segments(self):
        """Spot-check with actual Tencent segment weights."""
        shares = {
            "VAS": 108.77,
            "Marketing Services": 41.12,
            "FinTech and Business Services": 66.01,
            "Others": 2.94,
        }
        df = _make_segment_df(shares)
        overrides = {
            "VAS": [0.06],
            "Marketing Services": [0.12],
            "FinTech and Business Services": [0.10],
            "Others": [0.05],
        }
        result = _blend_segment_growth(df, overrides, years=1)
        total = sum(shares.values())
        expected = (
            108.77 / total * 0.06
            + 41.12 / total * 0.12
            + 66.01 / total * 0.10
            + 2.94 / total * 0.05
        )
        assert result == pytest.approx([expected], rel=1e-6)
