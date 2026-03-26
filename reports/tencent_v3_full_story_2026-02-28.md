# Tencent Valuation V3 — Full Build Story (As-of 2026-02-19, documented 2026-02-28)

## 0) Purpose

This file records the full end-to-end V3 work in one place:

- what was built,
- what data was collected,
- assumptions and formulas,
- build-up from raw data to model outputs,
- validation and QA,
- final valuation answer.

The goal stayed fixed:

1. equity valuation of Tencent under `base / bad / extreme`,
2. ship-ready project artifact,
3. repeatable pipeline for future reruns.

---

## 1) What Was Done (7 Workstreams)

### Workstream 1: Isolated V3 Platform (no V2 contamination)

Built a standalone V3 under:

- `/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3`

with its own:

- package: `tencent_valuation_v3`
- CLI: `tencent-valuation-v3`
- config: `v3/config/*`
- data outputs: `v3/data/*`
- reports: `v3/reports/*`
- tests: `v3/tests/*`

V2 code at `/Users/stevenchung/Desktop/P12B_File/Tencent Model/src/tencent_valuation` was not modified.

### Workstream 2: Data Collection + Provenance Layer

Added V3 fetch/provenance flow that writes:

- `v3/data/raw/<asof>/source_manifest.json`

Manifest includes for each source:

- URL,
- file path,
- bytes,
- SHA256 hash,
- parser version,
- status.

Collected public/free sources for run date `2026-02-19`:

1. Tencent IR financial news page
2. HKEX title search
3. HKEX CCASS page
4. SFC short-position page
5. Ken French APAC ex-Japan 3-factor zip
6. US Treasury daily yield CSV

All 6 fetched with `status=ok`.

### Workstream 3: Filing Overrides + Point-in-Time Inputs

Implemented and used strict override pack in:

- `v3/data/raw/2026-02-19/tencent_financials.csv`
- `v3/data/raw/2026-02-19/segment_revenue.csv`
- `v3/data/raw/2026-02-19/peer_fundamentals.csv`

And canonical quarterly dataset in:

- `v3/data/processed/tencent_quarterly_financials.csv`

Override policy enforced:

- fundamentals must come from strict 4-quarter TTM where available,
- QA fails investor-grade if override requirements are broken.

### Workstream 4: WACC Engine Upgrade (MM/Hamada + CAPM official, APT diagnostic)

Implemented in:

- `v3/src/tencent_valuation_v3/wacc.py`

Core formulas:

- `beta_U_peer = beta_L_peer / (1 + (1 - T_peer) * D_peer / E_peer)`
- `beta_L_tencent = beta_U_target * (1 + (1 - T_tencent) * D_target / E_target)`
- `Re_CAPM = Rf + beta_L_tencent * ERP`
- `Re_APT = Rf + sum(beta_k * lambda_k)`
- `WACC = E/(D+E)*Re_CAPM + D/(D+E)*Rd*(1-T)`

APT guardrails implemented:

- factor winsorization,
- beta caps,
- lambda shrink/caps,
- stability windows,
- unstable gating with reason codes.

Added key output fields:

- `beta_stability_score`
- `erp_decomposition`
- `apt_unstable_reason_codes`
- factor/premia t-value fields.

### Workstream 5: Multi-Method Valuation Stack

Added 6 additional method layers beyond DCF:

1. APV (`apv.py`)
2. Residual Income (`residual_income.py`)
3. Relative valuation (`comps.py`)
4. SOTP / T-value company bridge (`sotp.py`)
5. Reverse DCF (`reverse_dcf.py`)
6. Ensemble aggregator (`ensemble.py`)

New contracts generated:

- `v3/data/model/apv_outputs.csv`
- `v3/data/model/residual_income_outputs.csv`
- `v3/data/model/peer_multiples.csv`
- `v3/data/model/relative_valuation_outputs.csv`
- `v3/data/model/tvalue_company_bridge.csv`
- `v3/data/model/tvalue_stat_diagnostics.csv`
- `v3/data/model/reverse_dcf_outputs.csv`
- `v3/data/model/valuation_method_outputs.csv`
- `v3/data/model/valuation_ensemble.csv`

