# Tencent Valuation V3 (Standalone)

V3 is a fully isolated Tencent valuation program under `v3/`.
It does not read/write V1/V2 model outputs by default.

## Core Policy

- Official discount rate: CAPM-based WACC.
- APT: diagnostic only (guardrailed; can be unstable).
- Scenarios: `base`, `bad`, `extreme`.
- Reporting currency: HKD.

## Commands

```bash
tencent-valuation-v3 fetch --asof YYYY-MM-DD
tencent-valuation-v3 build-overrides --asof YYYY-MM-DD
tencent-valuation-v3 factors --asof YYYY-MM-DD [--refresh] [--source-mode auto|live|synthetic]
tencent-valuation-v3 wacc --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 dcf --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 apv --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 residual-income --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 comps --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 tvalue --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 reverse-dcf --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 ensemble --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 qa --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 report --asof YYYY-MM-DD [--refresh-factors] [--source-mode auto|live|synthetic]
tencent-valuation-v3 backtest --start YYYY-MM-DD --end YYYY-MM-DD --freq quarterly [--source-mode auto|live|synthetic]
tencent-valuation-v3 run-all --asof YYYY-MM-DD --source-mode live --refresh
```

## Output Root

All outputs are written under `v3/data` and `v3/reports`.

## Quick Start

```bash
cd "/Users/stevenchung/Desktop/P12B_File/Tencent Model/v3"
pip install -e .
tencent-valuation-v3 fetch --asof 2026-02-19
tencent-valuation-v3 build-overrides --asof 2026-02-19
tencent-valuation-v3 run-all --asof 2026-02-19 --source-mode live --refresh
```
