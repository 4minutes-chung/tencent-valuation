# Example Output Snapshot (2026-02-18)

Reference run:

```bash
tencent-valuation fetch --asof 2026-02-18
tencent-valuation build-overrides --asof 2026-02-18
tencent-valuation run-all --asof 2026-02-18 --source-mode live --refresh
```

Optional:

```bash
tencent-valuation backtest --start 2024-01-01 --end 2025-12-31 --freq quarterly --source-mode live
```

Expected artifacts under project root:

- `data/model/wacc_components.csv`
- `data/model/capm_apt_compare.csv`
- `data/model/valuation_outputs.csv`
- `data/model/sensitivity_wacc_g.csv`
- `data/model/sensitivity_margin_growth.csv`
- `data/model/scenario_assumptions_used.csv`
- `reports/qa_2026-02-18.json`
- `reports/tencent_valuation_2026-02-18.md`
- `reports/tencent_investment_memo_2026-02-18.md`

Interpretation notes:

- CAPM remains official discount-rate driver.
- APT is diagnostic; unstable APT should not override CAPM valuation.
- Investor-grade status is determined by QA summary (`failures == 0` and required gates).
