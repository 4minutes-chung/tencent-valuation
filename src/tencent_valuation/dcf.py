from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import ProjectPaths


class DcfError(RuntimeError):
    pass


@dataclass(frozen=True)
class DcfArtifacts:
    valuation_outputs: Path
    sensitivity_wacc_g: Path
    sensitivity_margin_growth: Path
    scenario_assumptions_used: Path



def _default_artifacts(paths: ProjectPaths) -> DcfArtifacts:
    return DcfArtifacts(
        valuation_outputs=paths.data_model / "valuation_outputs.csv",
        sensitivity_wacc_g=paths.data_model / "sensitivity_wacc_g.csv",
        sensitivity_margin_growth=paths.data_model / "sensitivity_margin_growth.csv",
        scenario_assumptions_used=paths.data_model / "scenario_assumptions_used.csv",
    )



def _get_path(path_values: list[float], years: int) -> list[float]:
    if not path_values:
        raise DcfError("Scenario path must contain at least one value")
    if len(path_values) >= years:
        return [float(x) for x in path_values[:years]]
    last = float(path_values[-1])
    return [float(x) for x in path_values] + [last] * (years - len(path_values))



def _project_fcff(
    base_revenue_hkd_bn: float,
    dep_pct_revenue: float,
    tax_rate: float,
    years: int,
    revenue_growth: list[float],
    ebit_margin: list[float],
    capex_pct_revenue: list[float],
    nwc_pct_revenue: list[float],
) -> pd.DataFrame:
    growth = _get_path(revenue_growth, years)
    margin = _get_path(ebit_margin, years)
    capex = _get_path(capex_pct_revenue, years)
    nwc = _get_path(nwc_pct_revenue, years)

    rows: list[dict[str, float | int]] = []
    prev_revenue = float(base_revenue_hkd_bn)
    for year in range(1, years + 1):
        rev = prev_revenue * (1.0 + growth[year - 1])
        ebit = rev * margin[year - 1]
        nopat = ebit * (1.0 - tax_rate)
        dep = rev * dep_pct_revenue
        capex_amt = rev * capex[year - 1]
        delta_nwc = (rev - prev_revenue) * nwc[year - 1]
        fcff = nopat + dep - capex_amt - delta_nwc

        rows.append(
            {
                "year": year,
                "revenue_hkd_bn": rev,
                "ebit_hkd_bn": ebit,
                "fcff_hkd_bn": fcff,
            }
        )
        prev_revenue = rev

    return pd.DataFrame(rows)



def _discount(value: float, rate: float, year: int) -> float:
    return float(value / ((1.0 + rate) ** year))



def _scenario_value(
    scenario_name: str,
    scenario_cfg: dict,
    years: int,
    wacc: float,
    tax_rate: float,
    base_fin: pd.Series,
    terminal_shift: float = 0.0,
    growth_shift: float = 0.0,
    margin_shift: float = 0.0,
) -> dict[str, float | str]:
    revenue_growth = [float(v) + growth_shift for v in scenario_cfg["revenue_growth"]]
    ebit_margin = [float(v) + margin_shift for v in scenario_cfg["ebit_margin"]]
    capex_path = [float(v) for v in scenario_cfg["capex_pct_revenue"]]
    nwc_path = [float(v) for v in scenario_cfg["nwc_pct_revenue"]]

    fcff = _project_fcff(
        base_revenue_hkd_bn=float(base_fin["revenue_hkd_bn"]),
        dep_pct_revenue=float(base_fin["dep_pct_revenue"]),
        tax_rate=tax_rate,
        years=years,
        revenue_growth=revenue_growth,
        ebit_margin=ebit_margin,
        capex_pct_revenue=capex_path,
        nwc_pct_revenue=nwc_path,
    )

    terminal_g = float(scenario_cfg["terminal_g"]) + terminal_shift
    wacc_eff = float(wacc)
    max_terminal = wacc_eff - 0.002
    if terminal_g >= max_terminal:
        terminal_g = max_terminal

    pv_fcff = 0.0
    for _, row in fcff.iterrows():
        pv_fcff += _discount(float(row["fcff_hkd_bn"]), wacc_eff, int(row["year"]))

    final_fcff = float(fcff.iloc[-1]["fcff_hkd_bn"])
    terminal_value = final_fcff * (1.0 + terminal_g) / (wacc_eff - terminal_g)
    pv_terminal = _discount(terminal_value, wacc_eff, years)

    enterprise_hkd_bn = pv_fcff + pv_terminal
    equity_hkd_bn = enterprise_hkd_bn + float(base_fin["net_cash_hkd_bn"])
    shares_bn = float(base_fin["shares_out_bn"])
    fair_value = equity_hkd_bn / shares_bn
    market_price = float(base_fin["current_price_hkd"])
    mos = (fair_value - market_price) / market_price

    return {
        "scenario": scenario_name,
        "enterprise_value_hkd_bn": enterprise_hkd_bn,
        "equity_value_hkd_bn": equity_hkd_bn,
        "fair_value_hkd_per_share": fair_value,
        "market_price_hkd": market_price,
        "margin_of_safety": mos,
    }



