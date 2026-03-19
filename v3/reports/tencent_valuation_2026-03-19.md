# Tencent Valuation V3 Report (2026-03-19)

## WACC Summary

- WACC (CAPM official): `9.11%`
- CAPM Re: `10.17%`
- APT Re (guardrailed, diagnostic): `12.27%`
- CAPM/APT gap: `209.4 bps`
- Beta stability score: `0.971`
- APT stability score: `0.333`
- APT unstable reason codes: `window_instability`
- ERP decomposition: `{"rf_annual": 0.0342265190350156, "market_excess_annual": 0.04542000000000001, "method": "rolling_excess_return", "lookback_months": 60}`

## Scenario DCF Valuation

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 455.56 | -17.25% |
| bad | 264.90 | -51.88% |
| extreme | 181.25 | -67.07% |

## Ensemble Fair Value

| Scenario | Ensemble Fair Value | Min Method | Max Method | Band Width Ratio |
|---|---:|---:|---:|---:|
| bad | 272.05 | 210.24 | 342.02 | 0.48 |
| base | 428.25 | 342.02 | 497.40 | 0.36 |
| extreme | 202.85 | 151.40 | 342.02 | 0.94 |

## T-Value Company Bridge

| Scenario | Operating | Strategic Inv. | Net Cash | Total Equity | HKD/share |
|---|---:|---:|---:|---:|---:|
| base | 4020.81 | 380.00 | 116.21 | 4517.02 | 497.40 |
| bad | 2289.45 | 323.00 | 116.21 | 2728.66 | 300.47 |
| extreme | 1529.79 | 266.00 | 116.21 | 1912.00 | 210.54 |

## Reverse DCF

- Implied terminal growth for current price: `4.01%`
- Implied margin shift vs base: `650.2 bps`
- Implied growth shift vs base: `351.7 bps`

## QA Summary

- Total checks: `21`
- Warnings: `2`
- Failures: `0`
- Investor-grade: `YES`

## Confidence

- Confidence level: `HIGH`.

- `segment_sum_to_total`: **pass** - Segment revenues reconcile to total revenue.
- `capm_apt_gap`: **warn** - CAPM/APT gap 209.4 bps; threshold 150.0 bps.
- `apt_stability_gate`: **warn** - APT diagnostic marked unstable and excluded from headline valuation.
- `target_de_bounds`: **pass** - Target D/E 0.166; max allowed 2.000.
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
