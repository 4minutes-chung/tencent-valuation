# Tencent Valuation Pipeline

Investor-oriented Tencent (`0700.HK`) valuation pipeline with:
- MM/Hamada target-structure beta logic.
- CAPM as official cost-of-equity for valuation.
- APT as guardrailed diagnostic only.
- 3-scenario DCF (`base`, `bad`, `extreme`) plus sensitivities.

## Core Policy

- Official WACC uses `Re_CAPM` only.
- APT is cross-check/diagnostic. If unstable, it is excluded from headline valuation.
- Investor-grade status requires:
  - override fundamentals present,
  - strict TTM method from quarterly series,
  - zero QA failures.

## Runbook (Per As-Of Date)

```bash
# 1) Snapshot source pages/files
tencent-valuation fetch --asof 2026-02-18

# 2) Build filing-derived override pack (quarterly -> strict TTM)
tencent-valuation build-overrides --asof 2026-02-18

# 3) Run valuation pipeline
tencent-valuation run-all --asof 2026-02-18 --source-mode live --refresh

# 4) Optional validation run
tencent-valuation backtest --start 2024-01-01 --end 2025-12-31 --freq quarterly --source-mode live
```

Deterministic CI/local mode:

```bash
tencent-valuation run-all --asof 2026-02-18 --source-mode synthetic --refresh
```

## CLI

```bash
tencent-valuation fetch --asof YYYY-MM-DD
tencent-valuation build-overrides --asof YYYY-MM-DD
tencent-valuation factors --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh]
tencent-valuation wacc --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation value --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation qa --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation report --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation backtest --start YYYY-MM-DD --end YYYY-MM-DD --freq quarterly [--source-mode auto|live|synthetic]
tencent-valuation run-all --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh]
```

## Config

- `config/wacc.yaml`: CAPM/APT/WACC controls, guardrails, ERP method, investor-grade override requirement.
- `config/peers.yaml`: peer universe for target leverage.
- `config/scenarios.yaml`: DCF assumptions and sensitivity grids.
- `config/qa_gates.yaml`: QA pass/warn/fail thresholds.

## Input Contracts

### Quarterly Canonical Dataset

- `data/processed/tencent_quarterly_financials.csv`
- Columns:
  - `period_end`
  - `revenue_rmb_bn`
  - `non_ifrs_op_profit_rmb_bn`
  - `capex_rmb_bn`
  - `net_cash_rmb_bn`
  - `shares_out_bn`
  - `source_doc`
  - `source_page_hint`

### Override Fundamentals (as-of)

- `data/raw/<asof>/tencent_financials.csv` required columns:
  - `asof,revenue_hkd_bn,ebit_margin,capex_pct_revenue,nwc_pct_revenue,dep_pct_revenue,net_cash_hkd_bn,shares_out_bn,current_price_hkd`
- `data/raw/<asof>/segment_revenue.csv` required columns:
  - `period,segment,revenue_hkd_bn,total_revenue_hkd_bn`
- `data/raw/<asof>/peer_fundamentals.csv` required columns:
  - `ticker,gross_debt_hkd_bn,interest_expense_hkd_bn_3y_avg,effective_tax_rate_3y_avg,shares_out_bn`

## Primary Outputs

- `data/model/wacc_components.csv`
- `data/model/capm_apt_compare.csv`
- `data/model/valuation_outputs.csv`
- `data/model/sensitivity_wacc_g.csv`
- `data/model/sensitivity_margin_growth.csv`
- `data/model/scenario_assumptions_used.csv`
- `data/model/backtest_summary.csv`
- `data/model/backtest_point_results.csv`
- `reports/qa_<asof>.json`
- `reports/tencent_valuation_<asof>.md`
- `reports/tencent_investment_memo_<asof>.md`

## QA Notes

- `override_fundamentals_present`: fails if override files are missing when required.
- `fundamentals_ttm_method`: fails if method is not strict `ttm_4q_from_quarterly`.
- `apt_stability_gate`: warns when APT is unstable.
- `peer_input_coverage`: fails if configured peers are missing in peer fundamentals.
- `scenario_ordering`: validates `extreme <= bad <= base`.
