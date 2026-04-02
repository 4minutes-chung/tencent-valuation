# Tencent Investment Memo V4 (2026-02-19)

## Thesis

- Official valuation discount rate remains CAPM-based WACC under MM/Hamada target structure.
- V4 includes APV, residual income, relative valuation, SOTP/T-value, EVA, Monte Carlo, real options, and reverse DCF cross-checks.
- APT diagnostic is unstable and excluded from headline discount-rate decisions.

## Key Assumptions

- WACC (official): `10.60%`
- CAPM cost of equity: `11.64%`
- APT diagnostic cost of equity: `12.76%`
- Target D/E: `0.170`
- Beta stability score: `0.973`
- Investor-grade QA status: `NOT PASS`

## DCF Scenario Fair Value

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 348.66 | -32.03% |
| bad | 203.87 | -60.26% |
| extreme | 146.59 | -71.42% |

## Ensemble Cross-Check

- bad: ensemble `242.49` (range `171.61` to `356.88`).
- base: ensemble `357.15` (range `274.50` to `445.39`).
- extreme: ensemble `192.08` (range `124.25` to `356.88`).
- expected: ensemble `292.26` (range `192.08` to `357.15`).

## Risks

- apt_stability_gate: APT diagnostic marked unstable and excluded from headline valuation.
- peer_input_coverage: Peer input coverage check against data/raw/<asof>/peer_fundamentals.csv.
- backtest_minimum_coverage: Backtest minimum coverage check.
- backtest_quality_flag: Backtest quality thresholds.
- backtest_ic_gate: Backtest IC (12m) 0.071; threshold 0.100.
- backtest_calibration_slope: Calibration slope 0.094; |deviation from 1.0| = 0.906.

## Decision Checklist

- [ ] Override filing inputs updated for current as-of date.
- [ ] CAPM inputs reviewed (rf, ERP, beta windows).
- [ ] Scenario assumptions reviewed against current operating trends.
- [ ] Position sizing and risk limits documented.
