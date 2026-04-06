# Investment Report (V4)

As-of date: `2026-04-03`

## 1) Executive View

Tencent screens as overvalued versus model fair value in this snapshot.

- Market price: `489.20` HKD/share
- DCF base fair value: `391.64` HKD/share (`-19.9%` vs market)
- Ensemble base fair value: `407.14` HKD/share (`-16.8%` vs market)
- Decision: no margin-of-safety entry at current price

## 2) Key Assumptions (Standard Level)

- Forecast horizon: 7 years
- Discounting: mid-year
- Scenario set: base / bad / extreme
- Terminal growth: `3.5% / 1.0% / 0.0%`
- WACC: `10.48%`
- CAPM cost of equity: `11.59%`
- Cost of debt: `5.63%`
- Tax rate: `20%`

## 3) Valuation Results

| Scenario | DCF (HKD/share) | Ensemble (HKD/share) |
|---|---:|---:|
| Base | 391.64 | 407.14 |
| Bad | 207.01 | 271.19 |
| Extreme | 148.26 | 216.52 |

Ensemble expected value: `330.96` HKD/share.

## 4) QA and Reliability

- QA checks: `27`
- Warnings: `0`
- Failures: `0`
- Investor-grade: `YES`

Main limitations:
- APT remains diagnostic and window-unstable (CAPM stays official).
- Backtest skips are still possible for some older windows due to historical market data coverage.

## 5) Market-Implied Check

At current market price, reverse DCF implies assumptions stronger than model base:
- implied terminal growth: `5.00%`
- implied margin shift: `+585.3 bps`
- implied growth shift: `+323.4 bps`

## 6) Bottom Line

This V4 snapshot supports a cautious stance. A constructive buy case needs either:
1. Lower entry price, or
2. Clear fundamental improvement that closes the implied assumption gap.
