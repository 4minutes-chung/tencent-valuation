# Tencent Investment Memo (2026-02-19)

## Thesis

- Tencent valuation is based on a CAPM-anchored WACC with peer-target leverage under MM/Hamada logic.
- Scenario valuation is decision-framed as base / bad / extreme for downside-aware position sizing.
- APT diagnostic is unstable for this run and is excluded from headline discount-rate decisions.

## Key Assumptions

- WACC (official): `7.76%`
- Cost of Equity (CAPM): `8.60%`
- Risk-free annualized: `3.37%`
- ERP annualized: `3.51%`
- Target D/E: `0.167`
- APT stability score: `0.404`
- Investor-grade QA status: `PASS`

## Scenario Fair Value

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 574.37 | 7.76% |
| bad | 316.47 | -40.63% |
| extreme | 211.10 | -60.39% |

## Risks

- capm_apt_gap: CAPM/APT gap 480.8 bps; threshold 150.0 bps.
- apt_stability_gate: APT diagnostic marked unstable and excluded from headline valuation.

## Confidence

- Overall confidence: HIGH.

## Decision Checklist

- [ ] Override filing inputs updated for current as-of date.
- [ ] CAPM inputs reviewed (rf, ERP, beta window).
- [ ] Scenario assumptions reviewed against current operating trends.
- [ ] Position sizing and risk limits documented.
