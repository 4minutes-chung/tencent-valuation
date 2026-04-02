# Example Output Snapshot (2026-02-19)

This example reflects a full run on the current repository layout (`main`, V4 CLI).

Reference run:

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent_Model"
tencent-valuation-v4 fetch --asof 2026-02-19
tencent-valuation-v4 build-overrides --asof 2026-02-19
tencent-valuation-v4 run-all --asof 2026-02-19 --source-mode live --refresh
```

## Key Outputs

- `data/model/wacc_components.csv`
- `data/model/valuation_outputs.csv`
- `data/model/apv_outputs.csv`
- `data/model/residual_income_outputs.csv`
- `data/model/relative_valuation_outputs.csv`
- `data/model/tvalue_company_bridge.csv`
- `data/model/tvalue_stat_diagnostics.csv`
- `data/model/reverse_dcf_outputs.csv`
- `data/model/valuation_ensemble.csv`
- `reports/tencent_valuation_2026-02-19.md`
- `reports/tencent_investment_memo_2026-02-19.md`
- `reports/tencent_v3_compact_log_2026-02-19.md`

## Notes

- Internal package/module names still include `tencent_valuation_v3` for compatibility.
- The operational command surface for current main is `tencent-valuation-v4`.
