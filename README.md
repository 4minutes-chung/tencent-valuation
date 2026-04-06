# Tencent Valuation Pipeline (V4)

9-method equity valuation of Tencent Holdings (`0700.HK`). Built to demonstrate CAPM, DCF, and ensemble valuation mechanics — reproducible from raw data to charts in a single command.

---

## Result (as of 2026-04-03, spot 489.2 HKD)

| Method | Fair Value (HKD) | vs. Spot |
|---|---|---|
| DCF (FCFF, 7-year) | 355.83 | −27% |
| APV | 346.39 | −29% |
| EVA | 367.71 | −25% |
| Monte Carlo (10k paths) | 362.15 | −26% |
| Real Options | 366.83 | −25% |
| Residual Income | 260.50 | −47% |
| SOTP | 445.89 | −9% |
| Relative (peer comps) | 644.89 | +32% |
| **Ensemble (QA-weighted)** | **386.18** | **−21%** |

**Model conclusion:** DCF-based methods cluster at 350–370 HKD. Ensemble fair value of 386 HKD is ~21% below spot — no margin of safety under base assumptions.

WACC: `10.48%` | Beta (Vasicek): `1.36` | rf (UST 10Y): `4.13%` | ERP: `4.63%`

---

## Charts

**DCF scenarios vs. market price**

![DCF vs Market](docs/figures/2026-04-03/01_dcf_vs_market.png)

**All 9 methods — base scenario cross-section**

![Method Cross-Section](docs/figures/2026-04-03/03_method_cross_section.png)

**DCF sensitivity: WACC vs. terminal growth rate**

![Sensitivity WACC-g](docs/figures/2026-04-03/07_sensitivity_wacc_g.png)

---

## Methods

| Layer | What it does |
|---|---|
| **WACC engine** | CAPM (official) + APT/Fama-French 3-factor (diagnostic), Vasicek beta adjustment, CRP add-on |
| **DCF** | 7-year FCFF projection, 3 scenarios (base / bad / extreme), WACC-discounted |
| **APV** | DCF + PV of interest tax shields, Modigliani-Miller framework |
| **Residual Income** | Excess return over cost of equity, from book value |
| **EVA** | NOPAT vs. invested capital charge |
| **SOTP** | Segment revenue × peer multiples (Gaming, FinTech, Cloud, Ads) |
| **Relative** | P/E, EV/EBIT, P/FCF comps across 5 HK-listed peers |
| **Monte Carlo** | 10,000 paths, stochastic revenue growth + margin |
| **Real Options** | Binomial tree on growth optionality |
| **Ensemble** | QA-gated weighted average; 27 checks, investor-grade gate |

---

## Quick Start

```bash
python -m pip install -e .
scripts/run_model.sh 2026-04-03 live
python scripts/generate_v4_visuals.py --asof 2026-04-03
```

QA check:
```bash
python3 -c "import json; print(json.load(open('reports/qa_2026-04-03.json'))['summary'])"
```

---

## Repo Structure

```
src/tencent_valuation_v4/   ← pipeline code + CLI
config/                     ← YAML config (WACC, scenarios, QA gates, method weights)
data/raw/<asof>/            ← raw snapshots (not committed)
docs/figures/<asof>/        ← 11 charts per run
tests/                      ← test suite
```

Full docs: [`docs/INVESTMENT_REPORT.md`](docs/INVESTMENT_REPORT.md) | [`docs/MODEL_ASSUMPTIONS.md`](docs/MODEL_ASSUMPTIONS.md)

---

## Data Sources

| Input | Source |
|---|---|
| Tencent financials (TTM) | Tencent IR quarterly filings + stooq FX |
| UST yield curve | FRED |
| Market / factor data | Public market data (live mode) |
| Peer capital structure | HKEX annual reports (FY2025, StockAnalysis) |
| Peer P&L multiples | yfinance TTM statements |

**Known limitation:** Relative valuation outputs are approximate — peer comps are anchored to real fundamentals but not Bloomberg-grade.

---

## QA

27 checks across WACC inputs, DCF mechanics, ensemble weights, and output sanity.
Last run: `0 warnings / 0 failures / investor_grade = True`
