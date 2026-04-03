# Run Ledger (2026-04-02 Snapshot)

## Purpose

This document is the step-by-step execution log for the live V4 snapshot as-of `2026-04-02`.
It records commands, internal pipeline stages, data provenance artifacts, and resulting outputs.

## 1) Execution Identity

- As-of date: `2026-04-02`
- Run mode: `live`
- Parser version: `v4.0`
- Manifest timestamp (UTC): `2026-04-03T00:24:10.069435+00:00`
- Package version: `0.4.1`
- Branch line during release docs: `codex/v4.1`

## 2) Operator Command Ledger

| Step | Command | Status | Evidence |
|---|---|---|---|
| 1 | `tencent-valuation-v4 fetch --asof 2026-04-02` | pass | `data/raw/2026-04-02/fetch_manifest.json` |
| 2 | `tencent-valuation-v4 build-overrides --asof 2026-04-02` | pass | `data/raw/2026-04-02/tencent_financials.csv`, `segment_revenue.csv` |
| 3 | `tencent-valuation-v4 run-all --asof 2026-04-02 --source-mode live --refresh` | pass | `reports/tencent_v4_compact_log_2026-04-02.md`, `data/model/*.csv` |
| 4 | `python scripts/generate_v4_visuals.py --asof 2026-04-02` | pass | `docs/figures/2026-04-02/*.png` |
| 5 | `ruff check .` | pass | release verification note |
| 6 | `pytest -q` | pass (`183 passed, 24 skipped`) | release verification note |

## 3) Internal `run-all` Stage Ledger

Recorded in `reports/tencent_v4_compact_log_2026-04-02.md`:

1. `fetch`
2. `build-overrides`
3. `factors`
4. `wacc`
5. `dcf/apv/residual/comps/tvalue/reverse-dcf`
6. `ensemble`
7. `qa/report`

## 4) Raw Source Provenance Ledger

### 4.1 Fetch/source manifests

- `data/raw/2026-04-02/source_manifest.json`
- `data/raw/2026-04-02/fetch_manifest.json`
- `data/raw/2026-04-02/factors_source_manifest.json`
- `data/raw/2026-04-02/pipeline_manifest.json`

### 4.2 Source entries captured

| Source name | Status | Bytes | SHA256 (prefix) |
|---|---|---:|---|
| `tencent_ir_financial_news` | ok | `305806` | `bb99513c9f0a` |
| `hkex_title_search` | ok | `12281` | `12bca3f22baf` |
| `hkex_ccass` | ok | `583809` | `a96c9ebf68a4` |
| `sfc_short_positions` | ok | `137492` | `f3d088e20c4c` |
| `ken_french_apac_3f` | ok | `5027` | `39661aac9950` |
| `ust_daily_yield` | ok | `5213` | `20d57474ee8b` |

## 5) Model Output Ledger

### 5.1 WACC and capital assumptions (realized)

- `Rf = 4.13%`
- `ERP = 4.63%`
- `beta (Vasicek-adjusted) = 1.342`
- `CAPM Re = 11.59%`
- `APT Re (diagnostic, guardrailed) = 12.76%`
- `Rd = 5.63%`
- `WACC = 10.52%`
- `APT unstable = true` (`window_instability`)

Evidence: `data/model/wacc_components.csv`

### 5.2 DCF outputs

| Scenario | Fair Value (HKD/share) | Margin of Safety vs 489.2 |
|---|---:|---:|
| base | `354.36` | `-27.56%` |
| bad | `206.34` | `-57.82%` |
| extreme | `147.87` | `-69.77%` |

Evidence: `data/model/valuation_outputs.csv`

### 5.3 Ensemble outputs

| Scenario | Ensemble Value | Min Method | Max Method |
|---|---:|---:|---:|
| base | `361.08` | `276.83` | `445.89` |
| bad | `244.64` | `172.93` | `363.11` |
| extreme | `193.66` | `125.17` | `363.11` |
| expected | `295.21` | `193.66` | `361.08` |

Evidence: `data/model/valuation_ensemble.csv`

### 5.4 Reverse DCF outputs

- Market price: `489.2`
- Implied terminal growth: `5.043%`
- Implied margin shift: `+950.5 bps`
- Implied growth shift: `+510.6 bps`

Evidence: `data/model/reverse_dcf_outputs.csv`

## 6) QA and Gate Ledger

Summary from `reports/qa_2026-04-02.json`:

- Total checks: `27`
- Pass: `23`
- Warn: `2`
- Fail: `2`
- Investor-grade: `false`

Warn checks:
- `apt_stability_gate`
- `backtest_calibration_slope`

Fail checks:
- `backtest_minimum_coverage` (`13` observed vs minimum `20`)
- `backtest_quality_flag` (coverage/calibration thresholds not met)

## 7) Visual Artifact Ledger

Generated under `docs/figures/2026-04-02/`:

1. `01_dcf_vs_market.png`
2. `02_ensemble_vs_dcf.png`
3. `03_method_cross_section.png`
4. `04_capm_apt_diagnostics.png`
5. `05_monte_carlo_distribution.png`
6. `06_stress_scenarios.png`
7. `07_sensitivity_wacc_g.png`
8. `08_sensitivity_margin_growth.png`
9. `09_backtest_scatter.png`
10. `10_regime_breakdown.png`
11. `11_scenario_paths.png`

## 8) Reproduction Checklist

1. Use the same as-of date (`2026-04-02`) and `--source-mode live`.
2. Ensure override inputs exist under `data/raw/2026-04-02/`.
3. Re-run commands in section 2 in order.
4. Verify:
   - manifests generated under `data/raw/2026-04-02/`
   - model outputs generated under `data/model/`
   - QA summary matches `27 / 2 warn / 2 fail`
   - chart pack contains 11 files under `docs/figures/2026-04-02/`
