import unittest
from pathlib import Path
import tempfile

import pandas as pd

from tencent_valuation_v4.factors import (
    FactorDataError,
    REQUIRED_TENCENT_FINANCIAL_COLS,
    _read_override_if_valid,
    run_factors,
    validate_ticker_coverage,
)
from tencent_valuation_v4.paths import build_paths


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

    def test_run_factors_rebuilds_when_asof_changes_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = build_paths(tmp)
            paths.ensure()
            peers = ["9988.HK", "3690.HK"]
            wacc_config = {
                "target_ticker": "0700.HK",
                "market_ticker": "HSI",
                "min_weekly_obs": 80,
                "apt_min_obs": 36,
                "source_mode": "synthetic",
            }

            run_factors(
                asof="2026-02-18",
                paths=paths,
                peers=peers,
                wacc_config=wacc_config,
                refresh=True,
                source_mode="synthetic",
            )
            run_factors(
                asof="2026-03-18",
                paths=paths,
                peers=peers,
                wacc_config=wacc_config,
                refresh=False,
                source_mode="synthetic",
            )

            fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
            self.assertEqual(str(fin.iloc[0]["asof"]), "2026-03-18")
            self.assertTrue((paths.data_raw / "2026-03-18" / "factors_source_manifest.json").exists())
            self.assertTrue((paths.data_processed / "factors_cache_manifest.json").exists())

    def test_run_factors_rebuilds_when_processed_cache_manifest_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = build_paths(tmp)
            paths.ensure()
            peers = ["9988.HK", "3690.HK"]
            wacc_config = {
                "target_ticker": "0700.HK",
                "market_ticker": "HSI",
                "min_weekly_obs": 80,
                "apt_min_obs": 36,
                "source_mode": "synthetic",
            }

            run_factors(
                asof="2026-02-18",
                paths=paths,
                peers=peers,
                wacc_config=wacc_config,
                refresh=True,
                source_mode="synthetic",
            )

            # Simulate mixed state where only raw manifest + financials are moved to new asof.
            raw_new = paths.data_raw / "2026-03-18"
            raw_new.mkdir(parents=True, exist_ok=True)
            (raw_new / "factors_source_manifest.json").write_text(
                '{"asof": "2026-03-18", "mode": "synthetic"}',
                encoding="utf-8",
            )
            fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
            fin.loc[0, "asof"] = "2026-03-18"
            fin.to_csv(paths.data_processed / "tencent_financials.csv", index=False)

            run_factors(
                asof="2026-03-18",
                paths=paths,
                peers=peers,
                wacc_config=wacc_config,
                refresh=False,
                source_mode="synthetic",
            )

            seg = pd.read_csv(paths.data_processed / "segment_revenue.csv")
            self.assertEqual(str(seg.iloc[0]["period"]), "2026-03-18")


if __name__ == "__main__":
    unittest.main()
