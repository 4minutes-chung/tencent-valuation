# Tencent Valuation V4 Report (2026-02-18)

## WACC Summary

- WACC (CAPM official): `10.60%`
- CAPM Re: `11.64%`
- APT Re (guardrailed, diagnostic): `12.76%`
- CAPM/APT gap: `111.8 bps`
- Beta stability score: `0.973`
- APT stability score: `0.333`
- APT unstable reason codes: `window_instability`
- ERP decomposition: `{"rf_annual": 0.041257894736841605, "market_excess_annual": 0.0463, "method": "rolling_excess_return", "lookback_months": 60}`

## Scenario DCF Valuation

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 348.66 | -32.03% |
| bad | 203.87 | -60.26% |
| extreme | 146.59 | -71.42% |

## Ensemble Fair Value

| Scenario | Ensemble Fair Value | Min Method | Max Method | Band Width Ratio |
|---|---:|---:|---:|---:|
| bad | 242.58 | 171.61 | 357.74 | 0.77 |
| base | 357.24 | 274.50 | 445.39 | 0.48 |
| extreme | 192.17 | 124.25 | 357.74 | 1.22 |
| expected | 292.35 | 192.17 | 357.24 | 0.56 |

## T-Value Company Bridge

| Scenario | Operating | Strategic Inv. | Net Cash | Total Equity | HKD/share |
|---|---:|---:|---:|---:|---:|
| base | 3563.46 | 380.00 | 116.23 | 4044.69 | 445.39 |
| bad | 2014.65 | 323.00 | 116.23 | 2438.87 | 268.56 |
| extreme | 1330.60 | 266.00 | 116.23 | 1697.83 | 186.96 |

## Reverse DCF

- Implied terminal growth for current price: `5.51%`
- Implied margin shift vs base: `1202.3 bps`
- Implied growth shift vs base: `627.8 bps`

## Monte Carlo Distribution

| Percentile | Fair Value (HKD/share) |
|---:|---:|
| 5 | 274.16 |
| 10 | 290.16 |
| 25 | 320.97 |
| 50 | 357.74 |
| 75 | 400.86 |
| 90 | 444.45 |
| 95 | 472.63 |

- P(FV > market price 513): `1.8%`
- Simulations: `10,000`

## EVA / Excess Return Analysis

| Scenario | Fair Value (HKD/share) | EVA Y1 (HKD bn) |
|---|---:|---:|
| base | 361.69 | -7.59 |
| bad | 271.30 | -54.80 |
| extreme | 250.99 | -102.01 |

## Stress Scenarios

| Scenario | Description | Prob | WACC | Fair Value (HKD/share) | MoS |
|---|---|---:|---:|---:|---:|
| gaming_crackdown | Severe gaming regulation tightening | 5.0% | 10.60% | 145.89 | -71.56% |
| fintech_regulation | Major fintech licensing / capital requirements | 8.0% | 10.60% | 218.10 | -57.49% |
| us_china_escalation | US-China tech decoupling | 10.0% | 11.60% | 198.14 | -61.38% |

## Risk Factors / Cost of Capital Inputs

- Risk-free rate (Rf): `0.0413`
- Equity risk premium (ERP): `0.0463`
- Country risk premium (CRP): `0.0125`
- Beta (levered, adjusted): `1.3536`
- Cost of debt (Rd): `0.0563`

## Backtest Performance

- Data points: `12`
- 12m directional hit rate: `75.0%`
- IC (12m): `0.0714`
- Calibration slope (12m): `0.0938`
- RMSE (12m): `0.4115`

### Regime Breakdown

| Regime | N | Hit Rate 12m | IC 12m | Calib. Slope |
|---|---:|---:|---:|---:|
| high_vol | 12 | 75.0% | 0.071 | 0.094 |

## QA Summary

- Total checks: `27`
- Warnings: `3`
- Failures: `2`
- Investor-grade: `NO`

## Confidence

- Confidence level: `MEDIUM-LOW` (APT instability and/or QA failures).

- `segment_sum_to_total`: **pass** - Segment revenues reconcile to total revenue.
- `capm_apt_gap`: **pass** - CAPM/APT gap 111.8 bps; threshold 150.0 bps.
- `apt_stability_gate`: **warn** - APT diagnostic marked unstable and excluded from headline valuation.
- `target_de_bounds`: **pass** - Target D/E 0.170; max allowed 2.000.
- `erp_reasonableness`: **pass** - ERP 0.046 within [3%, 10%] bounds.
- `crp_reasonableness`: **pass** - CRP 0.0125 within [0%, 5%] bounds.
- `beta_adjustment_applied`: **pass** - Beta adjustment method: 'vasicek'. Vasicek or Blume required for investor-grade.
- `scenario_ordering`: **pass** - Check extreme <= bad <= base.
- `override_fundamentals_present`: **pass** - Override files are present and processed data uses override sources.
- `fundamentals_ttm_method`: **pass** - Fundamentals are derived from strict 4-quarter TTM method.
- `peer_input_coverage`: **pass** - Peer input coverage check against data/raw/<asof>/peer_fundamentals.csv.
- `peer_source_recency`: **pass** - Peer source recency check.
- `source_manifest_health`: **pass** - Source manifest ingestion status.
- `scenario_economic_consistency`: **pass** - Scenario assumptions are within configured economic bounds.
- `stress_scenario_coverage`: **pass** - 3 stress scenarios defined; minimum 2 recommended.
- `schema::wacc_components.csv`: **pass** - Schema contract for wacc_components.csv.
- `schema::valuation_outputs.csv`: **pass** - Schema contract for valuation_outputs.csv.
- `schema::valuation_method_outputs.csv`: **pass** - Schema contract for valuation_method_outputs.csv.
- `schema::valuation_ensemble.csv`: **pass** - Schema contract for valuation_ensemble.csv.
- `schema::tvalue_company_bridge.csv`: **pass** - Schema contract for tvalue_company_bridge.csv.
- `schema::reverse_dcf_outputs.csv`: **pass** - Schema contract for reverse_dcf_outputs.csv.
- `headline_nan_check`: **pass** - No NaN values in ensemble headline outputs.
- `ensemble_band_width`: **pass** - Ensemble valuation band width sanity check.
- `backtest_minimum_coverage`: **fail** - Backtest minimum coverage check.
- `backtest_quality_flag`: **fail** - Backtest quality thresholds.
- `backtest_ic_gate`: **warn** - Backtest IC (12m) 0.071; threshold 0.100.
- `backtest_calibration_slope`: **warn** - Calibration slope 0.094; |deviation from 1.0| = 0.906.