### Workstream 6: QA + Backtest + Risk Gates

Extended QA to 21 checks in:

- `v3/src/tencent_valuation_v3/qa.py`

Added checks for:

- schema contracts,
- source manifest health,
- headline NaN gate,
- ensemble band-width sanity,
- override/TTM requirements,
- backtest quality with interval coverage.

Backtest extended in:

- `v3/src/tencent_valuation_v3/backtest.py`

Added outputs:

- `v3/data/model/backtest_summary.csv`
- `v3/data/model/backtest_point_results.csv`
- `v3/data/model/backtest_regime_breakdown.csv`

### Workstream 7: Reporting + Delivery Artifacts

Created reporting layer in:

- `v3/src/tencent_valuation_v3/report.py`

Generated:

- `v3/reports/tencent_valuation_2026-02-19.md`
- `v3/reports/tencent_investment_memo_2026-02-19.md`
- `v3/reports/tencent_v3_compact_log_2026-02-19.md`
- `v3/reports/tencent_v3_delivery_log_2026-02-19.md`

Also created example package:

- `v3/examples/2026-02-19/README.md`

---

## 2) Method Design (How the model thinks)

### Official decision valuation path

- **Discount rate**: CAPM-based WACC only.
- **Valuation core**: DCF with scenarios `base`, `bad`, `extreme`.

### Diagnostic/cross-check path

- APT cost of equity is computed and reported but does not override CAPM when unstable.
- APV, residual income, relative, T-value and reverse DCF provide method triangulation.
- Ensemble combines methods with pre-set weights and penalties when instability/QA risk appears.

### Scenario architecture

Forecast horizon: 7 years.

Base:

- stronger growth,
- higher long-run margin,
- lower capex intensity drift.

Bad:

- slower growth,
- lower margin path,
- higher capital intensity.

Extreme:

- near-term revenue decline,
- deeper margin compression,
- stress capital intensity.

---

## 3) Data Collected and Used

## A) Raw web snapshots (point-in-time)

Folder:

- `v3/data/raw/2026-02-19/`

Source manifest:

- `v3/data/raw/2026-02-19/source_manifest.json`

## B) Processed model inputs

- `v3/data/processed/tencent_financials.csv`
- `v3/data/processed/segment_revenue.csv`
- `v3/data/processed/market_inputs.csv`
- `v3/data/processed/weekly_returns.csv`
- `v3/data/processed/monthly_factors.csv`
- `v3/data/processed/monthly_asset_returns.csv`

## C) Model outputs

Located in:

- `v3/data/model/*`

(Full list in Section 8)

---

## 4) Assumptions and Defaults (material)

From `v3/config/wacc.yaml`, `v3/config/scenarios.yaml`, `v3/config/method_weights.yaml`:

1. Target: `0700.HK`, currency HKD.
2. CAPM official, APT diagnostic.
3. Beta window primary: 2Y weekly (`104w`).
4. Secondary beta checks: `156w` and monthly-window diagnostics.
5. ERP method: rolling excess return, 60m lookback.
6. APT: 60m lookback, min 36 observations, Newey-West HAC.
7. Rd bounds: floor `1.5%`, ceiling `12%`.
8. Scenario horizon: 7 years.
9. Ensemble base weights:
   - DCF 0.35
   - APV 0.20
   - Residual 0.15
   - Relative 0.15
   - SOTP/T-value 0.15
10. Investor-grade requires override + strict TTM method + no failures.

---

## 5) Build-up Pipeline (from raw to final)

Run order used:

1. `fetch --asof 2026-02-19`
2. `build-overrides --asof 2026-02-19`
3. `run-all --asof 2026-02-19 --source-mode live --refresh`

Internally `run-all` executes:

1. factors
2. wacc
3. dcf
4. apv
5. residual-income
6. comps
7. tvalue
8. reverse-dcf
9. backtest
10. qa
11. ensemble
12. reports + compact log

---

## 6) Validation and QA Outcome

QA file:

- `v3/reports/qa_2026-02-19.json`