def run_valuation(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> DcfArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    financials = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if financials.empty:
        raise DcfError("tencent_financials.csv is empty")
    base_fin = financials.iloc[0]

    wacc_frame = pd.read_csv(wacc_components_path)
    if wacc_frame.empty:
        raise DcfError("wacc_components.csv is empty")

    row = wacc_frame.iloc[0]
    wacc = float(row["wacc"])
    tax_rate = float(row["tax_rate_tencent"])

    years = int(scenarios_config["forecast_years"])
    scenario_order = ["base", "bad", "extreme"]
    derivation_rules = {
        "base": "trailing_trend_normalized",
        "bad": "base_stress_delta",
        "extreme": "base_shock_path",
    }

    out_rows: list[dict[str, float | str]] = []
    assumption_rows: list[dict[str, float | str | int]] = []
    for name in scenario_order:
        cfg = scenarios_config["scenarios"][name]
        val = _scenario_value(name, cfg, years, wacc, tax_rate, base_fin)
        val["asof"] = asof
        val["wacc"] = wacc
        out_rows.append(val)

        growth = _get_path([float(v) for v in cfg["revenue_growth"]], years)
        margin = _get_path([float(v) for v in cfg["ebit_margin"]], years)
        capex = _get_path([float(v) for v in cfg["capex_pct_revenue"]], years)
        nwc = _get_path([float(v) for v in cfg["nwc_pct_revenue"]], years)
        for year in range(1, years + 1):
            assumption_rows.append(
                {
                    "asof": asof,
                    "scenario": name,
                    "year": year,
                    "rev_growth": growth[year - 1],
                    "ebit_margin": margin[year - 1],
                    "capex_pct_rev": capex[year - 1],
                    "nwc_pct_rev": nwc[year - 1],
                    "derivation_rule": derivation_rules.get(name, "configured"),
                }
            )

    valuation = pd.DataFrame(out_rows)
    valuation.to_csv(artifacts.valuation_outputs, index=False)
    pd.DataFrame(assumption_rows).to_csv(artifacts.scenario_assumptions_used, index=False)

    sens_cfg = scenarios_config["sensitivities"]
    base_cfg = scenarios_config["scenarios"]["base"]

    wg_rows: list[dict[str, float | str]] = []
    for w_shift_bps in sens_cfg["wacc_shifts_bps"]:
        for g_shift_bps in sens_cfg["terminal_g_shifts_bps"]:
            shifted = _scenario_value(
                "base",
                base_cfg,
                years,
                wacc=wacc + (float(w_shift_bps) / 10000.0),
                tax_rate=tax_rate,
                base_fin=base_fin,
                terminal_shift=float(g_shift_bps) / 10000.0,
            )
            wg_rows.append(
                {
                    "asof": asof,
                    "wacc_shift_bps": float(w_shift_bps),
                    "terminal_g_shift_bps": float(g_shift_bps),
                    "fair_value_hkd_per_share": shifted["fair_value_hkd_per_share"],
                }
            )

    pd.DataFrame(wg_rows).to_csv(artifacts.sensitivity_wacc_g, index=False)

    mg_rows: list[dict[str, float | str]] = []
    for growth_shift in sens_cfg["growth_shifts_bps"]:
        for margin_shift in sens_cfg["margin_shifts_bps"]:
            shifted = _scenario_value(
                "base",
                base_cfg,
                years,
                wacc=wacc,
                tax_rate=tax_rate,
                base_fin=base_fin,
                growth_shift=float(growth_shift) / 10000.0,
                margin_shift=float(margin_shift) / 10000.0,
            )
            mg_rows.append(
                {
                    "asof": asof,
                    "growth_shift_bps": float(growth_shift),
                    "margin_shift_bps": float(margin_shift),
                    "fair_value_hkd_per_share": shifted["fair_value_hkd_per_share"],
                }
            )

    pd.DataFrame(mg_rows).to_csv(artifacts.sensitivity_margin_growth, index=False)

    return artifacts
