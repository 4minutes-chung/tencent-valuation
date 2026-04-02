# Tencent Valuation Pipeline V4 (`main`)

This repository is the active codebase for the Tencent (`0700.HK`) multi-method valuation pipeline.

Current status (validated on **April 1, 2026**):
- Active branch: `main`
- Package version: `0.4.1`
- CLI command: `tencent-valuation-v4`
- Test status: `183 passed, 24 skipped` (`pytest -q`)

The internal Python package path remains `src/tencent_valuation_v3/` for compatibility, but `main` is the V4 operating line.

## Quick Start

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent_Model"
python -m pip install -e .
```

Run a deterministic synthetic pipeline:

```bash
tencent-valuation-v4 fetch --asof 2026-02-19
tencent-valuation-v4 build-overrides --asof 2026-02-19
tencent-valuation-v4 run-all --asof 2026-02-19 --source-mode synthetic --refresh
```

Generate the visual publication pack (story-first outputs):

```bash
python scripts/generate_v4_visuals.py --asof 2026-03-19
```

Alternative module invocation (equivalent behavior):

```bash
python -m tencent_valuation_v3 run-all --asof 2026-02-19 --source-mode synthetic --refresh
```

## Command Surface

```bash
tencent-valuation-v4 fetch --asof YYYY-MM-DD
tencent-valuation-v4 build-overrides --asof YYYY-MM-DD

# Core build
tencent-valuation-v4 factors --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh]
tencent-valuation-v4 wacc --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 dcf --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]

# Additional valuation methods
tencent-valuation-v4 apv --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 residual-income --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 comps --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 tvalue --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 reverse-dcf --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 monte-carlo --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 eva --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 real-options --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 stress --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]

# Aggregation and controls
tencent-valuation-v4 ensemble --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 qa --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 report --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh-factors]
tencent-valuation-v4 backtest --start YYYY-MM-DD --end YYYY-MM-DD --freq quarterly|monthly [--source-mode auto|live|synthetic]
tencent-valuation-v4 run-all --asof YYYY-MM-DD [--source-mode auto|live|synthetic] [--refresh]
```

## Recommended Runbooks

Production-like (`auto` with fallback):

```bash
tencent-valuation-v4 fetch --asof 2026-03-19
tencent-valuation-v4 build-overrides --asof 2026-03-19
tencent-valuation-v4 run-all --asof 2026-03-19 --source-mode auto --refresh
tencent-valuation-v4 qa --asof 2026-03-19 --source-mode auto
```

Strict live-input mode (fails if live fetch fails):

```bash
tencent-valuation-v4 run-all --asof 2026-03-19 --source-mode live --refresh
```

## Repo Layout

- `src/tencent_valuation_v3/`: all valuation, QA, reporting, and CLI implementation
- `config/`: WACC, scenarios, method weights, sources, peers, QA gates, backtest vintages
- `data/raw/`: as-of source snapshots and provenance manifests
- `data/processed/`: intermediate normalized inputs
- `data/model/`: model outputs from each valuation method and diagnostics
- `reports/`: active generated outputs (QA, valuation report, memo, compact log)
- `tests/`: unit and integration tests
- `examples/`: example run snapshots

## Key Artifacts from `run-all`

`run-all` writes a full output set, including:

- `data/processed/weekly_returns.csv`
- `data/processed/monthly_factors.csv`
- `data/processed/monthly_asset_returns.csv`
- `data/processed/market_inputs.csv`
- `data/model/wacc_components.csv`
- `data/model/capm_apt_compare.csv`
- `data/model/valuation_outputs.csv`
- `data/model/apv_outputs.csv`
- `data/model/residual_income_outputs.csv`
- `data/model/relative_valuation_outputs.csv`
- `data/model/tvalue_company_bridge.csv`
- `data/model/reverse_dcf_outputs.csv`
- `data/model/eva_outputs.csv`
- `data/model/monte_carlo_outputs.csv`
- `data/model/stress_scenario_outputs.csv`
- `data/model/valuation_method_outputs.csv`
- `data/model/valuation_ensemble.csv`
- `data/model/backtest_summary.csv`
- `reports/qa_<asof>.json`
- `reports/tencent_valuation_<asof>.md`
- `reports/tencent_investment_memo_<asof>.md`

## QA and CI Notes

- QA checks are produced in `reports/qa_<asof>.json`.
- Investor-grade requires zero failures plus required checks (`override_fundamentals_present`, `fundamentals_ttm_method`, `backtest_minimum_coverage`).
- In CI, `backtest_quality_flag` is intentionally treated as non-blocking; other QA fails are blocking.
- CI runs with Python 3.11 via `.github/workflows/ci.yml`.

Run tests locally:

```bash
pytest -q
```

## Documentation Index

- `docs/V4_MAIN_DOCUMENTATION.md`: architecture, data contracts, commands, output contracts, operations
- `docs/VERSION_HISTORY.md`: git-era summary from v1 to current v4 main
- `docs/REPO_EVALUATION_2026-04-01.md`: independent repository assessment snapshot
- `docs/INVESTMENT_REPORT_V4_2026-03-19.md`: investment report with assumptions, base case, methodology, and conclusion
- `docs/COMPLETE_REPO_REVIEW_2026-04-01.md`: full repo review findings, rerun validation, and reorg results
- `docs/PUBLICATION_STORYBOOK_V4_2026-03-19.md`: visual-heavy final narrative (assumptions, base case, methodology, conclusion)
- `docs/figures/2026-03-19/`: generated PNG chart pack (11 visuals + manifest)
- `docs/paper/tencent_v4_publication_note.tex`: LaTeX publication note with formal equations and figure references
- `docs/FINAL_AUDIT_AND_RELEASE_NOTE_2026-04-02.md`: end-state audit verdict across code, model, and publication readiness

## Versioning and History

The repository history preserves v1/v2/v3/v4 evolution in git commits. `main` is the only active line for ongoing work.

For historical inspection, use commit checkout (read-only workflows recommended):

```bash
git show f2cf350:README.md   # v1
git show 9fa837f:README.md   # v2
git show 0e0cc09:README.md   # v3
git show 1260378:README.md   # v4 import milestone
```