Summary:

- total checks: **21**
- warnings: **2**
- failures: **0**
- investor_grade: **true**

Warnings:

1. CAPM/APT gap warning (480.8 bps > 150 bps threshold)
2. APT stability gate warning (APT unstable; excluded from headline decision valuation)

Backtest summary (`v3/data/model/backtest_summary.csv`):

- points: 8
- hit rate 12m: 0.75
- calibration MAE 12m (bucket): 0.3475
- interval coverage 12m: 0.75

Regime breakdown (`v3/data/model/backtest_regime_breakdown.csv`):

- risk_off: hit 1.00, MAE 0.186
- risk_on: hit 0.667, MAE 0.401

---

## 7) Final Valuation Answer (current run)

As-of: **2026-02-19**

### A) WACC stack

- Rf annual: **3.37%**
- ERP annual: **3.51%**
- Re_CAPM (official): **8.60%**
- Re_APT guardrailed (diagnostic): **13.40%**
- Rd: **3.43%**
- Target D/E: **0.1668**
- WACC (official): **7.76%**
- APT unstable: **true**

### B) DCF fair value (HKD/share)

- base: **573.78**
- bad: **316.14**
- extreme: **210.88**

### C) Ensemble fair value (HKD/share)

- base: **528.37**
- bad: **316.65**
- extreme: **229.30**

### D) T-value bridge (HKD/share)

- base: **615.62**
- bad: **351.71**
- extreme: **240.18**

### E) Reverse DCF implication

To justify market price 533 HKD under current structure:

- implied terminal growth: **1.95%**
- implied margin shift vs base: **-220.9 bps**
- implied growth shift vs base: **-131.2 bps**

Interpretation:

- Market price is below DCF base but close to ensemble base.
- Market-implied assumptions are weaker than base-case assumptions.

---

## 8) Full Artifact Index

## Core outputs

- `v3/data/model/wacc_components.csv`
- `v3/data/model/capm_apt_compare.csv`
- `v3/data/model/valuation_outputs.csv`
- `v3/data/model/sensitivity_wacc_g.csv`
- `v3/data/model/sensitivity_margin_growth.csv`
- `v3/data/model/scenario_assumptions_used.csv`

## Multi-method outputs

- `v3/data/model/apv_outputs.csv`
- `v3/data/model/residual_income_outputs.csv`
- `v3/data/model/peer_multiples.csv`
- `v3/data/model/relative_valuation_outputs.csv`
- `v3/data/model/tvalue_company_bridge.csv`
- `v3/data/model/tvalue_stat_diagnostics.csv`
- `v3/data/model/reverse_dcf_outputs.csv`
- `v3/data/model/valuation_method_outputs.csv`
- `v3/data/model/valuation_ensemble.csv`

## Validation outputs

- `v3/data/model/backtest_summary.csv`
- `v3/data/model/backtest_point_results.csv`
- `v3/data/model/backtest_regime_breakdown.csv`
- `v3/reports/qa_2026-02-19.json`

## Reports

- `v3/reports/tencent_valuation_2026-02-19.md`
- `v3/reports/tencent_investment_memo_2026-02-19.md`
- `v3/reports/tencent_v3_compact_log_2026-02-19.md`
- `v3/reports/tencent_v3_delivery_log_2026-02-19.md`
- `v3/reports/tencent_v3_full_story_2026-02-28.md` (this file)

---

## 9) Known Limitations (explicit)

1. APT is still unstable vs CAPM; remains diagnostic only.
2. Relative valuation still uses anchored proxy multiples unless peer TTM fundamentals are fully refreshed from filings.
3. Backtest sample is still small (8 points) despite passing gate thresholds.

---

## 10) Bottom Line

V3 is now fully implemented, isolated, tested, and reproducible.

Current investor-grade output (as-of 2026-02-19):

- **PASS** (0 QA failures),
- official WACC from CAPM/MM,
- DCF base value around **573.78 HKD/share**,
- ensemble base around **528.37 HKD/share**,
- market at 533 HKD appears roughly around the ensemble center and below DCF base.
