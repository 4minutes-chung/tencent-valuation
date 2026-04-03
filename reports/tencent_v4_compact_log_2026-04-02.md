# Tencent V4 Compact Log (2026-04-02)

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
- Ensemble bad: `244.64` (band `172.93`..`363.11`).
- Ensemble base: `361.08` (band `276.83`..`445.89`).
- Ensemble extreme: `193.66` (band `125.17`..`363.11`).
- Ensemble expected: `295.21` (band `193.66`..`361.08`).
- WACC: `10.52%`; CAPM Re `11.59%`; APT unstable `True`.

## Validation

- QA checks: `27`
- Warnings: `2`
- Failures: `2`
- Investor grade: `NO`

## Known Limits

- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.
- APT remains diagnostic and may be unstable across regimes.
