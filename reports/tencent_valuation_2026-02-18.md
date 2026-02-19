# Tencent Valuation Report (2026-02-18)

## WACC Summary

- WACC (CAPM-driven): `7.76%`
- Cost of Equity (CAPM official): `8.60%`
- Cost of Equity (APT guardrailed, diagnostic): `13.40%`
- Cost of Equity (APT raw): `20.09%`
- CAPM/APT gap (guardrailed): `480.8 bps`
- CAPM/APT gap (raw): `1149.8 bps`
- APT unstable gate: `TRIGGERED`
- APT stability score: `0.404`
- ERP method: `rolling_excess_return`
- Beta window (primary): `60m`
- Beta window (secondary): `36m`
- APT guardrail flags: `winsorized_factors_60m;lambda_shrunk_mkt_excess_60m;lambda_shrunk_smb_60m;lambda_shrunk_hml_60m;winsorized_factors_36m;lambda_shrunk_mkt_excess_36m;lambda_shrunk_smb_36m;lambda_shrunk_hml_36m;apt_unstable_windows;apt_unstable_beta_gap;lambda_warn_hml;apt_premia_warn;apt_unstable_gap`
- Target D/E: `0.167`
- Headline valuation policy: `APT excluded; CAPM remains official discount-rate anchor.`

## Scenario Valuation

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 575.03 | 7.88% |
| bad | 316.83 | -40.56% |
| extreme | 211.34 | -60.35% |

## QA Summary

- Total checks: `12`
- Warnings: `2`
- Failures: `1`
- Investor-grade: `NO`

## Confidence

- Confidence level: `MEDIUM-LOW` (APT instability and/or QA failures present).

- `segment_sum_to_total`: **pass** - Segment revenues reconcile to total revenue.
- `capm_apt_gap`: **warn** - CAPM/APT gap 480.8 bps; threshold 150.0 bps.
- `apt_stability_gate`: **warn** - APT diagnostic marked unstable and excluded from headline valuation.
- `target_de_bounds`: **pass** - Target D/E 0.167; max allowed 2.000.
- `scenario_ordering`: **pass** - Check extreme <= bad <= base.
- `override_fundamentals_present`: **pass** - Override files are present and processed data uses override sources.
- `fundamentals_ttm_method`: **pass** - Fundamentals are derived from strict 4-quarter TTM method.
- `peer_input_coverage`: **pass** - Peer input coverage check against data/raw/<asof>/peer_fundamentals.csv.
- `peer_source_recency`: **pass** - Peer source recency check.
- `scenario_economic_consistency`: **pass** - Scenario assumptions are within configured economic bounds.
- `backtest_minimum_coverage`: **pass** - Backtest minimum coverage check.
- `backtest_quality_flag`: **fail** - Backtest quality thresholds.
