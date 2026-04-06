# Tencent Holdings (0700.HK) — Investment Report

**As of:** 2026-04-03 | **Spot:** 489.2 HKD | **Model:** V4

---

## 1. Executive Summary

Tencent is one of the dominant technology platforms in China — gaming, social (WeChat), fintech (WeChat Pay), cloud, and advertising. Despite strong fundamentals, the model finds the stock **overvalued at current prices** across all DCF-based methods under base assumptions.

| | |
|---|---|
| Ensemble fair value (base) | **407 HKD** |
| vs. spot | **−17%** |
| Ensemble expected value (probability-weighted) | **331 HKD** |
| Margin of safety at spot | **None** |

**Conclusion:** No margin-of-safety entry at 489 HKD. A constructive case requires either a meaningful price decline or clear evidence of fundamental outperformance against the base scenario.

---

## 2. Cost of Capital (WACC)

### 2.1 Inputs

| Parameter | Value | Method |
|---|---|---|
| Risk-free rate (rf) | 4.13% | UST 10Y current yield (FRED) |
| Equity risk premium (ERP) | 4.63% | 60-month rolling excess return |
| Raw levered beta | 1.499 | 104-week OLS vs. HSI |
| Vasicek-adjusted beta | 1.359 | Shrinkage toward market beta = 1.0 |
| Country risk premium (CRP) | 1.25% | China regulatory exposure add-on |
| Cost of equity (CAPM) | 11.67% | rf + β × ERP + CRP |
| Cost of debt (Rd) | 5.63% | Synthetic spread: rf + 150bps |
| D/E ratio | 0.198 | From capital structure |
| Tax rate | 20.0% | Effective rate from filings |
| **WACC** | **10.48%** | CAPM-based, after-tax |

### 2.2 APT Diagnostic

A Fama-French 3-factor APT model was run alongside CAPM as a diagnostic check. Result: **APT is window-unstable** — the implied cost of equity swings 481bps across different estimation windows (24m vs. 60m). CAPM with Vasicek adjustment is the official cost of equity. APT is shown for transparency only.

| | CAPM | APT (guardrailed) |
|---|---|---|
| Cost of equity | 11.67% | 12.76% |
| Gap | — | +109bps |

The gap is within the 150bps alert threshold. APT is flagged unstable but does not override CAPM.

### 2.3 Vasicek Beta Adjustment

Raw OLS beta of 1.499 is noisy given a 2-year estimation window. Vasicek shrinkage pulls it toward 1.0:

> β_adjusted = w × β_raw + (1−w) × 1.0

Adjusted beta: **1.359**. This is the standard adjustment used by practitioners to reduce estimation error in shorter windows.

---

## 3. DCF Model

### 3.1 Framework

- **Projection horizon:** 7 years (mid-year discounting)
- **Free cash flow:** FCFF = NOPAT − net capex − ΔNWC − SBC
- **Terminal value:** Gordon Growth Model — `TV = FCFF₇ × (1 + g) / (WACC − g)`
- **Scenarios:** base / bad / extreme — each with independent revenue growth, margin, capex, and terminal g

### 3.2 Scenario Assumptions

| | Base | Bad | Extreme |
|---|---|---|---|
| Revenue growth (Yr 1→7) | 8% → 5.5% | 3% → 3.5% | −3% → 3% |
| EBIT margin (Yr 1→7) | 36% → 37.4% | 33% → 32.2% | 30% → 28.5% |
| Capex % revenue | 9% → 8.3% | 9.5% → 9.0% | 10% → 9.5% |
| Terminal growth (g) | **3.5%** | 1.0% | 0.0% |
| Annual buyback | HKD 40bn | HKD 20bn | — |

**Terminal g rationale (base = 3.5%):** Below China nominal GDP (~5–6%), reflecting regulatory uncertainty and mean reversion in long-run growth. Above US long-run nominal GDP (2–2.5%), justified by Tencent's embedded position in the Chinese economy.

### 3.3 DCF Results

| Scenario | Fair Value (HKD) | vs. Spot |
|---|---|---|
| Base | 391.64 | −20% |
| Bad | 207.01 | −58% |
| Extreme | 148.26 | −70% |

---

## 4. Supporting Valuation Methods

Eight additional methods were run alongside DCF. All base-scenario results:

| Method | Fair Value (HKD) | vs. Spot | Weight in Ensemble |
|---|---|---|---|
| DCF (FCFF) | 391.64 | −20% | 26.4% |
| APV | 373.26 | −24% | 15.9% |
| EVA | 379.26 | −22% | 10.6% |
| Monte Carlo (10k paths) | 399.33 | −18% | 10.6% |
| Real Options | 402.64 | −18% | 5.3% |
| Residual Income | 268.35 | −45% | 9.0% |
| SOTP | 445.89 | −9% | 14.3% |
| Relative (peer comps) | 644.89 | +32% | 8.1% |
| **Ensemble (QA-weighted)** | **407.14** | **−17%** | — |

