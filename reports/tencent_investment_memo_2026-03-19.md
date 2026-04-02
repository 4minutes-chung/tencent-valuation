# Tencent Investment Memo V3 (2026-03-19)

## Thesis

- Official valuation discount rate remains CAPM-based WACC under MM/Hamada target structure.
- V3 adds APV, residual income, relative valuation, SOTP/T-value, EVA, Monte Carlo, real options, and reverse DCF cross-checks.
- APT diagnostic is unstable and excluded from headline discount-rate decisions.

## Key Assumptions

- WACC (official): `16.75%`
- CAPM cost of equity: `19.93%`
- APT diagnostic cost of equity: `13.36%`
- Target D/E: `0.231`
- Beta stability score: `0.954`
- Investor-grade QA status: `NOT PASS`

## DCF Scenario Fair Value

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 176.39 | -66.91% |
| bad | 117.60 | -77.94% |
| extreme | 93.92 | -82.38% |

## Ensemble Cross-Check

- bad: ensemble `150.40` (range `75.02` to `275.93`).
- base: ensemble `198.85` (range `112.17` to `324.63`).
- extreme: ensemble `124.17` (range `55.42` to `227.24`).
- expected: ensemble `170.69` (range `124.17` to `198.85`).

## Risks

- capm_apt_gap: CAPM/APT gap 656.7 bps; threshold 150.0 bps.
- apt_stability_gate: APT diagnostic marked unstable and excluded from headline valuation.
- erp_reasonableness: ERP 0.158 outside [3%, 10%] bounds.
- backtest_minimum_coverage: Backtest minimum coverage check.
- backtest_quality_flag: Backtest quality thresholds.
- backtest_ic_gate: Backtest IC (12m) -0.657; threshold 0.100.
- backtest_calibration_slope: Calibration slope -0.003; |deviation from 1.0| = 1.003.

## Decision Checklist

- [ ] Override filing inputs updated for current as-of date.
- [ ] CAPM inputs reviewed (rf, ERP, beta windows).
- [ ] Scenario assumptions reviewed against current operating trends.
- [ ] Position sizing and risk limits documented.
