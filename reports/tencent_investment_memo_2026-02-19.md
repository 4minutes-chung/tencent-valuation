# Tencent Investment Memo V3 (2026-02-19)

## Thesis

- Official valuation discount rate remains CAPM-based WACC under MM/Hamada target structure.
- V3 adds APV, residual income, relative valuation, SOTP/T-value, and reverse DCF cross-checks.
- APT diagnostic is unstable and excluded from headline discount-rate decisions.

## Key Assumptions

- WACC (official): `7.76%`
- CAPM cost of equity: `8.60%`
- APT diagnostic cost of equity: `13.40%`
- Target D/E: `0.167`
- Beta stability score: `0.986`
- Investor-grade QA status: `PASS`

## DCF Scenario Fair Value

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 573.78 | 7.65% |
| bad | 316.14 | -40.69% |
| extreme | 210.88 | -60.43% |

## Ensemble Cross-Check

- bad: ensemble `316.65` (range `265.19` to `351.71`).
- base: ensemble `528.37` (range `341.39` to `615.62`).
- extreme: ensemble `229.30` (range `187.71` to `341.39`).

## Risks

- capm_apt_gap: CAPM/APT gap 480.8 bps; threshold 150.0 bps.
- apt_stability_gate: APT diagnostic marked unstable and excluded from headline valuation.

## Decision Checklist

- [ ] Override filing inputs updated for current as-of date.
- [ ] CAPM inputs reviewed (rf, ERP, beta windows).
- [ ] Scenario assumptions reviewed against current operating trends.
- [ ] Position sizing and risk limits documented.
