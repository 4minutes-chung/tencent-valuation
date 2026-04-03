# Full Model Assumptions (2026-04-02 Snapshot)

## Scope

This register captures the active assumptions used by the live V4 run for Tencent (`0700.HK`) as-of `2026-04-02`.
It is intended to be the complete non-code assumption reference for this snapshot.

## Snapshot Identity

- As-of date: `2026-04-02`
- Source mode: `live`
- Parser version: `v4.0`
- Package/CLI line: `tencent-valuation-v4` (`0.4.1`)
- Canonical module path: `src/tencent_valuation_v4/`

## 1) Data and Provenance Assumptions

| Item | Configured Basis | Realized in Snapshot |
|---|---|---|
| Primary price source | Live market source chain | `tencent_ifzq_gtimg (fallback: stooq, yahoo)` |
| Factor source | Ken French APAC ex-Japan 3 factors zip | Pulled from configured URL and parsed successfully |
| Risk-free source | US Treasury daily yield CSV | 2026 Treasury daily curve snapshot ingested |
| Fundamentals source | Override inputs expected in `data/raw/<asof>/` | `override_csv` (strict TTM build from quarterly filings) |
| Segment source | Override segment table expected in `data/raw/<asof>/` | `override_csv` |
| Peer fundamentals source | `data/raw/<asof>/peer_fundamentals.csv` | Present and passed coverage/recency checks |
| FX fallback | `fx_fallback_cny_hkd = 1.08` | Not used; realized FX `1.1362` (`frankfurter_cnyhkd_close_2026-04-02`) |
| Market-price fallback | `fallback_market_price_hkd = 533.0` | Not used; realized market price `489.2` HKD |

## 2) Cost-of-Capital Assumptions

### 2.1 Structural settings

- `rf_method`: `current_10y`
- `erp_method`: `rolling_excess_return` with `erp_lookback_months = 60`
- Beta window settings:
  - primary: `104w`
  - secondary: `156w` and `60m` diagnostics
- Beta adjustment: `vasicek`
- Cost of debt method: `synthetic_spread` with `rd_spread_bps = 150`
- Country risk premium (`CRP`): `1.25%`

### 2.2 Realized values

| Parameter | Realized Value |
|---|---:|
| Risk-free rate (`Rf`) | `4.13%` |
| Equity risk premium (`ERP`) | `4.63%` |
| Levered beta (raw) | `1.476` |
| Levered beta (Vasicek-adjusted) | `1.342` |
| CAPM cost of equity (`Re`) | `11.59%` |
| APT diagnostic `Re` (guardrailed) | `12.76%` |
| Cost of debt (`Rd`) | `5.63%` |
| Target D/E | `0.179` |
| Tax rate | `20.0%` |
| Official WACC | `10.52%` |

### 2.3 APT guardrail and stability assumptions

- CAPM/APT alert threshold: `150 bps` (realized gap `117.1 bps`, pass).
- APT instability threshold: `400 bps` across windows.
- APT stability windows: `24m`, `36m`, `60m`.
- Realized APT stability status: `unstable = true`.
- Recorded reason code: `window_instability`.
- Realized max cross-window gap: `480.9 bps`.
- Realized max cross-window beta gap: `1.283`.

Interpretation rule: APT is diagnostic-only when instability gates fail.

## 3) Operating and Scenario Assumptions

### 3.1 Forecast framework

- Horizon: `7 years`
- Discounting: `mid_year_discounting = true`
- Terminal value method: Gordon growth
- Scenarios: `base`, `bad`, `extreme`

### 3.2 Scenario paths (configured and used)

#### Base
- `terminal_g = 2.5%`
- `revenue_growth = [8.0%, 8.0%, 7.5%, 7.0%, 6.5%, 6.0%, 5.5%]`
- `ebit_margin = [36.0%, 36.5%, 36.8%, 37.0%, 37.2%, 37.3%, 37.4%]`
- `capex_pct_revenue = [9.0%, 9.0%, 8.8%, 8.6%, 8.5%, 8.4%, 8.3%]`
- `nwc_pct_revenue = [2.0%, 2.0%, 1.9%, 1.9%, 1.8%, 1.8%, 1.8%]`
- `sbc_pct_revenue = [1.5%, 1.5%, 1.4%, 1.4%, 1.3%, 1.3%, 1.2%]`
- `annual_buyback_hkd_bn = 40.0`

