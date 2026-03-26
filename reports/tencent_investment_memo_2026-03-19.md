# Tencent Investment Memo V3 (2026-03-19)

## Thesis

- Official valuation discount rate remains CAPM-based WACC under MM/Hamada target structure.
- V3 adds APV, residual income, relative valuation, SOTP/T-value, and reverse DCF cross-checks.
- APT diagnostic is unstable and excluded from headline discount-rate decisions.

## Key Assumptions

- WACC (official): `9.11%`
- CAPM cost of equity: `10.17%`
- APT diagnostic cost of equity: `12.27%`
- Target D/E: `0.166`
- Beta stability score: `0.971`
- Investor-grade QA status: `PASS`

## DCF Scenario Fair Value

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 455.56 | -17.25% |
| bad | 264.90 | -51.88% |
| extreme | 181.25 | -67.07% |

## Ensemble Cross-Check

- bad: ensemble `272.05` (range `210.24` to `342.02`).
- base: ensemble `428.25` (range `342.02` to `497.40`).
- extreme: ensemble `202.85` (range `151.40` to `342.02`).

## Risks

- capm_apt_gap: CAPM/APT gap 209.4 bps; threshold 150.0 bps.
- apt_stability_gate: APT diagnostic marked unstable and excluded from headline valuation.

## Decision Checklist

- [ ] Override filing inputs updated for current as-of date.
- [ ] CAPM inputs reviewed (rf, ERP, beta windows).
- [ ] Scenario assumptions reviewed against current operating trends.
- [ ] Position sizing and risk limits documented.
