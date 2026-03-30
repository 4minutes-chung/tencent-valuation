# Tencent Model V4 (Main)

This repository is the active Tencent valuation codebase.
`main` is the only working line and represents V4.

## Layout

- `config/`: model and QA configuration
- `src/tencent_valuation_v3/`: implementation package (internal module name kept for code compatibility)
- `data/`: processed/model outputs
- `reports/`: QA and valuation reports
- `tests/`: test suite

## Install

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent_Model"
python -m pip install -e .
```

## CLI

Use the V4 command:

```bash
tencent-valuation-v4 fetch --asof YYYY-MM-DD
tencent-valuation-v4 build-overrides --asof YYYY-MM-DD
tencent-valuation-v4 run-all --asof YYYY-MM-DD --source-mode auto --refresh
tencent-valuation-v4 qa --asof YYYY-MM-DD --source-mode auto
```

## Typical Run

```bash
tencent-valuation-v4 run-all --asof 2026-02-19 --source-mode synthetic --refresh
```

## Notes

- Old V1/V2/V3 branch history is not used for daily work.
- Keep new work on `main` and sync local with GitHub before each session.
