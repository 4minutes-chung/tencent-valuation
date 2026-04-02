# Version History (Git Lineage)

Last updated: April 1, 2026

This repository has a single active branch (`main`) with preserved commit history for v1 through v4 milestones.

## 1) Timeline Summary

| Era | Commit | Date | Headline |
|---|---|---|---|
| V1 | `f2cf350` | 2026-02-17 | Baseline Tencent valuation framework |
| V2 | `9fa837f` | 2026-02-19 | Added data snapshots and valuation reports |
| V3 | `0e0cc09` | 2026-03-19 | Added expanded v3 package/output set |
| V4 import milestone | `1260378` | 2026-03-26 | Imported Windows V4 files into GitHub repo |
| V4 cleanup (current main baseline) | `426f8fc` | 2026-03-29 | Cleaned repo to v4-only layout |

## 2) What Changed by Era

### V1 (`f2cf350`)
- Original package path: `src/tencent_valuation/`
- Core capabilities: fetch, factors, WACC, DCF, QA, report, backtest.
- Minimal test set (`tests/test_factors.py`, `tests/test_wacc_math.py`, `tests/test_integration_pipeline.py`).

### V2 (`9fa837f`)
- Added committed output snapshots in `data/` and `reports/`.
- Added deep-research report markdown artifacts.
- Expanded operational reproducibility through stored artifacts.

### V3 (`0e0cc09`)
- Added broader method stack and output contracts (APV, residual income, comps, T-value, reverse DCF, ensemble, regime backtest outputs).
- Introduced large `v3/` subtree with a standalone structure in that commit era.

### V4 import (`1260378`)
- Added/updated modernized `src/tencent_valuation_v3/` implementation.
- Added `config/sources.yaml`, `config/method_weights.yaml`, and `config/backtest_vintages/*`.
- Expanded tests for new method set and QA behaviors.
- Added V4-era formal reporting artifacts (kept in git history).

### V4 cleanup (`426f8fc`, current `main`)
- Removed obsolete legacy package path `src/tencent_valuation/`.
- Removed duplicated historical `v3/` subtree from repo root.
- Kept active implementation in `src/tencent_valuation_v3/` but switched package identity to V4 (`tencent-valuation-v4`, version `0.4.0`).
- Updated docs/config references for v4-only operation.

## 3) Current Main Characteristics

- Branch: `main`
- Total commits in current history: `11`
- Active package entrypoint: `tencent_valuation_v3.cli:main`
- CLI executable: `tencent-valuation-v4`
- CI branch target: `main` (push and PR)

## 4) How to Inspect Historical Versions

Read historical README files without checkout:

```bash
git show f2cf350:README.md
git show 9fa837f:README.md
git show 0e0cc09:README.md
git show 1260378:README.md
git show 426f8fc:README.md
```

List top-level tree at a specific version:

```bash
git ls-tree --name-only <commit>
```

Show file-level changes introduced by a milestone commit:

```bash
git diff-tree --no-commit-id --name-status -r <commit>
```

## 5) Practical Guidance

1. Treat `main` as the only operational line for new development.
2. Use historical commits for forensic comparisons and reproducibility, not day-to-day execution.
3. Keep documentation aligned with the V4 CLI name even when internal module names retain legacy `v3` identifiers.
