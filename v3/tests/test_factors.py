import unittest
from pathlib import Path
import tempfile

import pandas as pd

from tencent_valuation_v3.factors import (
    FactorDataError,
    REQUIRED_TENCENT_FINANCIAL_COLS,
    _read_override_if_valid,
    validate_ticker_coverage,
)


class FactorValidationTests(unittest.TestCase):
    def test_missing_ticker_raises(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": ["0700.HK", "0700.HK", "HSI"],
                "ret": [0.01, 0.02, 0.01],
            }
        )
        with self.assertRaises(FactorDataError):
            validate_ticker_coverage(frame, ["0700.HK", "9988.HK"], min_obs=2)

    def test_short_history_raises(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": ["0700.HK", "0700.HK", "9988.HK"],
                "ret": [0.01, 0.02, 0.03],
            }
        )
        with self.assertRaises(FactorDataError):
            validate_ticker_coverage(frame, ["0700.HK", "9988.HK"], min_obs=2)

    def test_override_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tencent_financials.csv"
            pd.DataFrame([{"asof": "2026-02-18"}]).to_csv(path, index=False)
            with self.assertRaises(FactorDataError):
                _read_override_if_valid(path, REQUIRED_TENCENT_FINANCIAL_COLS)


if __name__ == "__main__":
    unittest.main()
