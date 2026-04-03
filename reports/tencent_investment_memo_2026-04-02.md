# Tencent Investment Memo V4 (2026-04-02)

## Thesis

- Official valuation discount rate remains CAPM-based WACC under MM/Hamada target structure.
- V4 includes APV, residual income, relative valuation, SOTP/T-value, EVA, Monte Carlo, real options, and reverse DCF cross-checks.
- APT diagnostic is unstable and excluded from headline discount-rate decisions.

## Key Assumptions

- WACC (official): `10.52%`
- CAPM cost of equity: `11.59%`
- APT diagnostic cost of equity: `12.76%`
- Target D/E: `0.179`
- Beta stability score: `0.971`
- Investor-grade QA status: `NOT PASS`

## DCF Scenario Fair Value

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 354.36 | -27.56% |
| bad | 206.34 | -57.82% |
| extreme | 147.87 | -69.77% |

## Ensemble Cross-Check

- bad: ensemble `244.64` (range `172.93` to `363.11`).
- base: ensemble `361.08` (range `276.83` to `445.89`).
- extreme: ensemble `193.66` (range `125.17` to `363.11`).
- expected: ensemble `295.21` (range `193.66` to `361.08`).

## Risks

- apt_stability_gate: APT diagnostic marked unstable and excluded from headline valuation.
- backtest_minimum_coverage: Backtest minimum coverage check.
- backtest_quality_flag: Backtest quality thresholds.
- backtest_calibration_slope: Calibration slope 0.246; |deviation from 1.0| = 0.754.

## Decision Checklist

- [ ] Override filing inputs updated for current as-of date.
- [ ] CAPM inputs reviewed (rf, ERP, beta windows).
- [ ] Scenario assumptions reviewed against current operating trends.
- [ ] Position sizing and risk limits documented.
