"""Helper script to create vintage backtest configs."""
from pathlib import Path

DIR = Path(__file__).parent

TEMPLATE = """\
# Vintage config for backtest as-of dates in {year}
forecast_years: 7
mid_year_discounting: true
scenarios:
  base:
    terminal_g: {tg_base}
    revenue_growth: {growth}
    ebit_margin: {margin}
    capex_pct_revenue: [0.09, 0.09, 0.088, 0.086, 0.085, 0.084, 0.083]
    nwc_pct_revenue: [0.020, 0.020, 0.019, 0.019, 0.018, 0.018, 0.018]
    sbc_pct_revenue: [0.015, 0.015, 0.014, 0.014, 0.013, 0.013, 0.012]
  bad:
    terminal_g: {tg_bad}
    revenue_growth: [0.03, 0.03, 0.03, 0.032, 0.033, 0.034, 0.035]
    ebit_margin: [0.30, 0.298, 0.296, 0.294, 0.293, 0.292, 0.291]
    capex_pct_revenue: [0.095, 0.095, 0.094, 0.093, 0.092, 0.091, 0.090]
    nwc_pct_revenue: [0.022, 0.022, 0.022, 0.021, 0.021, 0.021, 0.021]
    sbc_pct_revenue: [0.016, 0.016, 0.015, 0.015, 0.015, 0.015, 0.015]
  extreme:
    terminal_g: {tg_ext}
    revenue_growth: [-0.05, -0.03, 0.01, 0.02, 0.025, 0.03, 0.03]
    ebit_margin: [0.28, 0.275, 0.272, 0.270, 0.268, 0.266, 0.265]
    capex_pct_revenue: [0.10, 0.10, 0.10, 0.098, 0.097, 0.096, 0.095]
    nwc_pct_revenue: [0.024, 0.024, 0.024, 0.023, 0.023, 0.023, 0.023]
    sbc_pct_revenue: [0.018, 0.018, 0.017, 0.016, 0.015, 0.015, 0.015]
sensitivities:
  wacc_shifts_bps: [-100, -50, 0, 50, 100]
  terminal_g_shifts_bps: [-100, 0, 100]
  growth_shifts_bps: [-200, 0, 200]
  margin_shifts_bps: [-200, 0, 200]
"""

VINTAGES = {
    "2018": dict(growth="[0.22, 0.20, 0.18, 0.16, 0.14, 0.12, 0.10]",
                 margin="[0.28, 0.29, 0.30, 0.31, 0.31, 0.32, 0.32]",
                 tg_base=0.03, tg_bad=0.015, tg_ext=0.0),
    "2019": dict(growth="[0.20, 0.18, 0.16, 0.14, 0.12, 0.10, 0.09]",
                 margin="[0.29, 0.30, 0.31, 0.32, 0.32, 0.33, 0.33]",
                 tg_base=0.03, tg_bad=0.015, tg_ext=0.0),
    "2020": dict(growth="[0.28, 0.22, 0.18, 0.15, 0.12, 0.10, 0.09]",
                 margin="[0.30, 0.31, 0.32, 0.33, 0.33, 0.34, 0.34]",
                 tg_base=0.03, tg_bad=0.015, tg_ext=0.0),
    "2021": dict(growth="[0.22, 0.18, 0.15, 0.12, 0.10, 0.09, 0.08]",
                 margin="[0.32, 0.33, 0.34, 0.34, 0.35, 0.35, 0.35]",
                 tg_base=0.028, tg_bad=0.012, tg_ext=0.0),
    "2022": dict(growth="[0.05, 0.07, 0.09, 0.10, 0.10, 0.09, 0.08]",
                 margin="[0.28, 0.30, 0.32, 0.33, 0.34, 0.35, 0.35]",
                 tg_base=0.025, tg_bad=0.010, tg_ext=0.0),
    "2023": dict(growth="[0.10, 0.10, 0.09, 0.09, 0.08, 0.08, 0.07]",
                 margin="[0.33, 0.34, 0.35, 0.36, 0.36, 0.37, 0.37]",
                 tg_base=0.025, tg_bad=0.010, tg_ext=0.0),
    "2024": dict(growth="[0.09, 0.09, 0.085, 0.08, 0.075, 0.07, 0.065]",
                 margin="[0.35, 0.355, 0.36, 0.362, 0.365, 0.368, 0.370]",
                 tg_base=0.025, tg_bad=0.010, tg_ext=0.0),
    "2025": dict(growth="[0.08, 0.08, 0.075, 0.07, 0.065, 0.06, 0.055]",
                 margin="[0.36, 0.365, 0.368, 0.37, 0.372, 0.373, 0.374]",
                 tg_base=0.025, tg_bad=0.010, tg_ext=0.0),
}

for year, v in VINTAGES.items():
    content = TEMPLATE.format(year=year, **v)
    (DIR / f"{year}.yaml").write_text(content, encoding="utf-8")
    print(f"Created {year}.yaml")
