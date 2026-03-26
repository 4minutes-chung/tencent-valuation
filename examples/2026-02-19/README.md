# Tencent Valuation V3 Example (2026-02-19)

This example was generated from:

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3"
PYTHONPATH=src python -m tencent_valuation_v3 fetch --asof 2026-02-19 --project-root .
PYTHONPATH=src python -m tencent_valuation_v3 build-overrides --asof 2026-02-19 --project-root .
PYTHONPATH=src python -m tencent_valuation_v3 run-all --asof 2026-02-19 --project-root . --source-mode live --refresh
```

## Key Outputs

- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/wacc_components.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/valuation_outputs.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/apv_outputs.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/residual_income_outputs.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/relative_valuation_outputs.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/tvalue_company_bridge.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/tvalue_stat_diagnostics.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/reverse_dcf_outputs.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/data/model/valuation_ensemble.csv`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/reports/tencent_valuation_2026-02-19.md`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/reports/tencent_investment_memo_2026-02-19.md`
- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3/reports/tencent_v3_compact_log_2026-02-19.md`
