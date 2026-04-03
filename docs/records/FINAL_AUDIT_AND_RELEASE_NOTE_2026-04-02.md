# Final Audit and Release Note (2026-04-02)

## Scope

Full repo pass with focus on:
- code correctness and technical debt
- economic/model coherence
- publication readiness (story + visuals)

## Verification Results

- `tencent-valuation-v4 fetch --asof 2026-04-02`: pass
- `tencent-valuation-v4 build-overrides --asof 2026-04-02`: pass
- `tencent-valuation-v4 run-all --asof 2026-04-02 --source-mode live --refresh`: pass
- `python scripts/generate_v4_visuals.py --asof 2026-04-02`: pass
- `ruff check .`: pass
- `pytest -q`: pass (`183 passed, 24 skipped`)

## Headline Valuation Basis

Headline narrative is anchored to the live April 2, 2026 snapshot:
- Market: `HKD 489.20`
- Base DCF: `HKD 354.36` (`-27.6%`)
- Base Ensemble: `HKD 361.08` (`-26.2%`)

## Technical Debt Actions Completed

- Removed stale generated report/figure sets and kept the latest snapshot outputs.
- Standardized output naming to V4 compact log paths.
- Simplified README for operational clarity and current-run orientation.

## Math/Econ Review Verdict

### 1) Mathematical correctness: `adequate`
- Core equations (DCF/APV/RI/SOTP/EVA/ensemble) remain internally coherent.
- No arithmetic or schema-breaking regressions detected in code/tests.

### 2) Unit and boundary consistency: `adequate`
- Output contracts and scenario ordering checks pass.
- Reverse-DCF values are interpreted as market-implied assumptions, not implementation errors.

### 3) Economic assumption validity: `adequate for directional use`
- CAPM/APT stability warning remains active in diagnostics.
- Backtest calibration quality remains constrained by sample depth and listing-history coverage.

### 4) Practical decision reliability: `adequate for narrative decisions`
- Suitable for scenario framing and investment-note communication.
- Not yet investor-grade for high-conviction sizing under current QA status.

## Publication Readiness Verdict

### Story quality: `strong`
- Visual-first storybook is available at:
  - `docs/PUBLICATION_STORYBOOK_V4_2026-04-02.md`
- Full assumption and execution records are available at:
  - `docs/ASSUMPTION_REGISTER_2026-04-02.md`
  - `docs/RUN_LEDGER_2026-04-02.md`
- Assumptions, base case, methodology, and conclusion are explicit.

### Visual coverage: `strong`
- 11 generated charts:
  - `docs/figures/2026-04-02/*.png`
- Reproducible with:
  - `python scripts/generate_v4_visuals.py --asof 2026-04-02`

### Paper-form artifact: `adequate`
- LaTeX publication note:
  - `docs/paper/tencent_v4_publication_note.tex`

## Residual Risks

1. CAPM/APT instability warning persists.
2. Backtest sample depth and calibration quality remain limited.
3. Proxy peer fundamentals still affect comps layer when full fields are absent.

## Final Recommendation

Project is in a publishable working-note state for the current live snapshot.

Use April 2, 2026 values as the active headline basis and update date-stamped outputs together on each new rerun.
