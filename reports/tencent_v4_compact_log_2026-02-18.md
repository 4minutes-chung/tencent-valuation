# Tencent V4 Compact Log (2026-02-18)

## Process

1. fetch
2. build-overrides
3. factors
4. wacc
5. dcf/apv/residual/comps/tvalue/reverse-dcf
6. ensemble
7. qa/report

## Headline Output

- DCF base: fair `348.66` HKD/share, MOS `-32.03%`.
- DCF bad: fair `203.87` HKD/share, MOS `-60.26%`.
- DCF extreme: fair `146.59` HKD/share, MOS `-71.42%`.
- Ensemble bad: `242.58` (band `171.61`..`357.74`).
- Ensemble base: `357.24` (band `274.50`..`445.39`).
- Ensemble extreme: `192.17` (band `124.25`..`357.74`).
- Ensemble expected: `292.35` (band `192.17`..`357.24`).
- WACC: `10.60%`; CAPM Re `11.64%`; APT unstable `True`.

## Validation

- QA checks: `27`
- Warnings: `3`
- Failures: `2`
- Investor grade: `NO`

## Known Limits

- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.
- APT remains diagnostic and may be unstable across regimes.
