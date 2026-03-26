# Tencent V3 Compact Log (2026-02-19)

## Process

1. fetch
2. build-overrides
3. factors
4. wacc
5. dcf/apv/residual/comps/tvalue/reverse-dcf
6. ensemble
7. qa/report

## Headline Output

- DCF base: fair `573.78` HKD/share, MOS `7.65%`.
- DCF bad: fair `316.14` HKD/share, MOS `-40.69%`.
- DCF extreme: fair `210.88` HKD/share, MOS `-60.43%`.
- Ensemble bad: `316.65` (band `265.19`..`351.71`).
- Ensemble base: `528.37` (band `341.39`..`615.62`).
- Ensemble extreme: `229.30` (band `187.71`..`341.39`).
- WACC: `7.76%`; CAPM Re `8.60%`; APT unstable `True`.

## Validation

- QA checks: `21`
- Warnings: `2`
- Failures: `0`
- Investor grade: `YES`

## Known Limits

- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.
- APT remains diagnostic and may be unstable across regimes.
