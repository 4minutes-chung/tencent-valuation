# Tencent Valuation Compact Run Log (2026-02-18)

## 1) Purpose
- Equity valuation for Tencent (`0700.HK`) with `base / bad / extreme` scenarios.
- CAPM-based official WACC (MM/Hamada capital structure logic), APT diagnostic only.
- Repeatable pipeline and ship-ready project artifacts.

## 2) Run Sequence (Executed)
1. `tencent-valuation fetch --asof 2026-02-18`
2. `tencent-valuation build-overrides --asof 2026-02-18`
3. `tencent-valuation run-all --asof 2026-02-18 --source-mode live --refresh`
4. `tencent-valuation backtest --start 2024-01-01 --end 2025-12-31 --freq quarterly --source-mode live`
5. `tencent-valuation qa --asof 2026-02-18 --source-mode live`
6. `tencent-valuation report --asof 2026-02-18 --source-mode live`

## 3) Data Pack Used
- Quarterly canonical fundamentals: `data/processed/tencent_quarterly_financials.csv`
- Quarterly coverage: `2023-12-31` to `2025-09-30` (8 quarters).
- Strict TTM revenue basis (last 4 quarters): `729.841 RMB bn`.
- As-of override inputs:
- `data/raw/2026-02-18/tencent_financials.csv`
- `data/raw/2026-02-18/segment_revenue.csv`
- `data/raw/2026-02-18/peer_fundamentals.csv`
- Market/factor inputs built from live mode and persisted to `data/processed/`.

## 4) Method Stack (Implemented)
- Capital structure:
- Peer levered beta -> unlevered beta (`beta_U_peer`) -> peer median target.
- Tencent relevering with target D/E and Tencent tax rate.
- Cost of equity:
- Official: `Re_CAPM = Rf + beta_L_tencent * ERP`.
- Diagnostic: `Re_APT = Rf + beta_mkt*lambda_mkt + beta_smb*lambda_smb + beta_hml*lambda_hml`.
- APT controls:
- Winsorization (1%/99%), beta caps, lambda shrinkage/caps.
- Rolling stability windows (24/36/60m policy, active windows available by data).
- WACC:
- `WACC = E/(D+E)*Re_CAPM + D/(D+E)*Rd*(1-T)`.
- DCF:
- 7-year forecast; scenarios vary growth/margin/capex/NWC paths.
- CAPM WACC remains official in all scenarios.
- Backtest:
- Quarterly as-of reruns; 6M/12M direction hit and calibration MAE.

## 5) Key Output Numbers
- WACC: `7.76%`
- Re (CAPM official): `8.60%`
- Re (APT guardrailed diagnostic): `13.40%`
- CAPM/APT gap: `480.8 bps`
- APT unstable: `true`
- APT stability score: `0.404`
- Target D/E: `0.1668`
- Rd: `3.43%`
- Rf annualized: `3.37%`
- ERP annualized: `3.51%`

### Fair Value (HKD/share)
- Base: `575.03` (MOS `+7.88%` vs `533.0`)
- Bad: `316.83` (MOS `-40.56%`)
- Extreme: `211.34` (MOS `-60.35%`)

### Backtest (2024-01-01 to 2025-12-31, quarterly)
- Points: `8`
- Hit rate 6M: `0.50`
- Hit rate 12M: `0.75`
- Calibration MAE 12M: `0.9903`

## 6) Validation / QA Status
- QA summary: `12 checks`, `2 warnings`, `1 failure`, `investor_grade=false`.
- Non-pass checks:
- `capm_apt_gap`: `warn` (CAPM/APT divergence above alert threshold).
- `apt_stability_gate`: `warn` (APT unstable; excluded from headline valuation).
- `backtest_quality_flag`: `fail` (calibration threshold not met).
- Pass highlights:
- Override fundamentals present and used.
- Strict TTM method detected (`ttm_4q_from_quarterly`).
- Peer input coverage pass.
- Scenario ordering pass (`extreme <= bad <= base`).
- Scenario economic consistency pass.

## 7) Main Changes Delivered in This Cycle
- Added `build-overrides` command and strict quarterly->TTM override flow.
- Added `backtest` command and output contracts.
- Added APT rolling stability + premia sanity diagnostics to WACC output.
- Added `config/qa_gates.yaml` and integrated new QA gates into pipeline.
- Added scenario assumptions output (`scenario_assumptions_used.csv`).
- Updated report + investment memo with confidence and investor-grade context.
- Updated CI to enforce QA fail-gate on pipeline fixture run.
- Added/updated tests; suite passes (`16/16`).

## 8) Known Gaps (Current)
- Model still not investor-grade because `backtest_quality_flag` is failing.
- CAPM vs APT divergence remains large; APT remains diagnostic-only and unstable.
- Peer fundamentals are currently template-driven unless manually refreshed from filings.

## 9) Tomorrow Test Focus (Priority Order)
1. Recalibrate backtest quality gate and calibration metric (or adjust scenario calibration logic).
2. Tighten peer fundamentals to fully filing-derived values (debt, interest, tax, shares) for all peers.
3. Improve factor/premia calibration to reduce persistent CAPM/APT gap without changing CAPM official policy.
4. Re-run full pipeline and target `failures=0` for investor-grade.

## 10) Artifact Index
- `data/model/wacc_components.csv`
- `data/model/capm_apt_compare.csv`
- `data/model/valuation_outputs.csv`
- `data/model/sensitivity_wacc_g.csv`
- `data/model/sensitivity_margin_growth.csv`
- `data/model/scenario_assumptions_used.csv`
- `data/model/backtest_summary.csv`
- `data/model/backtest_point_results.csv`
- `reports/qa_2026-02-18.json`
- `reports/tencent_valuation_2026-02-18.md`
- `reports/tencent_investment_memo_2026-02-18.md`
