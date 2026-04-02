# Investment Report — Tencent (0700.HK), V4 Snapshot

Date of valuation snapshot: March 19, 2026  
Model line: `main` (V4)  
Source basis: historical V4 formal report snapshot (March 19, 2026) preserved in git history

## 1) Conclusion (Investment View)

Under this V4 snapshot, Tencent appears **overvalued** versus intrinsic value in the base case.

- Market price: **HKD 550.50/share**
- Base ensemble fair value: **HKD 428.25/share**
- Implied gap vs market: **-22.2%**
- Recommendation from this model snapshot: **cautious / no margin-of-safety entry**

The model indicates that the current market price requires materially stronger long-run assumptions than the base scenario (higher terminal growth and higher sustainable margins).

## 2) Base Case Summary

| Item | Base | Bad | Extreme |
|---|---:|---:|---:|
| DCF Fair Value (HKD/share) | 455.56 | 264.90 | 181.25 |
| Ensemble Fair Value (HKD/share) | **428.25** | **272.05** | **202.85** |
| Margin of Safety vs HKD 550.50 | -17.2% | -50.6% | -63.2% |

## 3) Assumptions

### 3.1 Cost of Capital Assumptions

| Assumption | Value |
|---|---:|
| Risk-free rate (Rf) | 3.42% |
| Equity risk premium (ERP) | 4.54% |
| Country risk premium (CRP) | 1.25% |
| Levered beta (Vasicek adjusted) | 1.486 |
| Cost of equity (CAPM) | 10.17% |
| Cost of debt (Rd) | 3.43% |
| Target D/E | 0.166 |
| Tax rate | 20.0% |
| **Official WACC** | **9.11%** |

APT assumptions/diagnostics in this snapshot:
- APT implied Re (guardrailed): 12.27%
- CAPM-APT gap: 209 bps (warning)
- APT used as diagnostic only; excluded from headline WACC due instability

### 3.2 Operating Assumptions (Scenario Base)

Model structure:
- Forecast horizon: 7 years
- Mid-year discounting: enabled
- Scenario framework: base / bad / extreme

Detailed scenario assumptions:

| Year | Base Rev Growth | Base EBIT Margin | Bad Rev Growth | Bad EBIT Margin | Extreme Rev Growth | Extreme EBIT Margin |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8.0% | 36.0% | 3.0% | 33.0% | -3.0% | 30.0% |
| 2 | 8.0% | 36.5% | 3.0% | 32.8% | -2.0% | 29.5% |
| 3 | 7.5% | 36.8% | 3.0% | 32.6% | 1.0% | 29.2% |
| 4 | 7.0% | 37.0% | 3.2% | 32.5% | 2.0% | 29.0% |
| 5 | 6.5% | 37.2% | 3.3% | 32.4% | 2.5% | 28.8% |
| 6 | 6.0% | 37.3% | 3.4% | 32.3% | 3.0% | 28.6% |
| 7 | 5.5% | 37.4% | 3.5% | 32.2% | 3.0% | 28.5% |
| Terminal growth | 2.5% | - | 1.0% | - | 0.0% | - |

### 3.3 Balance Sheet / Conversion / Data Assumptions

- TTM fundamentals built from strict 4-quarter aggregation of Tencent filings.
- Filings coverage for this snapshot: 1Q2024 to 3Q2025.
- CNY/HKD conversion used for this run: ~1.1346.
- Shares outstanding used in valuation: ~9.081 bn.
- Net cash assumption in SOTP bridge: HKD 116.2 bn.
- Strategic investment value in SOTP base case: HKD 380.0 bn (haircut in downside scenarios).
- Peer comps inputs in this snapshot include proxy fundamentals (approximation risk).

### 3.4 Market-Implied Assumption Check (Reverse DCF)

At market price HKD 550.50, implied assumptions were:
- Terminal growth: **4.01%** (vs base 2.5%)
- Margin shift: **+650 bps** vs base
- Growth shift: **+352 bps** vs base

Interpretation: the market is pricing a more optimistic long-run trajectory than the base model.

## 4) Methodology

Pipeline path (v4):
1. `fetch`: source snapshots and provenance manifests.
2. `build-overrides`: filing-derived TTM fundamentals/segments.
3. `factors`: market returns, factor series, processed inputs.
4. `wacc`: CAPM official rate, APT diagnostic, leverage/tax adjustments.
5. Core and cross-check valuation methods:
   - DCF (FCFF + terminal value)
   - APV (unlevered value + tax shield)
   - Residual Income (book value + PV residual incomes)
   - Relative/Comps (peer multiples)
   - SOTP/T-value (segment operating value + investments + net cash)
6. `ensemble`: weighted aggregation across methods.
7. `qa`: gate checks for schema, assumptions, stability, and backtest quality.
8. `report`: valuation and memo outputs.

Method intent:
- DCF/APV: core intrinsic valuation anchors.
- Residual income: accounting-consistency cross-check.
- Comps: market-relative cross-check.
- SOTP: strategic portfolio optionality and segment bridge.
- Reverse DCF: market expectation decomposition.

## 5) Method Output Snapshot (Base Scenario)

| Method | Fair Value (HKD/share) | Ensemble Weight |
|---|---:|---:|
| DCF | 455.56 | 36.1% |
| APV | 455.56 | 20.6% |
| Residual Income | 343.50 | 15.5% |
| Relative / Comps | 342.02 | 13.9% |
| SOTP / T-Value | 497.40 | 13.9% |
| **Ensemble** | **428.25** | **100%** |

## 6) Validation, QA, and Risk Context

Validation snapshot:
- Backtest points: 8
- 12m directional hit rate: 75%
- Calibration MAE (bucket): 0.348 (near threshold)

QA summary:
- Total checks: 21
- Failures: 0
- Warnings: 2
- Investor-grade: YES

Primary flagged risks:
1. APT instability (CAPM/APT divergence).
2. Data vintage (TTM through 2025-Q3 in this snapshot).
3. Peer comps approximation risk from proxy peer fundamentals.
4. Limited statistical power from small backtest sample.
5. Regulatory/macro scenario risk (gaming, fintech regulation, geopolitics, FX).

## 7) Final Decision Statement

Using this v4 snapshot as-of March 19, 2026, the model does **not** indicate a margin-of-safety buy at HKD 550.50.

- Base intrinsic value is below market.
- Downside scenarios imply materially larger valuation compression.
- Upside to current price requires optimistic growth and margin assumptions versus modeled base.

Decision from this report: **neutral-to-defensive stance until either price resets or fundamentals exceed the implied market trajectory.**
