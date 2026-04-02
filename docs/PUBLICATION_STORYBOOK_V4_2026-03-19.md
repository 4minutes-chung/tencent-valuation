# Tencent Valuation V4 Storybook (Publishable Snapshot)

As-of date: `2026-03-19`  
Pipeline line: `main` (V4)

## 1) Headline Conclusion (Calibrated Snapshot)

The headline investment view is based on the calibrated March 19, 2026 valuation snapshot.

- Market price: `HKD 550.50/share`
- Base DCF fair value: `HKD 455.56/share` (`-17.2%`)
- Base ensemble fair value: `HKD 428.25/share` (`-22.2%`)
- Headline stance: `cautious / no margin-of-safety entry at current price`

This is a **moderate overvaluation call**, not a crash call.

## 2) Assumptions (Headline Case)

### 2.1 Cost of Capital

| Assumption | Value |
|---|---:|
| Risk-free rate (`Rf`) | `3.42%` |
| Equity risk premium (`ERP`) | `4.54%` |
| Country risk premium (`CRP`) | `1.25%` |
| Levered beta (Vasicek-adjusted) | `1.486` |
| CAPM cost of equity (`Re`) | `10.17%` |
| Cost of debt (`Rd`) | `3.43%` |
| Target D/E | `0.166` |
| Tax rate | `20.0%` |
| Official WACC | `9.11%` |

### 2.2 Scenario Structure

- Forecast horizon: `7 years`
- Scenarios: `base`, `bad`, `extreme`
- Methods in stack: DCF, APV, residual income, comps, SOTP/T-value, EVA, Monte Carlo, real options, ensemble

## 3) Base Case Results (Headline Case)

| Scenario | DCF Fair Value (HKD/share) | Ensemble Fair Value (HKD/share) | Margin of Safety vs HKD 550.50 |
|---|---:|---:|---:|
| Base | `455.56` | `428.25` | `-17.2%` (DCF), `-22.2%` (ensemble) |
| Bad | `264.90` | `272.05` | `-51.9%` (DCF), `-50.6%` (ensemble) |
| Extreme | `181.25` | `202.85` | `-67.1%` (DCF), `-63.2%` (ensemble) |

Reverse DCF (headline case):
- Implied terminal growth at market: `4.01%`
- Implied margin shift vs base: `+650 bps`
- Implied growth shift vs base: `+352 bps`

Interpretation: market price requires stronger long-run assumptions than base, but not implausible crash dynamics.

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

## 5) Diagnostic Synthetic Run (Non-Headline)

The repository also contains a fully reproducible synthetic rerun used for engineering verification.
That run produced much harsher fair values (including around `-67%` base margin of safety) because discount-rate inputs were far tighter:

- WACC near `16.75%`
- ERP near `15.8%`
- CAPM/APT gap warning and non-investor-grade QA

This synthetic output is retained for stress-testing and code verification, **not** as the headline investment conclusion.

## 6) Visual Evidence Pack

The charts below are generated from the reproducible synthetic diagnostic run and are best read as sensitivity and stress visuals.

### 6.1 Core valuation gap
![DCF vs market](figures/2026-03-19/01_dcf_vs_market.png)

### 6.2 Ensemble vs DCF
![Ensemble vs DCF](figures/2026-03-19/02_ensemble_vs_dcf.png)

### 6.3 Method cross-section (base)
![Method cross section](figures/2026-03-19/03_method_cross_section.png)

### 6.4 Cost-of-equity diagnostics
![CAPM APT diagnostics](figures/2026-03-19/04_capm_apt_diagnostics.png)

### 6.5 Monte Carlo distribution
![Monte Carlo distribution](figures/2026-03-19/05_monte_carlo_distribution.png)

### 6.6 Stress scenarios
![Stress scenarios](figures/2026-03-19/06_stress_scenarios.png)

### 6.7 WACC-growth sensitivity
![WACC growth sensitivity](figures/2026-03-19/07_sensitivity_wacc_g.png)

### 6.8 Margin-growth sensitivity
![Margin growth sensitivity](figures/2026-03-19/08_sensitivity_margin_growth.png)

### 6.9 Backtest signal-quality scatter
![Backtest scatter](figures/2026-03-19/09_backtest_scatter.png)

### 6.10 Regime hit-rate view
![Regime breakdown](figures/2026-03-19/10_regime_breakdown.png)

### 6.11 Scenario assumption paths
![Scenario paths](figures/2026-03-19/11_scenario_paths.png)

## 7) Final Decision Statement

Headline decision (calibrated March 19, 2026 case):
- Tencent screens as moderately overvalued at current market price.
- Preferred action is patience and entry discipline, not panic de-risking based on an extreme synthetic run.
