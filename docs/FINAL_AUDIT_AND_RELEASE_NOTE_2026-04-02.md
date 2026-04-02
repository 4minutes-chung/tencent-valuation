# Final Audit and Release Note (2026-04-02)

## Scope

Full repo pass on `main` with focus on:
- code correctness and technical debt
- economic/model coherence
- publication readiness (story + visuals)

## Verification Results

- `tencent-valuation-v4 run-all --asof 2026-03-19 --source-mode synthetic --refresh`: pass
- `tencent-valuation-v4 qa --asof 2026-03-19 --source-mode synthetic`: pass (warnings/fails inside QA report)
- `ruff check .`: pass
- `pytest -q`: pass (`183 passed, 24 skipped`)

## Headline Valuation Basis

Headline narrative is anchored to the calibrated March 19, 2026 snapshot:
- Market: `HKD 550.50`
- Base DCF: `HKD 455.56` (`-17.2%`)
- Base Ensemble: `HKD 428.25` (`-22.2%`)

The harsher synthetic outputs (including near `-67%`) are retained as stress diagnostics and engineering reproducibility checks, not as headline investment conclusion.

## Technical Debt Actions Completed

- Removed unused imports/variables across valuation modules and tests.
- Kept production behavior unchanged; cleanup focused on dead code and lint issues.
- Strengthened residual-income test by validating EBO identity for explicit-book and proxy-book variants.

## Math/Econ Review Verdict

### 1) Mathematical correctness: `adequate`
- Core equations (DCF/APV/RI/SOTP/EVA/ensemble) are internally coherent.
- No arithmetic or schema-breaking regressions detected in code/tests.

### 2) Unit and boundary consistency: `adequate`
- Output contracts and scenario ordering checks pass.
- Reverse-DCF extremes are treated as market-implied stress, not implementation error.

### 3) Economic assumption validity: `weak-to-adequate`
- Synthetic run has elevated ERP and CAPM/APT divergence.
- Backtest quality/calibration remains limited by sample depth.

### 4) Practical decision reliability: `adequate for directional narrative`
- Suitable for scenario framing and investment-note communication.
- Not yet investor-grade for high-conviction sizing under current QA status.

## Publication Readiness Verdict

### Story quality: `strong`
- Visual-first storybook added:
  - `docs/PUBLICATION_STORYBOOK_V4_2026-03-19.md`
- Explicit assumptions, base case, methodology, and conclusion are documented.

### Visual coverage: `strong`
- 11 generated charts:
  - `docs/figures/2026-03-19/*.png`
- Reproducible with:
  - `python scripts/generate_v4_visuals.py --asof 2026-03-19`

### Paper-form artifact: `adequate`
- LaTeX publication note added:
  - `docs/paper/tencent_v4_publication_note.tex`

## Residual Risks

1. CAPM/APT instability in synthetic diagnostics.
2. Backtest sample depth and calibration quality.
3. Proxy peer fundamentals in comps layer.

## Final Recommendation

Project is now in a **closed, publishable narrative state** for an investment-note / working-paper release.

Use calibrated March 19, 2026 values for the headline decision and keep synthetic severe outputs in sensitivity/stress appendices only.
