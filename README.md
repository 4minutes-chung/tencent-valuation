# Tencent Valuation Pipeline (V4.1)

This repository runs a multi-method valuation workflow for Tencent (`0700.HK`) with reproducible outputs.

## What It Runs

- Data snapshot and input overrides (`fetch`, `build-overrides`)
- Factor and WACC engine
- DCF, APV, residual income, comps, T-value, reverse DCF, EVA, Monte Carlo, real options, stress tests
- Ensemble valuation, QA report, memo, and compact run log
- Figure pack for charts and presentation visuals

## Quick Start

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent_Model"
python -m pip install -e .
```

Run full pipeline on a target date:

```bash
tencent-valuation-v4 fetch --asof YYYY-MM-DD
tencent-valuation-v4 build-overrides --asof YYYY-MM-DD
tencent-valuation-v4 run-all --asof YYYY-MM-DD --source-mode live --refresh
python scripts/generate_v4_visuals.py --asof YYYY-MM-DD
```

Equivalent module entrypoint:

```bash
python -m tencent_valuation_v3 run-all --asof YYYY-MM-DD --source-mode live --refresh
```

## Latest Snapshot

Latest full rerun in this repo: **2026-04-02**

- Spot price used: `489.2` HKD
- WACC: `10.52%`
- DCF base fair value: `354.36` HKD/share
- DCF base margin of safety: `-27.56%`
- Data mode: live (`Tencent + Frankfurter`, with Stooq/Yahoo fallback)

Latest generated files:

- `reports/qa_2026-04-02.json`
- `reports/tencent_valuation_2026-04-02.md`
- `reports/tencent_investment_memo_2026-04-02.md`
- `reports/tencent_v4_compact_log_2026-04-02.md`
- `docs/figures/2026-04-02/`

## Repo Structure

- `src/tencent_valuation_v3/` implementation code and CLI
- `config/` model, scenario, QA, and source configuration
- `data/raw/<asof>/` raw snapshots and manifests
- `data/processed/` normalized model inputs
- `data/model/` model outputs and diagnostics
- `reports/` generated QA and narrative outputs
- `docs/` project documentation and visual packs
- `scripts/` helper scripts (including visual generation)
- `tests/` unit and integration tests

## Core Commands

```bash
tencent-valuation-v4 --help
tencent-valuation-v4 run-all --asof YYYY-MM-DD --source-mode auto --refresh
tencent-valuation-v4 qa --asof YYYY-MM-DD --source-mode auto
tencent-valuation-v4 backtest --start YYYY-MM-DD --end YYYY-MM-DD --freq quarterly
pytest -q
```

## Notes

- Package name and CLI are V4 (`tencent-valuation-v4`, version `0.4.1`).
- Internal module path remains `tencent_valuation_v3` for compatibility.
- Backtest warnings for early vintages can appear when strict live history is shorter than required windows.
