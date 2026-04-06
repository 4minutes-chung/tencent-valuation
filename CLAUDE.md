# CLAUDE.md — Tencent Valuation V4

## Purpose

Tier 2 side-portfolio project. Owner is an economist (not IB/finance) targeting
market risk or financial economics roles. Goal: demonstrate equity valuation
literacy — CAPM, DCF, ensemble — so interviewers know "this person understands
how stocks are priced." Not for trading. Not for production. Not for getting a
quant job.

Portfolio deliverable: a clean GitHub repo where someone can glance at the
README, see charts and a results table, and immediately understand what was built
and why.

---

## What This Is

9-method equity valuation pipeline for Tencent Holdings (0700.HK):

- WACC engine: CAPM + APT (Fama-French 3-factor), Vasicek beta adjustment
- DCF: 7-year FCFF projection, 3 scenarios (base / bad / extreme)
- Supporting methods: APV, Residual Income, Comps, SOTP, EVA, Monte Carlo,
  Real Options, Stress
- Ensemble: QA-gated weighted average across all methods
- 11 charts auto-generated per run
- 27 QA checks; investor-grade flag

Active run: `2026-04-03`. Spot price `489.2` HKD. Ensemble base fair value
`385.89` HKD. Model says: overvalued, no margin of safety.

---

## Data Reality (Be Honest)

| Source | Status |
|--------|--------|
| `tencent_financials.csv` | Real — TTM from Tencent quarterly filings, FX from stooq |
| `peer_fundamentals.csv` | **Synthetic/template** — `source_doc=peer_fundamentals_template` |
| Factor data (CAPM/APT) | Real in `live` mode (FRED + public market data); synthetic in `stub` |
| UST yield curve | Real (FRED) |

Comps and relative valuation outputs are approximate because peer fundamentals
are template anchors. Do not claim full live data for the peer side. Document
this as a known limitation, do not hide it.

If the user wants to fix this: download real peer fundamentals from HKEX filings
or Bloomberg and replace `data/raw/<asof>/peer_fundamentals.csv`. The required
columns are: `net_income_hkd_bn`, `book_value_hkd_bn`, `ebit_hkd_bn`,
`fcf_hkd_bn`.

---

## What Claude Should Help With

1. README presentation — embed charts, write clear descriptions, fix absolute paths
2. .gitignore hygiene — what to track, what to exclude
3. Specific bugs when called out explicitly
4. Documentation updates when the run date changes
5. Understanding the pipeline flow for explanation purposes

---

## What Claude Should NOT Do

- Do not rewrite working valuation modules (dcf.py, wacc.py, factors.py, etc.)
- Do not add new valuation methods or complexity
- Do not "improve" tests or add type hints to untouched code
- Do not suggest refactors unless the user explicitly asks
- Do not over-engineer solutions to known limitations — document them instead

---

## Known Limitations (Document, Don't Fix)

1. **Peer comps are proxy anchors** — real peer fundamentals not downloaded
2. **APT is window-unstable** — CAPM is the official cost of equity; APT is
   diagnostic only
3. **Terminal ROIC check is a warning, not a failure** — known gap in QA hardness
4. **Monte Carlo uses a single correlation coefficient** — simplification
5. **Silent fallback to synthetic** in `auto` source mode — use `live` or `stub`
   explicitly

---

## How to Run

```bash
python -m pip install -e .
scripts/run_model.sh 2026-04-03 live
python scripts/generate_v4_visuals.py --asof 2026-04-03
```

Tests:
```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

QA check:
```bash
python3 -c "
import json
s = json.load(open('reports/qa_2026-04-03.json'))['summary']
print(s)
"
```

Release gate: `warnings=0`, `failures=0`, `investor_grade=true`.

---

## Repo Hygiene Rules

- No `Co-Authored-By` lines in commits
- Stage files intentionally; never blind `git add -A` before checking `git diff`
- QA must be clean before push
- Active docs (README, INVESTMENT_REPORT) must match the run date
- `docs/records/` is internal log noise — do not surface it in the portfolio

---

## File Map (What Matters for Portfolio)

```
README.md                         ← portfolio front door (keep clean)
docs/INVESTMENT_REPORT.md         ← decision narrative (keep, 1 page)
docs/MODEL_ASSUMPTIONS.md         ← methodological depth (keep)
docs/figures/<latest>/            ← 11 charts (the visual proof)
src/tencent_valuation_v4/         ← all code (breadth = the point)
config/                           ← YAML config (shows separation of concerns)
tests/                            ← test suite (shows rigor)
```

Not for portfolio display (internal):
```
docs/records/                     ← working logs
reports/tencent_v4_compact_log_*  ← internal run logs
data/raw/                         ← raw data (not committed)
data/model/                       ← generated outputs (not committed)
```
