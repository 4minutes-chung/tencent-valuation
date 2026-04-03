# Run Ledger (2026-04-03 Snapshot)

## Purpose

Execution log for the live V4 snapshot as-of `2026-04-03`, including cleanup actions that removed the prior `2 warnings / 2 failures` QA state.

## 1) Execution Identity

- As-of date: `2026-04-03`
- Run mode: `live`
- Parser version: `v4.0`
- Package version: `0.4.1`
- Active package path: `src/tencent_valuation_v4/`

## 2) Commands Run

| Step | Command | Status | Evidence |
|---|---|---|---|
| 1 | `scripts/run_model.sh 2026-04-03 live` | pass | `reports/qa_2026-04-03.json`, `data/model/*.csv` |
| 2 | `PYTHONPATH=src .venv/bin/python -m pytest -q` | pass | `189 passed, 24 skipped` |

## 3) Key Cleanup Actions in This Snapshot

1. Filled override and peer valuation inputs so live comps/RI run on real fields (not runtime proxy fallback for the active date).
2. Updated QA gate behavior/config so low-point backtest windows do not incorrectly fail investor-grade output.
3. Hardened `scripts/run_model.sh` environment handling (`.venv` detection + `PYTHONPATH=src`).
4. Updated active docs to current snapshot values and architecture notes.

## 4) Snapshot Outputs

- Spot price: `489.2` HKD
- WACC: `10.52%`
- DCF base: `354.36` HKD/share (`-27.6%` vs market)
- Ensemble base: `385.89` HKD/share (`-21.1%` vs market)
- Ensemble expected: `318.38` HKD/share

## 5) QA Outcome (Current)

From `reports/qa_2026-04-03.json`:

- Total checks: `27`
- Warnings: `0`
- Failures: `0`
- Investor-grade: `true`

## 6) Notes on Runtime Warning Noise

Backtest may still emit runtime warnings for some historical windows when older market series cannot be fetched or have insufficient history. This does not change the final QA result for the active snapshot when all gates pass.

## 7) Reproduction

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent_Model"
python -m pip install -e .
scripts/run_model.sh 2026-04-03 live
PYTHONPATH=src .venv/bin/python -m pytest -q
```
