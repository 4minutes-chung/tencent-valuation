"""Phase 1C — Residual income must not double-count net cash.

The Edwards-Bell-Ohlson identity is:
    equity = book0 + PV(explicit RIs) + PV(terminal RI)

Net cash is already embedded in book0 (reported equity includes cash).
Adding it again was the old bug.  This test:
  1. Verifies equity matches the EBO identity from the output columns.
  2. Verifies that when book_value_hkd_bn is supplied directly, it is used
     rather than the proxy (0.42 * revenue + net_cash).
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v3.pipeline import run_all


_ASOF = "2026-02-19"
_SHARES = 9.1
_NET_CASH = 120.0
_BOOK_VALUE = 550.0  # supplied directly — must not add net_cash again


def _write_overrides(tmp: Path, asof: str, include_book_value: bool = True) -> None:
    raw = tmp / "data" / "raw" / asof
    raw.mkdir(parents=True, exist_ok=True)

    row: dict = {
        "asof": asof,
        "revenue_hkd_bn": 760.0,
        "ebit_margin": 0.35,
        "capex_pct_revenue": 0.10,
        "nwc_pct_revenue": 0.02,
        "dep_pct_revenue": 0.03,
        "net_cash_hkd_bn": _NET_CASH,
        "shares_out_bn": _SHARES,
        "current_price_hkd": 500.0,
        "fundamentals_source": "override_csv",
    }
    if include_book_value:
        row["book_value_hkd_bn"] = _BOOK_VALUE

    pd.DataFrame([row]).to_csv(raw / "tencent_financials.csv", index=False)


class TestRiNoDoubleCount(unittest.TestCase):
    def _run(self, include_book_value: bool) -> pd.DataFrame:
        repo_root = Path(__file__).resolve().parents[1]
        tmp = Path(tempfile.mkdtemp())
        shutil.copytree(repo_root / "config", tmp / "config")
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        _write_overrides(tmp, _ASOF, include_book_value=include_book_value)
        payload = run_all(_ASOF, project_root=tmp, refresh=True, source_mode="synthetic")
        return pd.read_csv(payload["residual_income_outputs"])

    def test_ebo_identity_holds(self) -> None:
        """equity_value_hkd_bn == book_value_open + pv_ri + pv_terminal_ri."""
        ri = self._run(include_book_value=True)
        for _, row in ri.iterrows():
            expected = (
                float(row["book_value_open_hkd_bn"])
                + float(row["pv_residual_income_hkd_bn"])
                + float(row["pv_terminal_residual_income_hkd_bn"])
            )
            actual = float(row["equity_value_hkd_bn"])
            self.assertAlmostEqual(
                actual,
                expected,
                places=3,
                msg=f"EBO identity failed for scenario={row['scenario']}: {actual:.4f} != {expected:.4f}",
            )

    def test_uses_actual_book_value(self) -> None:
        """When book_value_hkd_bn is in the override, book0 must equal it exactly."""
        ri = self._run(include_book_value=True)
        for _, row in ri.iterrows():
            self.assertAlmostEqual(
                float(row["book_value_open_hkd_bn"]),
                _BOOK_VALUE,
                places=2,
                msg=f"Expected book0={_BOOK_VALUE}, got {row['book_value_open_hkd_bn']} for {row['scenario']}",
            )

    def test_net_cash_not_added_twice(self) -> None:
        """Equity from RI with explicit book value must not exceed EBO by ~net_cash * 0.20."""
        ri_with_book = self._run(include_book_value=True)
        ri_proxy = self._run(include_book_value=False)

        for scenario in ["base", "bad", "extreme"]:
            eq_with = float(ri_with_book.loc[ri_with_book["scenario"] == scenario, "equity_value_hkd_bn"].iloc[0])
            eq_proxy = float(ri_proxy.loc[ri_proxy["scenario"] == scenario, "equity_value_hkd_bn"].iloc[0])
            # Old bug would inflate by net_cash * 0.20 = 24.0 HKD bn.
            # The two variants legitimately differ (different book0), but neither
            # should be inflated by a spurious 0.20 * net_cash addend beyond EBO.
            # Check that both variants satisfy EBO identity.
            book0_with = float(
                ri_with_book.loc[ri_with_book["scenario"] == scenario, "book_value_open_hkd_bn"].iloc[0]
            )
            pv_ri_with = float(
                ri_with_book.loc[ri_with_book["scenario"] == scenario, "pv_residual_income_hkd_bn"].iloc[0]
            )
            pv_tv_with = float(
                ri_with_book.loc[
                    ri_with_book["scenario"] == scenario, "pv_terminal_residual_income_hkd_bn"
                ].iloc[0]
            )
            self.assertAlmostEqual(
                eq_with,
                book0_with + pv_ri_with + pv_tv_with,
                places=3,
                msg=f"EBO identity failed for explicit-book scenario={scenario}",
            )

            book0_proxy = float(
                ri_proxy.loc[ri_proxy["scenario"] == scenario, "book_value_open_hkd_bn"].iloc[0]
            )
            pv_ri = float(
                ri_proxy.loc[ri_proxy["scenario"] == scenario, "pv_residual_income_hkd_bn"].iloc[0]
            )
            pv_tv = float(
                ri_proxy.loc[ri_proxy["scenario"] == scenario, "pv_terminal_residual_income_hkd_bn"].iloc[0]
            )
            self.assertAlmostEqual(
                eq_proxy,
                book0_proxy + pv_ri + pv_tv,
                places=3,
                msg=f"EBO identity failed for proxy scenario={scenario}",
            )


if __name__ == "__main__":
    unittest.main()
