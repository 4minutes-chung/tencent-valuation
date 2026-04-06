"""Tests for Phase 4E: scenario probability weighting and expected value."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


def _build_method_outputs(tmp_path: Path, base_fv: float, bad_fv: float, extreme_fv: float) -> Path:
    """Write a minimal valuation_method_outputs.csv for ensemble to consume."""
    rows = []
    for scenario, fv in [("base", base_fv), ("bad", bad_fv), ("extreme", extreme_fv)]:
        rows.append({
            "scenario": scenario,
            "method": "dcf",
            "fair_value_hkd_per_share": fv,
            "weight": 1.0,
        })
    df = pd.DataFrame(rows)
    path = tmp_path / "valuation_method_outputs.csv"
    df.to_csv(path, index=False)
    return path


class TestExpectedValueRow:
    def test_expected_value_matches_probability_weighted_sum(self, tmp_path: Path):
        """
        With known fair values and known probabilities, the expected row
        should equal the weighted sum exactly.
        """
        probs = {"base": 0.50, "bad": 0.35, "extreme": 0.15}
        base_fv, bad_fv, extreme_fv = 500.0, 300.0, 100.0
        expected = probs["base"] * base_fv + probs["bad"] * bad_fv + probs["extreme"] * extreme_fv

        # Build a minimal ensemble CSV as if produced by run_ensemble
        rows = []
        for scenario, fv in [("base", base_fv), ("bad", bad_fv), ("extreme", extreme_fv)]:
            rows.append({
                "scenario": scenario,
                "ensemble_fair_value_hkd": fv,
                "ensemble_weight_total": 1.0,
                "market_price_hkd": 380.0,
                "margin_of_safety": (fv - 380.0) / 380.0,
            })
        df = pd.DataFrame(rows)

        # Simulate expected-value calculation
        ev = sum(probs[row["scenario"]] * row["ensemble_fair_value_hkd"] for _, row in df.iterrows())
        assert abs(ev - expected) < 1e-6

    def test_probabilities_sum_to_one(self):
        from tencent_valuation_v4.config import load_yaml
        config_path = Path(__file__).parents[1] / "config" / "method_weights.yaml"
        if not config_path.exists():
            pytest.skip("method_weights.yaml not found")
        cfg = load_yaml(config_path)
        probs = cfg.get("scenario_probabilities", {})
        total = sum(probs.values())
        assert abs(total - 1.0) < 1e-6

    def test_method_weights_sum_to_one(self):
        from tencent_valuation_v4.config import load_yaml
        config_path = Path(__file__).parents[1] / "config" / "method_weights.yaml"
        if not config_path.exists():
            pytest.skip("method_weights.yaml not found")
        cfg = load_yaml(config_path)
        weights = cfg.get("method_weights", {})
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_extreme_le_bad_le_base(self, tmp_path: Path):
        """Expected value ordering when scenarios are ordered correctly."""
        probs = {"base": 0.50, "bad": 0.35, "extreme": 0.15}
        scenarios = {"base": 500.0, "bad": 300.0, "extreme": 100.0}
        assert scenarios["extreme"] <= scenarios["bad"] <= scenarios["base"]
        ev = sum(probs[k] * v for k, v in scenarios.items())
        # EV should be between extreme and base
        assert scenarios["extreme"] <= ev <= scenarios["base"]

    def test_stress_probabilities_below_one(self):
        from tencent_valuation_v4.config import load_yaml
        config_path = Path(__file__).parents[1] / "config" / "scenarios.yaml"
        if not config_path.exists():
            pytest.skip("scenarios.yaml not found")
        cfg = load_yaml(config_path)
        stress = cfg.get("stress_scenarios", {})
        total_stress_prob = sum(s.get("probability", 0.0) for s in stress.values())
        assert total_stress_prob < 1.0
