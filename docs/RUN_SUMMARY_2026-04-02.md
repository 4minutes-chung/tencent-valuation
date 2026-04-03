# Run Summary (2026-04-02)

## Snapshot

- As-of date: `2026-04-02`
- Source mode: `live`
- Package version: `0.4.1`
- Spot price used: `489.2` HKD
- FX used (CNY/HKD): `1.1362` (`frankfurter_cnyhkd_close_2026-04-02`)
- WACC: `10.52%`

## DCF Output

| Scenario | Fair Value (HKD/share) | Margin of Safety |
|---|---:|---:|
| base | 354.36 | -27.56% |
| bad | 206.34 | -57.82% |
| extreme | 147.87 | -69.77% |

## Ensemble Output

| Scenario | Ensemble Value | Method Min | Method Max |
|---|---:|---:|---:|
| base | 361.08 | 276.83 | 445.89 |
| bad | 244.64 | 172.93 | 363.11 |
| extreme | 193.66 | 125.17 | 363.11 |
| expected | 295.21 | 193.66 | 361.08 |

## Generated Reports

- `reports/qa_2026-04-02.json`
- `reports/tencent_valuation_2026-04-02.md`
- `reports/tencent_investment_memo_2026-04-02.md`
- `reports/tencent_v4_compact_log_2026-04-02.md`

## Visual Pack

Directory: `docs/figures/2026-04-02/`

- `01_dcf_vs_market.png`
- `02_ensemble_vs_dcf.png`
- `03_method_cross_section.png`
- `04_capm_apt_diagnostics.png`
- `05_monte_carlo_distribution.png`
- `06_stress_scenarios.png`
- `07_sensitivity_wacc_g.png`
- `08_sensitivity_margin_growth.png`
- `09_backtest_scatter.png`
- `10_regime_breakdown.png`
- `11_scenario_paths.png`

## Known Limits

- Backtest warnings appear for early vintages due to limited live history coverage for some tickers.
- Relative valuation still uses proxy logic when peer fundamental columns are not provided in full.
