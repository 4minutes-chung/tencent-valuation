"""Tests for vasicek_adjust and blume_adjust — Phase 2D."""
from __future__ import annotations

import math
import unittest

from tencent_valuation_v3.wacc import blume_adjust, vasicek_adjust


class TestVasicekAdjust(unittest.TestCase):
    def test_hand_calculation(self) -> None:
        # w = 0.16 / (0.16 + 0.0625) = 0.16 / 0.2225 = 0.71910...
        # result = 0.71910 * 1.5 + (1 - 0.71910) * 1.0 = 1.07865 + 0.28090 = 1.35955
        beta_raw = 1.5
        prior = 1.0
        se = 0.25
        pv = 0.16
        w = pv / (pv + se ** 2)
        expected = w * beta_raw + (1.0 - w) * prior
        result = vasicek_adjust(beta_raw, beta_prior=prior, se_beta=se, prior_variance=pv)
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_hand_calculation_specific_value(self) -> None:
        # Explicit numeric check matching spec
        # w = 0.16 / (0.16 + 0.0625) = 0.7191011...
        # result = 0.7191 * 1.5 + 0.2809 * 1.0 = 1.3596...
        result = vasicek_adjust(1.5, beta_prior=1.0, se_beta=0.25, prior_variance=0.16)
        w = 0.16 / (0.16 + 0.25 ** 2)
        expected = w * 1.5 + (1.0 - w) * 1.0
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-10))
        # roughly 1.359...
        self.assertGreater(result, 1.35)
        self.assertLess(result, 1.37)

    def test_shrinks_high_beta_toward_prior(self) -> None:
        beta_raw = 2.0
        prior = 1.0
        result = vasicek_adjust(beta_raw, beta_prior=prior)
        self.assertLess(result, beta_raw)
        self.assertGreater(result, prior)

    def test_shrinks_low_beta_toward_prior(self) -> None:
        beta_raw = 0.3
        prior = 1.0
        result = vasicek_adjust(beta_raw, beta_prior=prior)
        self.assertGreater(result, beta_raw)
        self.assertLess(result, prior)

    def test_beta_at_prior_unchanged(self) -> None:
        result = vasicek_adjust(1.0, beta_prior=1.0)
        self.assertTrue(math.isclose(result, 1.0, rel_tol=1e-12))

    def test_zero_se_returns_raw_beta(self) -> None:
        # When se_beta→0, w→1, so result→beta_raw
        result = vasicek_adjust(1.5, beta_prior=1.0, se_beta=1e-10, prior_variance=0.16)
        self.assertTrue(math.isclose(result, 1.5, rel_tol=1e-4))

    def test_zero_prior_variance_returns_prior(self) -> None:
        # When prior_variance→0, w→0, result→beta_prior
        result = vasicek_adjust(1.5, beta_prior=1.0, se_beta=0.25, prior_variance=1e-10)
        self.assertTrue(math.isclose(result, 1.0, rel_tol=1e-4))


class TestBlumeAdjust(unittest.TestCase):
    def test_blume_high_beta(self) -> None:
        result = blume_adjust(1.5)
        expected = 0.33 + 0.67 * 1.5
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))
        self.assertTrue(math.isclose(result, 1.335, rel_tol=1e-12))

    def test_blume_low_beta(self) -> None:
        result = blume_adjust(0.5)
        expected = 0.33 + 0.67 * 0.5
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))
        self.assertTrue(math.isclose(result, 0.665, rel_tol=1e-12))

    def test_blume_unit_beta_unchanged(self) -> None:
        # 0.33 + 0.67*1.0 = 1.00
        result = blume_adjust(1.0)
        self.assertTrue(math.isclose(result, 1.0, rel_tol=1e-12))

    def test_blume_shrinks_high_beta(self) -> None:
        beta = 2.0
        result = blume_adjust(beta)
        self.assertLess(result, beta)

    def test_blume_raises_low_beta(self) -> None:
        beta = 0.2
        result = blume_adjust(beta)
        self.assertGreater(result, beta)

    def test_blume_zero_beta(self) -> None:
        result = blume_adjust(0.0)
        self.assertTrue(math.isclose(result, 0.33, rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
