import math
import unittest

from tencent_valuation.wacc import (
    apt_cost_of_equity,
    clamp_beta,
    calc_rd,
    calc_wacc,
    capm_cost_of_equity,
    is_apt_unstable,
    relever_beta,
    shrink_and_cap_lambda,
    unlever_beta,
    winsorize_series,
)


class WaccMathTests(unittest.TestCase):
    def test_hamada_roundtrip(self) -> None:
        beta_l = 1.20
        tax = 0.20
        d_e = 0.25
        beta_u = unlever_beta(beta_l, tax, d_e)
        beta_l_again = relever_beta(beta_u, tax, d_e)
        self.assertTrue(math.isclose(beta_l, beta_l_again, rel_tol=1e-12))

    def test_capm_formula(self) -> None:
        rf = 0.03
        beta = 1.10
        erp = 0.05
        got = capm_cost_of_equity(rf, beta, erp)
        self.assertTrue(math.isclose(got, 0.085, rel_tol=1e-12))

    def test_apt_formula(self) -> None:
        rf = 0.03
        betas = {"MKT_EXCESS": 1.0, "SMB": 0.4, "HML": -0.2}
        lambdas = {"MKT_EXCESS": 0.05, "SMB": 0.02, "HML": 0.01}
        got = apt_cost_of_equity(rf, betas, lambdas)
        expected = 0.03 + 1.0 * 0.05 + 0.4 * 0.02 - 0.2 * 0.01
        self.assertTrue(math.isclose(got, expected, rel_tol=1e-12))

    def test_wacc_formula(self) -> None:
        re = 0.10
        d_e = 0.30
        rd = 0.05
        tax = 0.20
        got = calc_wacc(re, d_e, rd, tax)
        equity_weight = 1.0 / 1.3
        debt_weight = 0.3 / 1.3
        expected = equity_weight * re + debt_weight * rd * (1 - tax)
        self.assertTrue(math.isclose(got, expected, rel_tol=1e-12))

    def test_rd_floor_for_zero_debt(self) -> None:
        got = calc_rd(interest_expense_hkd_bn=1.0, avg_gross_debt_hkd_bn=0.0, floor=0.02, ceiling=0.10)
        self.assertEqual(got, 0.02)

    def test_rd_clipping(self) -> None:
        low = calc_rd(interest_expense_hkd_bn=0.5, avg_gross_debt_hkd_bn=100.0, floor=0.02, ceiling=0.10)
        high = calc_rd(interest_expense_hkd_bn=30.0, avg_gross_debt_hkd_bn=100.0, floor=0.02, ceiling=0.10)
        self.assertEqual(low, 0.02)
        self.assertEqual(high, 0.10)

    def test_winsorize_series(self) -> None:
        import pandas as pd

        s = pd.Series([0.01, 0.02, 0.03, 0.04, 1.00])
        out, changed = winsorize_series(s, 0.01)
        self.assertTrue(changed)
        self.assertLess(out.iloc[-1], 1.00)

    def test_clamp_beta(self) -> None:
        beta, changed = clamp_beta(3.2, 2.0)
        self.assertEqual(beta, 2.0)
        self.assertTrue(changed)

    def test_shrink_and_cap_lambda(self) -> None:
        lam, shrink_changed, cap_changed = shrink_and_cap_lambda(sample=0.20, shrinkage=0.6, abs_cap=0.08)
        self.assertEqual(lam, 0.08)
        self.assertTrue(shrink_changed)
        self.assertTrue(cap_changed)

    def test_apt_unstable_gate(self) -> None:
        self.assertTrue(is_apt_unstable(0.09, 0.15, unstable_gap_bps=400))
        self.assertFalse(is_apt_unstable(0.09, 0.12, unstable_gap_bps=400))


if __name__ == "__main__":
    unittest.main()
