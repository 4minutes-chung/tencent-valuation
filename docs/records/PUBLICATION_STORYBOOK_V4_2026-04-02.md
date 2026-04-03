# Tencent Valuation V4 Storybook (Publishable Snapshot)

As-of date: `2026-04-02`  
Pipeline line: `main` (V4)

## 1) Headline Conclusion

The current live snapshot points to an overvaluation setup versus intrinsic value estimates.

- Market price: `HKD 489.20/share`
- Base DCF fair value: `HKD 354.36/share` (`-27.6%`)
- Base ensemble fair value: `HKD 361.08/share` (`-26.2%`)
- Headline stance: `cautious / no margin-of-safety entry at current price`

## 2) Assumptions (Current Snapshot)

### 2.1 Cost of Capital

| Assumption | Value |
|---|---:|
| Risk-free rate (`Rf`) | `4.13%` |
| Equity risk premium (`ERP`) | `4.63%` |
| Country risk premium (`CRP`) | `1.25%` |
| Levered beta (Vasicek-adjusted) | `1.342` |
| CAPM cost of equity (`Re`) | `11.59%` |
| Cost of debt (`Rd`) | `5.63%` |
| Target D/E | `0.179` |
| Tax rate | `20.0%` |
| Official WACC | `10.52%` |

### 2.2 Scenario Structure

- Forecast horizon: `7 years`
- Scenarios: `base`, `bad`, `extreme`
- Methods in stack: DCF, APV, residual income, comps, SOTP/T-value, EVA, Monte Carlo, real options, ensemble

## 3) Base Case Results

| Scenario | DCF Fair Value (HKD/share) | Ensemble Fair Value (HKD/share) | Margin of Safety vs HKD 489.20 |
|---|---:|---:|---:|
| Base | `354.36` | `361.08` | `-27.6%` (DCF), `-26.2%` (ensemble) |
| Bad | `206.34` | `244.64` | `-57.8%` (DCF), `-50.0%` (ensemble) |
| Extreme | `147.87` | `193.66` | `-69.8%` (DCF), `-60.4%` (ensemble) |

Reverse DCF (market-implied):
- Implied terminal growth at market: `5.04%`
- Implied margin shift vs base: `+951 bps`
- Implied growth shift vs base: `+511 bps`

Interpretation: market price implies stronger long-run assumptions than the current base-case operating path.

## 4) Methodology

Valuation stack:
1. DCF (FCFF + terminal value)
2. APV (unlevered value + tax shield)
3. Residual Income
4. Relative valuation (comps)
5. SOTP / T-Value
6. EVA
7. Monte Carlo
8. Real options
9. Ensemble weighting

Controls:
- QA gates (`pass`/`warn`/`fail`)
- Backtest diagnostics
- Output schema contracts

## 5) QA Snapshot

- Total checks: `27`
- Status split: `23 pass`, `2 warn`, `2 fail`
- Investor-grade gate: `false`

Main warning/fail themes are model calibration quality and proxy dependence in peer-fundamental inputs.

## 6) Visual Evidence Pack

### 6.1 Core valuation gap
![DCF vs market](figures/2026-04-02/01_dcf_vs_market.png)

### 6.2 Ensemble vs DCF
![Ensemble vs DCF](figures/2026-04-02/02_ensemble_vs_dcf.png)

### 6.3 Method cross-section (base)
![Method cross section](figures/2026-04-02/03_method_cross_section.png)

### 6.4 Cost-of-equity diagnostics
![CAPM APT diagnostics](figures/2026-04-02/04_capm_apt_diagnostics.png)

### 6.5 Monte Carlo distribution
![Monte Carlo distribution](figures/2026-04-02/05_monte_carlo_distribution.png)

### 6.6 Stress scenarios
![Stress scenarios](figures/2026-04-02/06_stress_scenarios.png)

### 6.7 WACC-growth sensitivity
![WACC growth sensitivity](figures/2026-04-02/07_sensitivity_wacc_g.png)

### 6.8 Margin-growth sensitivity
![Margin growth sensitivity](figures/2026-04-02/08_sensitivity_margin_growth.png)

### 6.9 Backtest signal-quality scatter
![Backtest scatter](figures/2026-04-02/09_backtest_scatter.png)

### 6.10 Regime hit-rate view
![Regime breakdown](figures/2026-04-02/10_regime_breakdown.png)

### 6.11 Scenario assumption paths
![Scenario paths](figures/2026-04-02/11_scenario_paths.png)

## 7) Final Decision Statement

Current live snapshot decision:
- Tencent screens as overvalued relative to both base DCF and base ensemble values.
- Preferred action is patience and entry discipline until assumptions or price reset improve margin of safety.
