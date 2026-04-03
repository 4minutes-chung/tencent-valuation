# Investment Report (V4)

As-of date: `2026-04-03`

## 1) Executive View

Tencent screens as overvalued versus model fair value in this snapshot.

- Market price: `489.20` HKD/share
- DCF base fair value: `354.36` HKD/share (`-27.6%` vs market)
- Ensemble base fair value: `385.89` HKD/share (`-21.1%` vs market)
- Decision: no margin-of-safety entry at current price

## 2) Key Assumptions (Standard Level)

- Forecast horizon: 7 years
- Discounting: mid-year
- Scenario set: base / bad / extreme
- Terminal growth: `2.5% / 1.0% / 0.0%`
- WACC: `10.52%`
- CAPM cost of equity: `11.59%`
- Cost of debt: `5.63%`
- Tax rate: `20%`

## 3) Valuation Results

| Scenario | DCF (HKD/share) | Ensemble (HKD/share) |
|---|---:|---:|
| Base | 354.36 | 385.89 |
| Bad | 206.34 | 267.27 |
| Extreme | 147.87 | 212.64 |

Ensemble expected value: `318.38` HKD/share.

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
- implied terminal growth: `5.043%`
- implied margin shift: `+950.5 bps`
- implied growth shift: `+510.6 bps`

## 6) Bottom Line

This V4 snapshot supports a cautious stance. A constructive buy case needs either:
1. Lower entry price, or
2. Clear fundamental improvement that closes the implied assumption gap.
