# V4 Main Documentation

Last updated: April 1, 2026

## 1) Scope and Intent

This document describes the operational behavior of the current `main` branch (V4) in this repository.

Important naming note:
- Public CLI and package identity: V4 (`tencent-valuation-v4`, version `0.4.1`)
- Internal module path: `src/tencent_valuation_v3/` (kept for backward compatibility)

## 2) End-to-End Pipeline

The orchestration entrypoint is `src/tencent_valuation_v3/pipeline.py`.

High-level flow for `run-all --asof <date>`:
1. Load config and path context.
2. Snapshot source manifest metadata into `data/raw/<asof>/pipeline_manifest.json`.
3. Build factors and market inputs.
4. Run WACC (CAPM official, APT diagnostic/guardrailed).
5. Run DCF core valuation.
6. Run additional methods: APV, residual income, comps, T-value, reverse DCF, EVA, Monte Carlo, real options, stress.
7. Run backtest (`2018-01-01` to `<asof>`, quarterly).
8. Run QA checks.
9. Run ensemble aggregation.
10. Write report outputs (valuation report, investment memo, compact log).

## 3) CLI Contract

Primary command:

```bash
tencent-valuation-v4 --help
```

Subcommands:
- Data prep: `fetch`, `build-overrides`, `factors`
- Core valuation: `wacc`, `dcf`
- Additional methods: `apv`, `residual-income`, `comps`, `tvalue`, `reverse-dcf`, `monte-carlo`, `eva`, `real-options`, `stress`
- Validation/reporting: `ensemble`, `qa`, `report`, `backtest`, `run-all`

Each valuation/report command accepts `--asof YYYY-MM-DD` and optional `--source-mode auto|live|synthetic`.

## 4) Source Modes

`run_factors()` supports three source modes:

- `live`: uses external sources (Stooq, Ken French, U.S. Treasury). Fails hard on live-fetch errors.
- `auto`: tries `live`, falls back to synthetic with warning if live fetch fails.
- `synthetic`: deterministic generated market/factor series (seeded by `asof`) and optional overrides.

Manifest behavior:
- `fetch` writes `data/raw/<asof>/source_manifest.json`.
- factors build writes `data/raw/<asof>/factors_source_manifest.json`.
- pipeline writes `data/raw/<asof>/pipeline_manifest.json`.

## 5) Data Contracts

### Required config files
- `config/wacc.yaml`
- `config/qa_gates.yaml`
- `config/peers.yaml`
- `config/scenarios.yaml`
- `config/method_weights.yaml`
- `config/sources.yaml`

### Override input files (optional but strongly recommended)
Location: `data/raw/<asof>/`

`tencent_financials.csv` required columns:
- `asof`
- `revenue_hkd_bn`
- `ebit_margin`
- `capex_pct_revenue`
- `nwc_pct_revenue`
- `dep_pct_revenue`
- `net_cash_hkd_bn`
- `shares_out_bn`
- `current_price_hkd`

`segment_revenue.csv` required columns:
- `period`
- `segment`
- `revenue_hkd_bn`
- `total_revenue_hkd_bn`

`peer_fundamentals.csv` minimum columns for market input override:
- `ticker`
- `gross_debt_hkd_bn`
- `interest_expense_hkd_bn_3y_avg`
- `effective_tax_rate_3y_avg`
- `shares_out_bn`

For richer comps behavior, include additional fundamentals used by comps:
- `net_income_hkd_bn`
- `book_value_hkd_bn`
- `ebit_hkd_bn`
- `fcf_hkd_bn`

## 6) Output Contracts

### Processed layer (`data/processed/`)
- `weekly_returns.csv`
- `monthly_factors.csv`
- `monthly_asset_returns.csv`
- `market_inputs.csv`
- `tencent_financials.csv`
- `segment_revenue.csv`
- `tencent_quarterly_financials.csv` (from override builder)

### Model layer (`data/model/`)
- WACC: `wacc_components.csv`, `capm_apt_compare.csv`, `peer_beta_table.csv`
- DCF core: `valuation_outputs.csv`, `sensitivity_wacc_g.csv`, `sensitivity_margin_growth.csv`, `scenario_assumptions_used.csv`
- Additional methods: `apv_outputs.csv`, `residual_income_outputs.csv`, `peer_multiples.csv`, `relative_valuation_outputs.csv`, `tvalue_company_bridge.csv`, `tvalue_stat_diagnostics.csv`, `reverse_dcf_outputs.csv`, `eva_outputs.csv`, `monte_carlo_outputs.csv`, `monte_carlo_percentiles.csv`, `real_options_outputs.csv`, `stress_scenario_outputs.csv`
- Ensemble: `valuation_method_outputs.csv`, `valuation_ensemble.csv`
- Backtest: `backtest_summary.csv`, `backtest_point_results.csv`, `backtest_regime_breakdown.csv`

### Reports layer (`reports/`)
- `qa_<asof>.json`
- `tencent_valuation_<asof>.md`
- `tencent_investment_memo_<asof>.md`
- `tencent_v4_compact_log_<asof>.md`

Legacy/manual artifacts are intentionally not kept in current `main`; use git history for older deliverables.

## 7) QA Behavior

`run_qa()` produces pass/warn/fail checks and summary counts.

Notable gates include:
- Structure/value sanity: scenario ordering, CAPM/APT gap, D/E bounds, ERP/CRP ranges.
- Data readiness: override fundamentals present, strict TTM method, peer input coverage, source manifest health.
- Output contracts: schema checks for core model outputs.
- Headline quality: no NaN headline ensemble outputs, ensemble band width sanity.
- Backtest checks: minimum coverage, quality flag, IC gate, calibration slope.

Investor-grade requires:
- zero `fail` checks
- `override_fundamentals_present == pass`
- `fundamentals_ttm_method == pass`
- `backtest_minimum_coverage == pass`

CI nuance:
- `backtest_quality_flag` is currently non-blocking in CI.

## 8) Test and CI State

Current test snapshot (April 1, 2026):
- `pytest -q`: `183 passed, 24 skipped`

CI workflow (`.github/workflows/ci.yml`):
- installs package in editable mode
- runs `python -m unittest discover -s tests -v`
- runs synthetic `run-all` and `qa`
- enforces QA gate with only `backtest_quality_flag` treated as non-blocking

## 9) Operational Recommendations

1. For daily production-like runs, use `--source-mode auto` plus override files.
2. For reproducible development and CI, use `--source-mode synthetic`.
3. Keep override CSVs complete to avoid proxy fallbacks in comps/residual-income modules.
4. Treat generated data/report artifacts as outputs; regenerate intentionally with clear `asof` context.

## 10) Troubleshooting Quick Guide

- Error: missing config peers/scenarios/weights
  - verify all YAML files exist under `config/` and are valid.

- Error: live fetch failures
  - use `--source-mode auto` (fallback) or `--source-mode synthetic` for offline runs.

- QA fail on override fundamentals or TTM method
  - run `build-overrides --asof <date>` and verify `data/raw/<asof>/tencent_financials.csv`.

- Comps warnings about proxy multiples
  - enrich `peer_fundamentals.csv` with `net_income_hkd_bn`, `book_value_hkd_bn`, `ebit_hkd_bn`, and `fcf_hkd_bn`.

## 11) Investment Report

For a complete investment write-up (assumptions, base case, methodology, and conclusion), see:

- `docs/INVESTMENT_REPORT_V4_2026-03-19.md` (formal narrative snapshot)
- `docs/RUN_SUMMARY_2026-04-02.md` (latest run table + outputs + visual pack)

These are date-stamped valuation snapshots and should be regenerated/updated for new as-of dates.
