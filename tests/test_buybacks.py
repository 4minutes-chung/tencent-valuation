"""Tests for 3F: share buyback modeling."""
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
        "current_price_hkd": 400.0,
    }
)

BASE_CFG = {
    "terminal_g": 0.025,
    "revenue_growth": [0.08] * 5,
    "ebit_margin": [0.36] * 5,
    "capex_pct_revenue": [0.09] * 5,
    "nwc_pct_revenue": [0.02] * 5,
}

YEARS = 5
WACC = 0.09
TAX = 0.15


def _run(buyback: float) -> dict:
    cfg = {**BASE_CFG, "annual_buyback_hkd_bn": buyback}
    return _scenario_value("test", cfg, years=YEARS, wacc=WACC, tax_rate=TAX, base_fin=BASE_FIN)


class TestBuybacks:
    def test_no_buyback_is_default(self):
        """Omitting annual_buyback_hkd_bn is equivalent to zero buyback."""
        no_buyback_cfg = dict(BASE_CFG)
        res_default = _scenario_value("t", no_buyback_cfg, years=YEARS, wacc=WACC, tax_rate=TAX, base_fin=BASE_FIN)
        res_zero = _run(0.0)
        assert math.isclose(res_default["fair_value_hkd_per_share"], res_zero["fair_value_hkd_per_share"])
        assert res_zero["total_buyback_hkd_bn"] == pytest.approx(0.0)
        assert res_zero["shares_retired_bn"] == pytest.approx(0.0)

    def test_total_buyback_equals_annual_times_years(self):
        res = _run(40.0)
        assert res["total_buyback_hkd_bn"] == pytest.approx(40.0 * YEARS)

    def test_shares_retired_equals_buyback_over_price(self):
        annual = 40.0
        res = _run(annual)
        expected_retired = (annual * YEARS) / float(BASE_FIN["current_price_hkd"])
        assert res["shares_retired_bn"] == pytest.approx(expected_retired)

    def test_buyback_accretive_when_price_below_intrinsic(self):
        """Buybacks are accretive when market price << intrinsic value (retiring cheap shares)."""
        # Use market_price=100 — well below intrinsic value — so retiring shares at 100
        # while they're worth more is strictly value-creating per remaining share.
        cheap_fin = BASE_FIN.copy()
        cheap_fin["current_price_hkd"] = 100.0
        cfg_no = dict(BASE_CFG)
        cfg_bb = {**BASE_CFG, "annual_buyback_hkd_bn": 40.0}
        no_bb = _scenario_value("t", cfg_no, years=YEARS, wacc=WACC, tax_rate=TAX, base_fin=cheap_fin)
        with_bb = _scenario_value("t", cfg_bb, years=YEARS, wacc=WACC, tax_rate=TAX, base_fin=cheap_fin)
        assert with_bb["fair_value_hkd_per_share"] > no_bb["fair_value_hkd_per_share"]

    def test_buyback_dilutive_when_price_above_intrinsic(self):
        """Buybacks are dilutive when market price >> intrinsic value (overpaying for shares)."""
        # current BASE_FIN has market_price=400 but fair_value≈355 → dilutive
        no_bb = _run(0.0)
        with_bb = _run(40.0)
        assert with_bb["fair_value_hkd_per_share"] < no_bb["fair_value_hkd_per_share"]

    def test_net_cash_reduced_by_total_buyback(self):
        """equity = enterprise + (net_cash - total_buyback)."""
        annual = 30.0
        res = _run(annual)
        total_bb = annual * YEARS
        expected_equity = res["enterprise_value_hkd_bn"] + (float(BASE_FIN["net_cash_hkd_bn"]) - total_bb)
        assert res["equity_value_hkd_bn"] == pytest.approx(expected_equity)

    def test_fair_value_consistent_with_equity_and_shares(self):
        """fair_value = equity / final_shares."""
        annual = 25.0
        res = _run(annual)
        total_bb = annual * YEARS
        retired = total_bb / float(BASE_FIN["current_price_hkd"])
        final_shares = float(BASE_FIN["shares_out_bn"]) - retired
        expected_fv = res["equity_value_hkd_bn"] / final_shares
        assert res["fair_value_hkd_per_share"] == pytest.approx(expected_fv)

    def test_larger_buyback_retires_more_shares(self):
        small = _run(10.0)
        large = _run(50.0)
        assert large["shares_retired_bn"] > small["shares_retired_bn"]

    def test_result_keys_present(self):
        res = _run(20.0)
        assert "total_buyback_hkd_bn" in res
        assert "shares_retired_bn" in res
