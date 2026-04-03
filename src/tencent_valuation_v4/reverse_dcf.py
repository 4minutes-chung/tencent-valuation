from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .dcf import _project_fcff
from .paths import ProjectPaths


class ReverseDcfError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReverseDcfArtifacts:
    reverse_dcf_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> ReverseDcfArtifacts:
    return ReverseDcfArtifacts(reverse_dcf_outputs=paths.data_model / "reverse_dcf_outputs.csv")


def _discount(value: float, rate: float, year: int) -> float:
    return float(value / ((1.0 + rate) ** year))


def _ev_with_terminal_g(
    base_revenue: float,
    dep_pct: float,
    tax_rate: float,
    years: int,
    growth: list[float],
    margin: list[float],
    capex: list[float],
    nwc: list[float],
    wacc: float,
    g: float,
) -> float:
    fcff = _project_fcff(
        base_revenue_hkd_bn=base_revenue,
        dep_pct_revenue=dep_pct,
        tax_rate=tax_rate,
        years=years,
        revenue_growth=growth,
        ebit_margin=margin,
        capex_pct_revenue=capex,
        nwc_pct_revenue=nwc,
    )
    pv_fcff = 0.0
    for _, row in fcff.iterrows():
        pv_fcff += _discount(float(row["fcff_hkd_bn"]), wacc, int(row["year"]))
    final_fcff = float(fcff.iloc[-1]["fcff_hkd_bn"])
    g_eff = min(g, wacc - 0.002)
    terminal_value = final_fcff * (1.0 + g_eff) / max(1e-6, (wacc - g_eff))
    pv_terminal = _discount(terminal_value, wacc, years)
    return pv_fcff + pv_terminal


def _bisection(fn, lo: float, hi: float, iters: int = 80) -> float:
    vlo = fn(lo)
    vhi = fn(hi)
    if np.sign(vlo) == np.sign(vhi):
        return lo if abs(vlo) <= abs(vhi) else hi

    a = lo
    b = hi
    for _ in range(iters):
        m = 0.5 * (a + b)
        vm = fn(m)
        if np.sign(vm) == np.sign(vlo):
            a = m
            vlo = vm
        else:
            b = m
            vhi = vm
    return 0.5 * (a + b)


def run_reverse_dcf(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> ReverseDcfArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    wacc = pd.read_csv(wacc_components_path)
    if fin.empty or wacc.empty:
        raise ReverseDcfError("Missing inputs for reverse DCF")

    frow = fin.iloc[0]
    wrow = wacc.iloc[0]

    years = int(scenarios_config.get("forecast_years", 7))
    base_cfg = scenarios_config["scenarios"]["base"]

    growth = [float(x) for x in base_cfg["revenue_growth"]][:years]
    margin_base = [float(x) for x in base_cfg["ebit_margin"]][:years]
    capex = [float(x) for x in base_cfg["capex_pct_revenue"]][:years]
    nwc = [float(x) for x in base_cfg["nwc_pct_revenue"]][:years]

    base_revenue = float(frow["revenue_hkd_bn"])
    dep_pct = float(frow["dep_pct_revenue"])
    tax_rate = float(wrow["tax_rate_tencent"])
    wacc_rate = float(wrow["wacc"])
    market_price = float(frow["current_price_hkd"])
    shares = float(frow["shares_out_bn"])
    net_cash = float(frow["net_cash_hkd_bn"])

    target_equity = market_price * shares
    target_ev = target_equity - net_cash

    def ev_gap_for_g(g: float) -> float:
        ev = _ev_with_terminal_g(
            base_revenue=base_revenue,
            dep_pct=dep_pct,
            tax_rate=tax_rate,
            years=years,
            growth=growth,
            margin=margin_base,
            capex=capex,
            nwc=nwc,
            wacc=wacc_rate,
            g=g,
        )
        return ev - target_ev

    implied_terminal_g = _bisection(ev_gap_for_g, lo=-0.05, hi=max(-0.01, wacc_rate - 0.005))

    terminal_g_base = float(base_cfg["terminal_g"])

    def ev_gap_for_margin_delta(delta: float) -> float:
        margin = [m + delta for m in margin_base]
        ev = _ev_with_terminal_g(
            base_revenue=base_revenue,
            dep_pct=dep_pct,
            tax_rate=tax_rate,
            years=years,
            growth=growth,
            margin=margin,
            capex=capex,
            nwc=nwc,
            wacc=wacc_rate,
            g=terminal_g_base,
        )
        return ev - target_ev

    implied_margin_delta = _bisection(ev_gap_for_margin_delta, lo=-0.20, hi=0.20)

    implied_growth_delta = 0.0

    def ev_gap_for_growth_delta(delta: float) -> float:
        growth_shifted = [g + delta for g in growth]
        ev = _ev_with_terminal_g(
            base_revenue=base_revenue,
            dep_pct=dep_pct,
            tax_rate=tax_rate,
            years=years,
            growth=growth_shifted,
            margin=margin_base,
            capex=capex,
            nwc=nwc,
            wacc=wacc_rate,
            g=terminal_g_base,
        )
        return ev - target_ev

    implied_growth_delta = _bisection(ev_gap_for_growth_delta, lo=-0.20, hi=0.20)

    pd.DataFrame(
        [
            {
                "asof": asof,
                "market_price_hkd": market_price,
                "market_equity_value_hkd_bn": target_equity,
                "market_enterprise_value_hkd_bn": target_ev,
                "implied_terminal_g": implied_terminal_g,
                "implied_margin_shift_bps": implied_margin_delta * 10000.0,
                "implied_growth_shift_bps": implied_growth_delta * 10000.0,
                "wacc_used": wacc_rate,
            }
        ]
    ).to_csv(artifacts.reverse_dcf_outputs, index=False)

    return artifacts