**Notes on outliers:**

- **Residual Income (268 HKD):** Book value-anchored. Tencent's equity book value is high relative to earnings power, creating conservative implied returns on equity. Lowest estimate in the stack.
- **Relative comps (645 HKD):** Peer multiples (P/E, EV/EBIT) across 5 HK-listed tech peers are rich — the whole sector is priced for growth. This method reflects market sentiment, not intrinsic value. Down-weighted in ensemble to 8%.
- **SOTP (446 HKD):** Segment-level valuation (Gaming, FinTech, Cloud, Ads) using peer revenue multiples plus strategic investments at book. Closest to intrinsic among the higher estimates.

### 4.1 Monte Carlo

10,000 simulated paths with stochastic revenue growth, margin, and WACC. Correlation between growth and margin: −0.30 (higher growth tends to compress margins). Output distribution:

- P10: ~310 HKD
- P50: ~399 HKD
- P90: ~510 HKD
- Mean: 399 HKD

### 4.2 Real Options

Binomial tree on Tencent's growth optionality (AI, international gaming, fintech expansion). Option value added on top of base DCF operating value. Adds ~11 HKD/share to the DCF base.

---

## 5. Ensemble Construction

The ensemble is a QA-gated weighted average across all 8 methods (excluding Real Options as an overlay). Base weights are configured in `config/method_weights.yaml` and then adjusted:

- **APT instability penalty:** −10% to APT-dependent methods
- **Backtest quality penalty:** −15% applied where backtest coverage is thin

Realized normalized weights are shown in the table above. The ensemble is only accepted if all 27 QA checks pass and `investor_grade = True`.

**Scenario probabilities (for expected value):**

| Scenario | Probability | Ensemble FV |
|---|---|---|
| Base | 50% | 407 HKD |
| Bad | 35% | 271 HKD |
| Extreme | 15% | 217 HKD |
| **Expected value** | — | **331 HKD** |

---

## 6. Sensitivity Analysis

DCF fair value (HKD) across WACC and terminal growth shifts from base:

| WACC shift \ g shift | −100bps (g=2.5%) | Base (g=3.5%) | +100bps (g=4.5%) |
|---|---:|---:|---:|
| −100bps (WACC=9.48%) | 411 | 461 | 532 |
| −50bps (WACC=9.98%) | 382 | 424 | 482 |
| **Base (WACC=10.48%)** | **356** | **392** | **439** |
| +50bps (WACC=10.98%) | 333 | 364 | 404 |
| +100bps (WACC=11.48%) | 313 | 339 | 373 |

**Key read:** The model only produces a fair value above spot (489 HKD) when WACC drops 100bps AND terminal g rises 100bps simultaneously — a bull case requiring both lower discount rates and higher long-run growth than base.

---

## 7. Stress Scenarios

Three named stress scenarios applied on top of the base DCF, each with an independent probability:

| Scenario | Description | Probability | Fair Value (HKD) |
|---|---|---|---|
| Gaming crackdown | Severe regulation tightening on gaming revenue | 5% | 160 |
| Fintech regulation | Major licensing / capital requirements on WeChat Pay | 8% | 241 |
| US-China escalation | Tech decoupling, +100bps WACC adder | 10% | 215 |

All stress scenarios produce fair values well below spot. Combined stress probability: 23%.

---

## 8. Market-Implied Check (Reverse DCF)

At spot price 489.2 HKD, solving backwards for the terminal growth rate that justifies current price (holding all other assumptions constant):

| Implied assumption | Value |
|---|---|
| Implied terminal g | **5.0%** |
| Implied margin shift | +585bps above base |
| Implied growth shift | +323bps above base |

The market is pricing in terminal growth above China nominal GDP and materially better margins than the base case. This is a high bar — it requires Tencent to sustain above-GDP growth in perpetuity with expanding margins.

---

## 9. Data and Limitations

| Input | Source |
|---|---|
| Tencent financials (TTM) | Tencent IR quarterly filings + stooq FX |
| UST yield curve | FRED |
| Factor data (CAPM/APT) | Ken French APAC data library |
| Peer capital structure | StockAnalysis HKEX FY2025 |
| Peer P&L multiples | yfinance TTM statements |

**Known limitations:**
1. APT is window-unstable — CAPM is official, APT is diagnostic
2. Monte Carlo uses a single growth-margin correlation (−0.30) — simplification
3. Terminal ROIC implied by base scenario is a monitoring metric, not a hard QA gate
4. Backtest coverage is thin for pre-2022 windows due to peer listing dates

---

## 10. QA Summary

27 automated checks across WACC inputs, DCF mechanics, ensemble weights, scenario ordering, and output schema.

**Last run result:** `warnings=0 | failures=0 | investor_grade=True`
