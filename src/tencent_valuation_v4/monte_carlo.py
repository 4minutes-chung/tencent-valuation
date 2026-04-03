"""Phase 4A: Monte Carlo DCF simulation.

Samples WACC, terminal_g, revenue growth, and EBIT margin from
correlated distributions centred on the base scenario.  Runs
*n_simulations* mini-DCFs and outputs a full distribution plus
key percentiles.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .dcf import _discount, _get_path, _project_fcff
from .paths import ProjectPaths


class MonteCarloError(RuntimeError):
    pass


@dataclass(frozen=True)
class MonteCarloArtifacts:
    monte_carlo_outputs: Path
    monte_carlo_percentiles: Path


def _default_artifacts(paths: ProjectPaths) -> MonteCarloArtifacts:
    return MonteCarloArtifacts(
        monte_carlo_outputs=paths.data_model / "monte_carlo_outputs.csv",
        monte_carlo_percentiles=paths.data_model / "monte_carlo_percentiles.csv",
    )


def _mini_dcf(
    base_revenue: float,
    dep_pct: float,
    tax_rate: float,
    net_cash: float,
    shares_bn: float,
    revenue_growth: list[float],
    ebit_margin: list[float],
    capex_pct: list[float],
    nwc_pct: list[float],
    sbc_pct: list[float] | None,
    wacc: float,
    terminal_g: float,
    years: int,
    mid_year: bool,
) -> float:
    """Run a minimal DCF and return fair value per share."""
    terminal_g = min(terminal_g, wacc - 0.002)

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

    pv_fcff = 0.0
    for _, row in fcff_df.iterrows():
        yr = float(row["year"]) - 0.5 if mid_year else float(row["year"])
        pv_fcff += _discount(float(row["fcff_hkd_bn"]), wacc, yr)

    final_fcff = float(fcff_df.iloc[-1]["fcff_hkd_bn"])
    tv = final_fcff * (1.0 + terminal_g) / (wacc - terminal_g)
    pv_tv = _discount(tv, wacc, years)

    ev = pv_fcff + pv_tv
    equity = ev + net_cash
    return equity / shares_bn


def run_monte_carlo(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
    n_simulations: int | None = None,
    seed: int | None = None,
) -> MonteCarloArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    financials = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if financials.empty:
        raise MonteCarloError("tencent_financials.csv is empty")
    base_fin = financials.iloc[0]

    wacc_frame = pd.read_csv(wacc_components_path)
    if wacc_frame.empty:
        raise MonteCarloError("wacc_components.csv is empty")
    wacc_base = float(wacc_frame.iloc[0]["wacc"])
    tax_rate = float(wacc_frame.iloc[0]["tax_rate_tencent"])

    years = int(scenarios_config["forecast_years"])
    mid_year = bool(scenarios_config.get("mid_year_discounting", False))
    base_cfg = scenarios_config["scenarios"]["base"]

    mc_cfg = scenarios_config.get("monte_carlo", {})
    n_sims = int(n_simulations if n_simulations is not None else mc_cfg.get("n_simulations", 10000))
    growth_std = float(mc_cfg.get("growth_std", 0.03))
    margin_std = float(mc_cfg.get("margin_std", 0.02))
    wacc_std = float(mc_cfg.get("wacc_std", 0.005))
    tg_std = float(mc_cfg.get("terminal_g_std", 0.005))
    corr_gm = float(mc_cfg.get("correlation_growth_margin", -0.3))

    base_growth = [float(v) for v in base_cfg["revenue_growth"]]
    base_margin = [float(v) for v in base_cfg["ebit_margin"]]
    base_capex = [float(v) for v in base_cfg["capex_pct_revenue"]]
    base_nwc = [float(v) for v in base_cfg["nwc_pct_revenue"]]
    base_tg = float(base_cfg["terminal_g"])
    sbc_base: list[float] | None = (
        [float(v) for v in base_cfg["sbc_pct_revenue"]]
        if "sbc_pct_revenue" in base_cfg
        else None
    )

    base_revenue = float(base_fin["revenue_hkd_bn"])
    dep_pct = float(base_fin["dep_pct_revenue"])
    net_cash = float(base_fin["net_cash_hkd_bn"])
    shares_bn = float(base_fin["shares_out_bn"])

    capex_path = _get_path(base_capex, years)
    nwc_path = _get_path(base_nwc, years)
    sbc_path = _get_path(sbc_base, years) if sbc_base else None

    # Correlated sampling: growth shift and margin shift are correlated
    rng = np.random.default_rng(seed)
    cov = np.array([
        [growth_std**2, corr_gm * growth_std * margin_std],
        [corr_gm * growth_std * margin_std, margin_std**2],
    ])
    gm_shifts = rng.multivariate_normal([0.0, 0.0], cov, size=n_sims)
    wacc_draws = rng.normal(wacc_base, wacc_std, size=n_sims)
    tg_draws = rng.normal(base_tg, tg_std, size=n_sims)

    rows = []
    growth_base_full = _get_path(base_growth, years)
    margin_base_full = _get_path(base_margin, years)

    for i in range(n_sims):
        g_shift = float(gm_shifts[i, 0])
        m_shift = float(gm_shifts[i, 1])
        w = max(0.02, float(wacc_draws[i]))
        tg = float(tg_draws[i])

        growth = [max(-0.50, g + g_shift) for g in growth_base_full]
        margin = [max(0.0, min(0.90, m + m_shift)) for m in margin_base_full]

        try:
            fv = _mini_dcf(
                base_revenue=base_revenue,
                dep_pct=dep_pct,
                tax_rate=tax_rate,
                net_cash=net_cash,
                shares_bn=shares_bn,
                revenue_growth=growth,
                ebit_margin=margin,
                capex_pct=capex_path,
                nwc_pct=nwc_path,
                sbc_pct=sbc_path,
                wacc=w,
                terminal_g=tg,
                years=years,
                mid_year=mid_year,
            )
        except Exception:  # noqa: BLE001
            continue

        rows.append({
            "sim_id": i,
            "fair_value_hkd_per_share": fv,
            "wacc": w,
            "terminal_g": tg,
            "growth_shift": g_shift,
            "margin_shift": m_shift,
        })

    if not rows:
        raise MonteCarloError("All Monte Carlo simulations failed")

    mc_df = pd.DataFrame(rows)
    mc_df.to_csv(artifacts.monte_carlo_outputs, index=False)

    fv_series = mc_df["fair_value_hkd_per_share"].astype(float)
    pct_rows = [
        {
            "asof": asof,
            "percentile": p,
            "fair_value_hkd_per_share": float(np.percentile(fv_series, p)),
        }
        for p in [5, 10, 25, 50, 75, 90, 95]
    ]
    pd.DataFrame(pct_rows).to_csv(artifacts.monte_carlo_percentiles, index=False)

    return artifacts
