"""Tests for 3D: H-model terminal value (gradual growth fade)."""
from __future__ import annotations

import math
import pytest
import pandas as pd

from tencent_valuation_v3.dcf import _scenario_value


BASE_FIN = pd.Series(
    {
        "revenue_hkd_bn": 600.0,
        "dep_pct_revenue": 0.04,
        "net_cash_hkd_bn": 300.0,
        "shares_out_bn": 9.4,
        "current_price_hkd": 380.0,
    }
)

BASE_CFG = {
    "terminal_g": 0.025,
    "revenue_growth": [0.08] * 5,
    "ebit_margin": [0.36] * 5,
    "capex_pct_revenue": [0.09] * 5,
    "nwc_pct_revenue": [0.02] * 5,
}


def _run(cfg: dict, method: str, **kwargs) -> dict:
    cfg = {**BASE_CFG, "terminal_value_method": method, **cfg}
    return _scenario_value(
        "test", cfg, years=5, wacc=0.09, tax_rate=0.15, base_fin=BASE_FIN, **kwargs
    )


class TestHModel:
    def test_gordon_growth_is_default(self):
        """Omitting terminal_value_method uses gordon_growth."""
        cfg = dict(BASE_CFG)
        res = _scenario_value(
            "test", cfg, years=5, wacc=0.09, tax_rate=0.15, base_fin=BASE_FIN
        )
        assert res["terminal_value_method"] == "gordon_growth"

    def test_method_stored_in_result(self):
        res = _run({}, method="h_model")
        assert res["terminal_value_method"] == "h_model"

    def test_h_model_higher_than_gordon_when_g_short_gt_g_long(self):
        """H-model TV > Gordon Growth TV when near-term growth > terminal growth."""
        # g_short (last revenue_growth) = 0.08 > terminal_g = 0.025
        # So H-model should produce higher TV → higher fair value
        gg = _run({}, method="gordon_growth")
        hm = _run({"h_model_half_life": 10.0, "h_model_g_short": 0.08}, method="h_model")
        assert hm["fair_value_hkd_per_share"] > gg["fair_value_hkd_per_share"]

    def test_h_model_equals_gordon_when_g_short_equals_g_long(self):
        """H-model collapses to Gordon Growth when g_short == terminal_g."""
        terminal_g = BASE_CFG["terminal_g"]
        gg = _run({}, method="gordon_growth")
        hm = _run(
            {"h_model_g_short": terminal_g, "h_model_half_life": 8.0},
            method="h_model",
        )
        assert math.isclose(
            gg["fair_value_hkd_per_share"],
            hm["fair_value_hkd_per_share"],
            rel_tol=1e-9,
        )

    def test_h_model_half_life_scales_premium(self):
        """Longer half-life → larger H → larger terminal value premium."""
        hm_short = _run({"h_model_g_short": 0.08, "h_model_half_life": 4.0}, method="h_model")
        hm_long = _run({"h_model_g_short": 0.08, "h_model_half_life": 10.0}, method="h_model")
        assert hm_long["fair_value_hkd_per_share"] > hm_short["fair_value_hkd_per_share"]

    def test_h_model_uses_last_revenue_growth_as_default_g_short(self):
        """h_model_g_short defaults to last year's revenue_growth when not specified."""
        cfg_with = {**BASE_CFG, "terminal_value_method": "h_model", "h_model_g_short": BASE_CFG["revenue_growth"][-1]}
        cfg_without = {**BASE_CFG, "terminal_value_method": "h_model"}
        res_with = _scenario_value("t", cfg_with, years=5, wacc=0.09, tax_rate=0.15, base_fin=BASE_FIN)
        res_without = _scenario_value("t", cfg_without, years=5, wacc=0.09, tax_rate=0.15, base_fin=BASE_FIN)
        assert math.isclose(
            res_with["fair_value_hkd_per_share"],
            res_without["fair_value_hkd_per_share"],
            rel_tol=1e-9,
        )

    def test_gordon_growth_explicit(self):
        """Explicit gordon_growth method matches default."""
        default = _scenario_value("t", dict(BASE_CFG), years=5, wacc=0.09, tax_rate=0.15, base_fin=BASE_FIN)
        explicit = _run({}, method="gordon_growth")
        assert math.isclose(
            default["fair_value_hkd_per_share"],
            explicit["fair_value_hkd_per_share"],
            rel_tol=1e-9,
        )
