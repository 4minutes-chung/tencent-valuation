# Tencent Valuation Pipeline (V4.1)

Multi-method valuation workflow for Tencent (`0700.HK`) with reproducible outputs.

## Quick Start

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent_Model"
python -m pip install -e .
```

Run the full pipeline:

```bash
tencent-valuation-v4 fetch --asof YYYY-MM-DD
tencent-valuation-v4 build-overrides --asof YYYY-MM-DD
tencent-valuation-v4 run-all --asof YYYY-MM-DD --source-mode live --refresh
python scripts/generate_v4_visuals.py --asof YYYY-MM-DD
```

Single command (recommended):

```bash
scripts/run_model.sh YYYY-MM-DD synthetic
```

## Current Snapshot (Active)

- As-of: `2026-04-03`
- Spot price: `489.2` HKD
- WACC: `10.52%`
- DCF base: `354.36` HKD/share
- Ensemble base: `385.89` HKD/share
- QA summary: `27 checks`, `0 warnings`, `0 failures`, investor-grade `YES`

## Documentation (Primary)

1. `README.md` (quick start)
2. `docs/INVESTMENT_REPORT.md` (short investment report)
3. `docs/MODEL_ASSUMPTIONS.md` (full assumptions + QA gates + implications)
4. `docs/DOCUMENTATION.md` (project operation and structure)

## Documentation (Records)

Historical notes, audits, previous snapshots, and working logs:
- `docs/records/`

## Repo Structure

- `src/tencent_valuation_v4/` canonical code + CLI
- `config/` model configuration
- `data/raw/<asof>/` raw snapshots + manifests
- `data/processed/` processed inputs
- `data/model/` model outputs
- `reports/` run reports
- `docs/figures/<asof>/` chart pack
- `tests/` tests

## Architecture Sanity Notes

- `pyproject.toml` is required: it defines package metadata, dependencies, and CLI entrypoint (`tencent-valuation-v4`).
- `src/` is the standard Python source layout used by `setuptools`.
- Active code is V4 only: `src/tencent_valuation_v4/`.
- There is no active `src/tencent_valuation_v3/` package in this repository.
