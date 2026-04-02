# Example Output Snapshot (2026-02-18)

This snapshot is compatible with the current `main` (V4 command surface).

Reference run:

```bash
tencent-valuation-v4 fetch --asof 2026-02-18
tencent-valuation-v4 build-overrides --asof 2026-02-18
tencent-valuation-v4 run-all --asof 2026-02-18 --source-mode live --refresh
```

Optional backtest:

```bash
tencent-valuation-v4 backtest --start 2024-01-01 --end 2025-12-31 --freq quarterly --source-mode live
```

Expected artifacts under project root:

- `data/model/wacc_components.csv`
- `data/model/capm_apt_compare.csv`
- `data/model/valuation_outputs.csv`
- `data/model/apv_outputs.csv`
- `data/model/residual_income_outputs.csv`
- `data/model/relative_valuation_outputs.csv`
- `data/model/tvalue_company_bridge.csv`
- `data/model/reverse_dcf_outputs.csv`
- `data/model/valuation_ensemble.csv`
- `data/model/backtest_summary.csv`
- `reports/qa_2026-02-18.json`
- `reports/tencent_valuation_2026-02-18.md`
- `reports/tencent_investment_memo_2026-02-18.md`

Interpretation notes:

- CAPM remains the official discount-rate driver for headline valuation.
- APT is diagnostic; unstable APT should not override CAPM valuation.
- Investor-grade is determined by QA summary (`failures == 0` and required pass gates).
