# Complete Repository Review (V4 Main)

Date: April 1, 2026  
Branch: `main`  
Scope: full repository (`src`, `tests`, `config`, `data`, `reports`, CI, docs) plus fresh rerun validation.

## 1) What Was Checked

- Repository structure and git state.
- Source + test baseline integrity.
- CI workflow behavior (`.github/workflows/ci.yml`).
- Full test suite run: `pytest -q`.
- Full pipeline rerun for `asof=2026-04-01`:
  - `fetch`
  - `build-overrides`
  - `run-all --source-mode auto --refresh`
  - `qa`
  - `report`
  - additional `backtest --freq monthly`
- Folder organization and legacy artifact placement.

## 2) Validation Results

- Tests: **183 passed, 24 skipped**.
- Full rerun for `2026-04-01`: completed end-to-end and produced expected artifacts.
- QA summary for `2026-04-01`:
  - total checks: 27
  - warnings: 6
  - failures: 1
  - investor-grade: false

## 3) Key Findings (Prioritized)

### [P1] Live ingestion path is fragile and frequently falls back to synthetic

Observed behavior during rerun:
- repeated warnings: `Live factor build failed (No columns to parse from file); using synthetic fallback.`
- fallback occurred across factor and backtest routines.

Impact:
- production-like `auto` mode can silently degrade to synthetic estimates, materially changing valuation quality and making live-vs-synthetic provenance critical.

Recommendation:
- harden remote parser guards for Stooq/Treasury responses and fail fast with explicit source-specific diagnostics.
- optionally add a strict run profile (`auto-strict`) that errors if synthetic fallback occurs.

### [P1] Peer fundamentals for comps are incomplete by default

Observed behavior during rerun:
- warnings that `peer_fundamentals.csv` is missing `net_income_hkd_bn`, `book_value_hkd_bn`, `ebit_hkd_bn`, `fcf_hkd_bn`.
- system falls back to proxy multiples.

Impact:
- relative valuation and ensemble quality degrade; risk of understating data quality issues.

Recommendation:
- upgrade override generation/input contract to include full comps columns.
- treat missing full comps columns as an explicit QA warn/fail based on run profile.

### [P2] Backtest quality gating failed for the 2026-04-01 run

Observed in `reports/qa_2026-04-01.json`:
- `backtest_quality_flag`: fail
- `backtest_minimum_coverage`: warn/fail context depending gate profile
- investor-grade set to false.

Impact:
- current run does not meet investor-grade criteria.

Recommendation:
- do not use this snapshot as investor-grade investment output without improving backtest coverage/calibration behavior.
- review backtest interval coverage and calibration pipeline in current environment.

### [P2] Generated artifact strategy is mixed (tracked historical + ignored new generated files)

Observed:
- historical generated artifacts remain tracked.
- `.gitignore` excludes broad generated patterns (`data/raw/**`, `data/model/*.csv`, `reports/tencent_valuation_*.md`, etc.).

Impact:
- behavior is workable but easy to misinterpret for contributors (what should be committed vs regenerated).

Recommendation:
- publish a single artifact policy (tracked snapshots vs fully generated) and enforce it consistently.

### [P3] Internal naming still carries `v3` module paths in V4 line

Observed:
- package path remains `src/tencent_valuation_v3/`.

Impact:
- low immediate risk; moderate onboarding/maintenance confusion.

Recommendation:
- keep as-is short term, but define a future migration plan if a namespace change is desired.

## 4) Folder Reorganization Outcome

Reports cleanup was applied so `main` keeps only active V4 outputs.

- Active root stays focused on:
  - `qa_<asof>.json`
  - `tencent_valuation_<asof>.md`
  - `tencent_investment_memo_<asof>.md`
  - `tencent_v3_compact_log_<asof>.md`
- Legacy/manual report artifacts were removed from current `main`.
- Historical copies remain available in git commit history.

## 5) Overall Status

- Codebase is operational and test-stable.
- Rerun completed successfully with full artifact generation.
- Main execution risk is data-quality/source fragility in live mode and incomplete peer fundamentals for comps.
- Current `2026-04-01` output is useful for diagnostics but is **not investor-grade** per QA.
