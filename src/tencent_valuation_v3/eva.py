"""Phase 4B: Excess Return / EVA (Economic Value Added) model.

For each scenario:
  1. Estimate IC_0 (invested capital) from financials proxy.
  2. Project NOPAT and IC year-by-year.
  3. EVA_t = NOPAT_t - WACC * IC_{t-1}
  4. Enterprise value = IC_0 + PV(EVA_explicit) + PV(EVA_terminal)
  5. Equity = Enterprise + net_cash; fair value = equity / shares.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .dcf import _discount, _get_path, _project_fcff
from .paths import ProjectPaths


class EvaError(RuntimeError):
    pass


@dataclass(frozen=True)
class EvaArtifacts:
    eva_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> EvaArtifacts:
    return EvaArtifacts(eva_outputs=paths.data_model / "eva_outputs.csv")


def _run_eva_scenario(
    scenario_name: str,
    scenario_cfg: dict,
    years: int,
    wacc: float,
    tax_rate: float,
    base_fin: pd.Series,
    mid_year: bool = False,
) -> dict[str, float | str]:
    """Compute EVA-based fair value for one scenario."""
    revenue_growth = [float(v) for v in scenario_cfg["revenue_growth"]]
    ebit_margin = [float(v) for v in scenario_cfg["ebit_margin"]]
    capex_pct = [float(v) for v in scenario_cfg["capex_pct_revenue"]]
    nwc_pct = [float(v) for v in scenario_cfg["nwc_pct_revenue"]]
    sbc_pct: list[float] | None = (
        [float(v) for v in scenario_cfg["sbc_pct_revenue"]]
        if "sbc_pct_revenue" in scenario_cfg
        else None
    )
    terminal_g = float(scenario_cfg["terminal_g"])
    terminal_g = min(terminal_g, wacc - 0.002)

    base_revenue = float(base_fin["revenue_hkd_bn"])
    dep_pct = float(base_fin["dep_pct_revenue"])
    net_cash = float(base_fin["net_cash_hkd_bn"])
    shares_bn = float(base_fin["shares_out_bn"])

    # IC_0 proxy: steady-state PP&E + NWC
    # Steady-state PP&E = capex / depreciation rate (both as pct of revenue)
    capex_pct_0 = float(_get_path(capex_pct, years)[0])
    nwc_pct_0 = float(_get_path(nwc_pct, years)[0])
    ic_0 = base_revenue * (capex_pct_0 / max(dep_pct, 1e-4) + nwc_pct_0)

    fcff_df = _project_fcff(
        base_revenue_hkd_bn=base_revenue,
        dep_pct_revenue=dep_pct,
        tax_rate=tax_rate,
        years=years,
        revenue_growth=revenue_growth,
        ebit_margin=ebit_margin,
        capex_pct_revenue=capex_pct,
        nwc_pct_revenue=nwc_pct,
        sbc_pct_revenue=sbc_pct,
    )

    pv_eva = 0.0
    ic_prev = ic_0
    cap_period_years = 0
    eva_y1: float = float("nan")
    for _, row in fcff_df.iterrows():
        year = int(row["year"])
        nopat = float(row["ebit_hkd_bn"]) * (1.0 - tax_rate)
        fcff = float(row["fcff_hkd_bn"])
        eva = nopat - wacc * ic_prev

        if year == 1:
            eva_y1 = eva

        if eva > 0:
            cap_period_years = year

        yr: float = year - 0.5 if mid_year else float(year)
        pv_eva += _discount(eva, wacc, yr)

        # IC grows by net investment = NOPAT - FCFF
        ic_prev = ic_prev + (nopat - fcff)
        ic_prev = max(ic_prev, 0.0)

    # Terminal EVA: perpetuity of last-year EVA grown at terminal_g
    last_nopat = float(fcff_df.iloc[-1]["ebit_hkd_bn"]) * (1.0 - tax_rate)
    last_fcff = float(fcff_df.iloc[-1]["fcff_hkd_bn"])
    terminal_nopat = last_nopat * (1.0 + terminal_g)
    terminal_eva = terminal_nopat - wacc * ic_prev

    if wacc > terminal_g and terminal_eva > 0:
        tv_eva = terminal_eva / (wacc - terminal_g)
    else:
        tv_eva = 0.0

    pv_tv_eva = _discount(tv_eva, wacc, years)

    enterprise_hkd_bn = ic_0 + pv_eva + pv_tv_eva
    equity_hkd_bn = enterprise_hkd_bn + net_cash
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
        "ic_0_hkd_bn": ic_0,
        "eva_y1_hkd_bn": eva_y1,
        "competitive_advantage_period_years": cap_period_years,
    }


def run_eva(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> EvaArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    financials = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if financials.empty:
        raise EvaError("tencent_financials.csv is empty")
    base_fin = financials.iloc[0]

    wacc_frame = pd.read_csv(wacc_components_path)
    if wacc_frame.empty:
        raise EvaError("wacc_components.csv is empty")
    wacc = float(wacc_frame.iloc[0]["wacc"])
    tax_rate = float(wacc_frame.iloc[0]["tax_rate_tencent"])

    years = int(scenarios_config["forecast_years"])
    mid_year = bool(scenarios_config.get("mid_year_discounting", False))

    rows = []
    for name in ["base", "bad", "extreme"]:
        cfg = scenarios_config["scenarios"][name]
        result = _run_eva_scenario(name, cfg, years, wacc, tax_rate, base_fin, mid_year=mid_year)
        result["asof"] = asof
        result["wacc"] = wacc
        rows.append(result)

    pd.DataFrame(rows).to_csv(artifacts.eva_outputs, index=False)
    return artifacts
