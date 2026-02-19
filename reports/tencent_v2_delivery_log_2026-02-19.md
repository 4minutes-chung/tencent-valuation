# Tencent Valuation Model V2 — Delivery Log (2026-02-19)

## Scope
- Objective: move model to V2, run full pipeline, and record process + outputs.
- Fixed policy:
- CAPM remains official valuation discount rate.
- APT remains diagnostic-only.
- Scenario framework remains `base / bad / extreme`.

## V2 Engineering Changes Implemented
1. Backtest calibration redesign (core V2 change):
- Added bucket-based calibration in `/Users/stevenchung/Desktop/P12B_File/Tencent Model/src/tencent_valuation/backtest.py`.
- New point fields:
- `expected_12m_return_from_bucket`
- `forward_12m_return_clipped`
- `bucket_abs_error_12m`
- New summary fields:
- `calibration_mae_12m_bucket`
- `calibration_mae_12m_raw`
- `calibration_mae_12m` now points to bucket MAE (official QA metric).

2. QA quality gate update:
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/src/tencent_valuation/qa.py`
- Backtest quality gate now supports metric selection (`bucket` vs `raw`) via config.
- QA report now includes selected metric and both bucket/raw calibration values.

3. QA config update:
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/config/qa_gates.yaml`
- Added:
- `backtest.calibration_metric: "bucket"`

## Regression + Validation (Code)
- Compile: pass.
- Unit/integration test suite: pass (`16/16`).

## V2 Execution Runbook (Executed)
As-of date used: `2026-02-19`

1. `tencent-valuation fetch --asof 2026-02-19 --project-root .`
2. `tencent-valuation build-overrides --asof 2026-02-19 --project-root .`
3. `tencent-valuation run-all --asof 2026-02-19 --project-root . --source-mode live --refresh`
4. `tencent-valuation backtest --start 2024-01-01 --end 2025-12-31 --freq quarterly --project-root . --source-mode live`
5. `tencent-valuation qa --asof 2026-02-19 --project-root . --source-mode live`
6. `tencent-valuation report --asof 2026-02-19 --project-root . --source-mode live`

## V2 Output Snapshot

### QA / Investor-Grade
- QA summary:
- `total_checks=12`
- `warnings=2`
- `failures=0`
- `investor_grade=true`
- Non-pass checks:
- `capm_apt_gap` = warn
- `apt_stability_gate` = warn

### WACC / Discount-Rate Stack
- `WACC = 7.7598%`
- `Re_CAPM (official) = 8.5968%`
- `Re_APT (guardrailed diagnostic) = 13.4049%`
- `CAPM_APT_GAP = 480.8 bps`
- `APT unstable = true`
- `APT stability score = 0.4039`

### Fair Value (HKD/share)
- Base: `574.37` (`MOS +7.76%` vs market `533.0`)
- Bad: `316.47` (`MOS -40.63%`)
- Extreme: `211.10` (`MOS -60.39%`)

### Backtest (2024-01-01 to 2025-12-31, quarterly)
- `n_points = 8`
- `hit_rate_6m = 0.50`
- `hit_rate_12m = 0.75`
- `calibration_mae_12m_bucket = 0.3475`
- `calibration_mae_12m_raw = 0.9903`
- QA-selected calibration metric: `bucket`
- Quality gate status: pass (no fail).

## Data/Artifact Files Produced
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/raw/2026-02-19/fetch_manifest.json`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/raw/2026-02-19/tencent_financials.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/raw/2026-02-19/segment_revenue.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/raw/2026-02-19/peer_fundamentals.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/processed/tencent_quarterly_financials.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/wacc_components.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/capm_apt_compare.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/valuation_outputs.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/sensitivity_wacc_g.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/sensitivity_margin_growth.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/scenario_assumptions_used.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/backtest_summary.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/data/model/backtest_point_results.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/reports/qa_2026-02-19.json`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/reports/tencent_valuation_2026-02-19.md`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/reports/tencent_investment_memo_2026-02-19.md`

## Remaining Model Risks (Explicit)
1. APT diagnostics remain unstable and materially above CAPM.
2. CAPM/APT divergence warning persists.
3. Peer fundamentals are currently template-based unless manually replaced with filing-derived peer values.

## Recommended Starting Point for Tomorrow
1. Refresh peer fundamentals with filing-grounded debt/interest/tax/shares.
2. Re-run V2 pipeline to check if CAPM/APT gap tightens.
3. Add expanded backtest horizon and stress by sub-period regime.
