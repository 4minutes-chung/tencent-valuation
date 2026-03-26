# Tencent V3 Compact Log (2026-03-19)

## Process

1. fetch
2. build-overrides
3. factors
4. wacc
5. dcf/apv/residual/comps/tvalue/reverse-dcf
6. ensemble
7. qa/report

## Headline Output

- DCF base: fair `455.56` HKD/share, MOS `-17.25%`.
- DCF bad: fair `264.90` HKD/share, MOS `-51.88%`.
- DCF extreme: fair `181.25` HKD/share, MOS `-67.07%`.
- Ensemble bad: `272.05` (band `210.24`..`342.02`).
- Ensemble base: `428.25` (band `342.02`..`497.40`).
- Ensemble extreme: `202.85` (band `151.40`..`342.02`).
- WACC: `9.11%`; CAPM Re `10.17%`; APT unstable `True`.

## Validation

- QA checks: `21`
- Warnings: `2`
- Failures: `0`
- Investor grade: `YES`

## Known Limits

- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.
- APT remains diagnostic and may be unstable across regimes.
