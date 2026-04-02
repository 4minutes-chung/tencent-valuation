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

- DCF base: fair `176.39` HKD/share, MOS `-66.91%`.
- DCF bad: fair `117.60` HKD/share, MOS `-77.94%`.
- DCF extreme: fair `93.92` HKD/share, MOS `-82.38%`.
- Ensemble bad: `150.40` (band `75.02`..`275.93`).
- Ensemble base: `198.85` (band `112.17`..`324.63`).
- Ensemble extreme: `124.17` (band `55.42`..`227.24`).
- Ensemble expected: `170.69` (band `124.17`..`198.85`).
- WACC: `16.75%`; CAPM Re `19.93%`; APT unstable `True`.

## Validation

- QA checks: `27`
- Warnings: `5`
- Failures: `2`
- Investor grade: `NO`

## Known Limits

- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.
- APT remains diagnostic and may be unstable across regimes.