#### Bad
- `terminal_g = 1.0%`
- `revenue_growth = [3.0%, 3.0%, 3.0%, 3.2%, 3.3%, 3.4%, 3.5%]`
- `ebit_margin = [33.0%, 32.8%, 32.6%, 32.5%, 32.4%, 32.3%, 32.2%]`
- `capex_pct_revenue = [9.5%, 9.5%, 9.4%, 9.3%, 9.2%, 9.1%, 9.0%]`
- `nwc_pct_revenue = [2.2%, 2.2%, 2.2%, 2.1%, 2.1%, 2.1%, 2.1%]`
- `sbc_pct_revenue = [1.6%, 1.6%, 1.5%, 1.5%, 1.5%, 1.5%, 1.5%]`
- `annual_buyback_hkd_bn = 20.0`

#### Extreme
- `terminal_g = 0.0%`
- `revenue_growth = [-3.0%, -2.0%, 1.0%, 2.0%, 2.5%, 3.0%, 3.0%]`
- `ebit_margin = [30.0%, 29.5%, 29.2%, 29.0%, 28.8%, 28.6%, 28.5%]`
- `capex_pct_revenue = [10.0%, 10.0%, 10.0%, 9.8%, 9.7%, 9.6%, 9.5%]`
- `nwc_pct_revenue = [2.4%, 2.4%, 2.4%, 2.3%, 2.3%, 2.3%, 2.3%]`
- `sbc_pct_revenue = [1.8%, 1.8%, 1.7%, 1.6%, 1.5%, 1.5%, 1.5%]`
- `annual_buyback_hkd_bn = 0.0`

### 3.3 Stress scenario overlays

- `gaming_crackdown` (probability `0.05`)
- `fintech_regulation` (probability `0.08`)
- `us_china_escalation` (probability `0.10`, includes `+100 bps` WACC adder)

## 4) Method Aggregation Assumptions

### 4.1 Configured base method weights

| Method | Config Weight |
|---|---:|
| DCF | `0.25` |
| APV | `0.15` |
| Residual Income | `0.10` |
| Relative | `0.10` |
| SOTP/T-value | `0.15` |
| EVA | `0.10` |
| Monte Carlo | `0.10` |
| Real Options | `0.05` |

Penalty factors configured:
- `apt_unstable_penalty = 0.90`
- `backtest_quality_penalty = 0.85`

### 4.2 Realized normalized base-scenario weights

| Method | Realized Weight |
|---|---:|
| DCF | `0.2641` |
| APV | `0.1585` |
| Residual Income | `0.0898` |
| Relative | `0.0808` |
| SOTP/T-value | `0.1426` |
| EVA | `0.1057` |
| Monte Carlo | `0.1057` |
| Real Options | `0.0528` |

## 5) QA Gate Assumptions and Outcomes

### 5.1 Key configured gates

- Peer source max age: `18 months`
- Backtest minimum points: `20`
- Minimum 12m hit rate: `0.45`
- Max calibration MAE (12m, bucket): `0.35`
- Minimum interval coverage (12m): `0.40`
- Minimum IC (12m): `0.10`
- Max calibration slope deviation from 1.0: `0.50`
- Headline max ensemble band-width ratio: `3.5`

### 5.2 Realized QA summary

- Total checks: `27`
- `pass = 23`, `warn = 2`, `fail = 2`
- Investor-grade: `false`

Warn checks:
- `apt_stability_gate`
- `backtest_calibration_slope`

Fail checks:
- `backtest_minimum_coverage` (`13` points vs min `20`)
- `backtest_quality_flag` (interval coverage and calibration profile below configured gates)

## 6) Embedded Valuation Conclusions

- DCF fair value (`base`): `354.36` HKD/share (`-27.56%` vs market `489.2`)
- Ensemble fair value (`base`): `361.08` HKD/share (`-26.20%` vs market `489.2`)
- Ensemble expected value: `295.21` HKD/share
- Reverse DCF at market:
  - implied terminal growth: `5.043%`
  - implied margin shift: `+950.5 bps`
  - implied growth shift: `+510.6 bps`

## 7) Reproducibility

Command sequence for this assumption set:

```bash
tencent-valuation-v4 fetch --asof 2026-04-02
tencent-valuation-v4 build-overrides --asof 2026-04-02
tencent-valuation-v4 run-all --asof 2026-04-02 --source-mode live --refresh
python scripts/generate_v4_visuals.py --asof 2026-04-02
```

Primary evidence files:
- `data/raw/2026-04-02/factors_source_manifest.json`
- `data/raw/2026-04-02/source_manifest.json`
- `data/model/wacc_components.csv`
- `data/model/scenario_assumptions_used.csv`
- `data/model/valuation_outputs.csv`
- `data/model/valuation_ensemble.csv`
- `reports/qa_2026-04-02.json`
