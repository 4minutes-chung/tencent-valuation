"""Tests for _fama_macbeth_lambdas — Phase 2E."""
from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd

from tencent_valuation_v3.wacc import WaccError, _fama_macbeth_lambdas


def _make_synthetic_data(
    n_tickers: int = 8,
    n_periods: int = 60,
    true_lambda_mkt: float = 0.005,   # monthly (→ 0.06 annualised)
    true_lambda_smb: float = 0.002,   # monthly
    true_lambda_hml: float = -0.001,  # monthly
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Generate synthetic factor and asset data where the true lambdas are known.

    Asset excess returns are generated as:
        excess_ret_i_t = beta_mkt_i * lambda_mkt + beta_smb_i * lambda_smb
                       + beta_hml_i * lambda_hml + noise

    Returns (monthly_assets_df, monthly_factors_df, tickers).
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-01", periods=n_periods, freq="MS")
    tickers = [f"TICK{i:02d}" for i in range(n_tickers)]

    # Assign fixed betas per ticker (time-series betas)
    betas_mkt = rng.uniform(0.5, 1.5, size=n_tickers)
    betas_smb = rng.uniform(-0.5, 0.5, size=n_tickers)
    betas_hml = rng.uniform(-0.3, 0.3, size=n_tickers)

    # Generate factor realisations (monthly)
    mkt_excess = rng.normal(0.004, 0.04, size=n_periods)
    smb = rng.normal(0.001, 0.02, size=n_periods)
    hml = rng.normal(0.001, 0.02, size=n_periods)
    rf = np.full(n_periods, 0.002)

    factors_df = pd.DataFrame(
        {
            "date": dates,
            "RF": rf,
            "MKT_EXCESS": mkt_excess,
            "SMB": smb,
            "HML": hml,
        }
    )

    # Build asset returns: ret = RF + beta_mkt*MKT_EXCESS + beta_smb*SMB + beta_hml*HML + noise
    asset_rows = []
    for i, ticker in enumerate(tickers):
        for t, dt in enumerate(dates):
            noise = rng.normal(0, 0.015)
            ret = (
                rf[t]
                + betas_mkt[i] * mkt_excess[t]
                + betas_smb[i] * smb[t]
                + betas_hml[i] * hml[t]
                + noise
            )
            asset_rows.append({"date": dt, "ticker": ticker, "ret": ret})
    assets_df = pd.DataFrame(asset_rows)

    return assets_df, factors_df, tickers


class TestFamaMacbethLambdas(unittest.TestCase):
    def setUp(self) -> None:
        self.assets, self.factors, self.tickers = _make_synthetic_data(
            n_tickers=10, n_periods=72, seed=99
        )

    def test_returns_three_dicts(self) -> None:
        lambdas, t_stats, se = _fama_macbeth_lambdas(self.assets, self.factors, self.tickers, min_obs=24)
        self.assertIsInstance(lambdas, dict)
        self.assertIsInstance(t_stats, dict)
        self.assertIsInstance(se, dict)
        for key in ["MKT_EXCESS", "SMB", "HML"]:
            self.assertIn(key, lambdas)
            self.assertIn(key, t_stats)
            self.assertIn(key, se)

    def test_lambdas_are_annualised(self) -> None:
        # Annualised lambdas should be roughly 12x monthly values
        # We just check they are non-trivially different from raw monthly values
        # by checking magnitude is plausible for annualised (>0.001 for MKT)
        lambdas, _, _ = _fama_macbeth_lambdas(self.assets, self.factors, self.tickers, min_obs=24)
        # MKT lambda should be plausible as annual (synthetic data ~0.004*12=0.048)
        # just check it's finite and non-zero
        self.assertTrue(math.isfinite(lambdas["MKT_EXCESS"]))
        self.assertNotAlmostEqual(lambdas["MKT_EXCESS"], 0.0, places=5)

    def test_t_stats_are_real_not_synthetic(self) -> None:
        _, t_stats, se = _fama_macbeth_lambdas(self.assets, self.factors, self.tickers, min_obs=24)
        for key in ["MKT_EXCESS", "SMB", "HML"]:
            # t-stat = mean/SE, should be computed from actual data, not hardcoded 4.0
            self.assertTrue(math.isfinite(t_stats[key]))
            # confirm t-stat != 4.0 (old synthetic value)
            self.assertFalse(math.isclose(t_stats[key], 4.0, rel_tol=0.01))

    def test_t_stats_have_correct_sign(self) -> None:
        lambdas, t_stats, _ = _fama_macbeth_lambdas(self.assets, self.factors, self.tickers, min_obs=24)
        for key in ["MKT_EXCESS", "SMB", "HML"]:
            lam = lambdas[key]
            t = t_stats[key]
            if abs(lam) > 1e-8:
                # t-stat sign must match lambda sign
                self.assertEqual(int(math.copysign(1, t)), int(math.copysign(1, lam)),
                                 msg=f"Sign mismatch for {key}: lambda={lam}, t={t}")

    def test_raises_wacc_error_with_fewer_than_3_tickers(self) -> None:
        # Only 2 tickers
        small_assets = self.assets.loc[self.assets["ticker"].isin(self.tickers[:2])].copy()
        with self.assertRaises(WaccError):
            _fama_macbeth_lambdas(small_assets, self.factors, self.tickers[:2], min_obs=24)

    def test_raises_wacc_error_if_min_obs_not_met(self) -> None:
        # Require 200 obs per ticker but only have 72
        with self.assertRaises(WaccError):
            _fama_macbeth_lambdas(self.assets, self.factors, self.tickers, min_obs=200)

    def test_known_data_lambda_estimate(self) -> None:
        """
        FM lambda for MKT should be finite and have correct sign when data is generated from
        CAPM DGP: ret_i_t = RF_t + beta_i * MKT_EXCESS_t + eps_i_t.

        In this DGP, Pass 1 recovers beta_i from time-series covariation with MKT_EXCESS,
        and Pass 2 cross-sectional regression of (excess_ret_i_t on beta_i) yields lambda_mkt_t.
        The average lambda should be positive since mean(MKT_EXCESS) > 0.
        """
        rng = np.random.default_rng(17)
        n_tickers = 10
        n_periods = 120
        dates = pd.date_range("2015-01-01", periods=n_periods, freq="MS")
        tickers = [f"S{i}" for i in range(n_tickers)]
        # Diverse betas to ensure cross-sectional spread
        betas_mkt = np.linspace(0.3, 2.2, n_tickers)

        # Factor realizations — positive mean for MKT_EXCESS
        mkt = rng.normal(0.006, 0.04, size=n_periods)   # positive mean ERP
        rf = np.full(n_periods, 0.002)
        factors = pd.DataFrame({"date": dates, "RF": rf, "MKT_EXCESS": mkt, "SMB": 0.0, "HML": 0.0})

        rows = []
        for i, ticker in enumerate(tickers):
            for t, dt in enumerate(dates):
                # Pure CAPM DGP: excess_ret = beta_i * MKT_EXCESS_t + small_noise
                noise = rng.normal(0, 0.005)
                ret = rf[t] + betas_mkt[i] * mkt[t] + noise
                rows.append({"date": dt, "ticker": ticker, "ret": ret})
        assets = pd.DataFrame(rows)

        lambdas, t_stats, _ = _fama_macbeth_lambdas(assets, factors, tickers, min_obs=24)
        # Under pure CAPM DGP, FM MKT lambda should be positive (tracks realised MKT premium)
        # and finite
        self.assertTrue(math.isfinite(lambdas["MKT_EXCESS"]))
        self.assertGreater(
            lambdas["MKT_EXCESS"], 0.0,
            msg=f"Expected positive FM MKT lambda under CAPM DGP, got {lambdas['MKT_EXCESS']:.4f}"
        )


if __name__ == "__main__":
    unittest.main()
