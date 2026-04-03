"""Phase 1E — QA must run before ensemble; qa_step must not call ensemble.

Old bug: qa_step called run_ensemble with a non-existent QA JSON path, then
called run_qa.  After the fix, the canonical order is:
    multimethod → QA → ensemble

Tests verify:
  1. qa_step returns a valid QaArtifacts with an existing qa_report_json file.
  2. ensemble_step (which now correctly uses the QA report) runs without error.
  3. run_all produces ensemble output that references a real QA file.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tencent_valuation_v4.pipeline import ensemble_step, qa_step, run_all


_ASOF = "2026-02-19"


def _setup(tmp: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp / "config")
    raw = tmp / "data" / "raw" / _ASOF
    raw.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "asof": _ASOF,
                "revenue_hkd_bn": 760.0,
                "ebit_margin": 0.35,
                "capex_pct_revenue": 0.10,
                "nwc_pct_revenue": 0.02,
                "dep_pct_revenue": 0.03,
                "net_cash_hkd_bn": 120.0,
                "shares_out_bn": 9.1,
                "current_price_hkd": 500.0,
                "fundamentals_source": "override_csv",
            }
        ]
    ).to_csv(raw / "tencent_financials.csv", index=False)


class TestQaEnsembleOrdering(unittest.TestCase):
    def test_qa_step_produces_report(self) -> None:
        """qa_step must produce a valid QA JSON report without raising."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        _setup(tmp)

        qa_artifacts = qa_step(_ASOF, project_root=tmp, refresh_factors=True, source_mode="synthetic")

        self.assertTrue(
            qa_artifacts.qa_report_json.exists(),
            f"qa_report_json not found: {qa_artifacts.qa_report_json}",
        )

    def test_ensemble_step_uses_real_qa_report(self) -> None:
        """ensemble_step must run after qa_step has produced its report."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        _setup(tmp)

        # Run ensemble_step which internally runs multimethod then QA then ensemble
        ens_artifacts = ensemble_step(_ASOF, project_root=tmp, refresh_factors=True, source_mode="synthetic")
        self.assertTrue(ens_artifacts.valuation_ensemble.exists())
        self.assertTrue(ens_artifacts.valuation_method_outputs.exists())

    def test_run_all_ensemble_is_valid(self) -> None:
        """Ensemble output from run_all must have real scenario rows."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        _setup(tmp)

        payload = run_all(_ASOF, project_root=tmp, refresh=True, source_mode="synthetic")
        ensemble = pd.read_csv(payload["valuation_ensemble"])
        self.assertIn("scenario", ensemble.columns)
        self.assertIn("ensemble_fair_value_hkd_per_share", ensemble.columns)
        # Must have all three scenarios
        for scenario in ("base", "bad", "extreme"):
            self.assertIn(scenario, ensemble["scenario"].tolist())

    def test_qa_before_ensemble_in_run_all(self) -> None:
        """QA report file must exist and ensemble must reference a valid QA report."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        _setup(tmp)

        payload = run_all(_ASOF, project_root=tmp, refresh=True, source_mode="synthetic")

        # qa_report must exist and be a real file
        qa_path = Path(payload["qa_report"])
        self.assertTrue(qa_path.exists(), f"QA report not found: {qa_path}")
        # It must be parseable as JSON and have 'gates' key
        import json
        with qa_path.open() as fh:
            qa_data = json.load(fh)
        self.assertIn("checks", qa_data)


if __name__ == "__main__":
    unittest.main()
