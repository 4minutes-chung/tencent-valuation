# Tencent Valuation V3 Report (2026-02-19)

## WACC Summary

- WACC (CAPM official): `7.76%`
- CAPM Re: `8.60%`
- APT Re (guardrailed, diagnostic): `13.40%`
- CAPM/APT gap: `480.8 bps`
- Beta stability score: `0.986`
- APT stability score: `0.404`
- APT unstable reason codes: `capm_apt_gap;window_instability`
- ERP decomposition: `{"rf_annual": 0.03370444447361208, "market_excess_annual": 0.0351, "method": "rolling_excess_return", "lookback_months": 60}`

## Scenario DCF Valuation

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 573.78 | 7.65% |
| bad | 316.14 | -40.69% |
| extreme | 210.88 | -60.43% |

## Ensemble Fair Value

| Scenario | Ensemble Fair Value | Min Method | Max Method | Band Width Ratio |
|---|---:|---:|---:|---:|
| bad | 316.65 | 265.19 | 351.71 | 0.27 |
| base | 528.37 | 341.39 | 615.62 | 0.52 |
| extreme | 229.30 | 187.71 | 341.39 | 0.67 |

## T-Value Company Bridge

| Scenario | Operating | Strategic Inv. | Net Cash | Total Equity | HKD/share |
|---|---:|---:|---:|---:|---:|
| base | 5094.64 | 380.00 | 116.01 | 5590.65 | 615.62 |
| bad | 2754.98 | 323.00 | 116.01 | 3193.99 | 351.71 |
| extreme | 1799.10 | 266.00 | 116.01 | 2181.10 | 240.18 |

## Reverse DCF

- Implied terminal growth for current price: `1.95%`
- Implied margin shift vs base: `-220.9 bps`
- Implied growth shift vs base: `-131.2 bps`

## QA Summary

- Total checks: `21`
- Warnings: `2`
- Failures: `0`
- Investor-grade: `YES`

## Confidence

- Confidence level: `HIGH`.

- `segment_sum_to_total`: **pass** - Segment revenues reconcile to total revenue.
- `capm_apt_gap`: **warn** - CAPM/APT gap 480.8 bps; threshold 150.0 bps.
- `apt_stability_gate`: **warn** - APT diagnostic marked unstable and excluded from headline valuation.
- `target_de_bounds`: **pass** - Target D/E 0.167; max allowed 2.000.
- `scenario_ordering`: **pass** - Check extreme <= bad <= base.
- `override_fundamentals_present`: **pass** - Override files are present and processed data uses override sources.
- `fundamentals_ttm_method`: **pass** - Fundamentals are derived from strict 4-quarter TTM method.
- `peer_input_coverage`: **pass** - Peer input coverage check against data/raw/<asof>/peer_fundamentals.csv.
- `peer_source_recency`: **pass** - Peer source recency check.
- `source_manifest_health`: **pass** - Source manifest ingestion status.
- `scenario_economic_consistency`: **pass** - Scenario assumptions are within configured economic bounds.
- `schema::wacc_components.csv`: **pass** - Schema contract for wacc_components.csv.
- `schema::valuation_outputs.csv`: **pass** - Schema contract for valuation_outputs.csv.
- `schema::valuation_method_outputs.csv`: **pass** - Schema contract for valuation_method_outputs.csv.
- `schema::valuation_ensemble.csv`: **pass** - Schema contract for valuation_ensemble.csv.
- `schema::tvalue_company_bridge.csv`: **pass** - Schema contract for tvalue_company_bridge.csv.
- `schema::reverse_dcf_outputs.csv`: **pass** - Schema contract for reverse_dcf_outputs.csv.
- `headline_nan_check`: **pass** - No NaN values in ensemble headline outputs.
- `ensemble_band_width`: **pass** - Ensemble valuation band width sanity check.
- `backtest_minimum_coverage`: **pass** - Backtest minimum coverage check.
- `backtest_quality_flag`: **pass** - Backtest quality thresholds.
