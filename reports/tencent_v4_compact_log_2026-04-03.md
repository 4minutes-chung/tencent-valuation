# Tencent V4 Compact Log (2026-04-03)

## Process

1. fetch
2. build-overrides
3. factors
4. wacc
5. dcf/apv/residual/comps/tvalue/reverse-dcf
6. ensemble
7. qa/report

## Headline Output

- DCF base: fair `354.36` HKD/share, MOS `-27.56%`.
- DCF bad: fair `206.34` HKD/share, MOS `-57.82%`.
- DCF extreme: fair `147.87` HKD/share, MOS `-69.77%`.
- Ensemble bad: `267.27` (band `168.26`..`547.60`).
- Ensemble base: `385.89` (band `263.23`..`644.24`).
- Ensemble extreme: `212.64` (band `125.17`..`450.96`).
- Ensemble expected: `318.38` (band `212.64`..`385.89`).
- WACC: `10.52%`; CAPM Re `11.59%`; APT unstable `True`.

## Validation

- QA checks: `27`
- Warnings: `0`
- Failures: `0`
- Investor grade: `YES`

## Known Limits

- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.
- APT remains diagnostic and may be unstable across regimes.
