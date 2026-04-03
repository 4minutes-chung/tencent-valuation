# DOCUMENTATION

Last updated: 2026-04-03

This file is the single operational guide for the V4 project.

## 1) What This Project Does

The project values Tencent (`0700.HK`) using a multi-method stack:
- DCF
- APV
- Residual Income
- Relative valuation (comps)
- SOTP / T-value
- EVA
- Monte Carlo
- Real options
- Stress scenarios
- Ensemble aggregation

Primary CLI:
- `tencent-valuation-v4`

## 2) Standard Workflow

```bash
tencent-valuation-v4 fetch --asof YYYY-MM-DD
tencent-valuation-v4 build-overrides --asof YYYY-MM-DD
tencent-valuation-v4 run-all --asof YYYY-MM-DD --source-mode live --refresh
python scripts/generate_v4_visuals.py --asof YYYY-MM-DD
```

## 3) Current Snapshot (Active)

- As-of date: `2026-04-03`
- Spot price: `489.2` HKD
- WACC: `10.52%`
- DCF base value: `354.36` HKD/share
- Ensemble base value: `385.89` HKD/share
- QA summary: `27 checks`, `0 warnings`, `0 failures`, investor-grade `YES`

## 4) Required Inputs

Required config files:
- `config/wacc.yaml`
- `config/scenarios.yaml`
- `config/method_weights.yaml`
- `config/qa_gates.yaml`
- `config/peers.yaml`
- `config/sources.yaml`

Expected override inputs under `data/raw/<asof>/`:
- `tencent_financials.csv`
- `segment_revenue.csv`
- `peer_fundamentals.csv`

Structure notes:
- `pyproject.toml` exists to define install/build/dependency metadata and the CLI script.
- `src/` is the package source root.
- Canonical package is `src/tencent_valuation_v4/` (V4-only execution path).

## 5) Main Outputs

- Reports: `reports/`
- Model tables: `data/model/`
- Processed inputs: `data/processed/`
- Visuals: `docs/figures/<asof>/`

## 6) The 3 Supporting Docs

- `docs/INVESTMENT_REPORT.md` (short decision-oriented report)
- `docs/MODEL_ASSUMPTIONS.md` (full assumptions + QA gates + implications)
- `README.md` (repo quick start)

## 7) Historical / Working Records

All extra review notes, audit notes, previous snapshots, and work logs are moved to:
- `docs/records/`
