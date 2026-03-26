from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .dcf import _discount, _get_path, _project_fcff
from .paths import ProjectPaths


class ApvError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApvArtifacts:
    apv_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> ApvArtifacts:
    return ApvArtifacts(apv_outputs=paths.data_model / "apv_outputs.csv")


def _unlevered_cost_of_equity(rf: float, beta_u: float, erp: float) -> float:
    """Ru = Rf + beta_u * ERP (CAPM with unlevered beta, no leverage premium)."""
    return float(rf + beta_u * erp)


def _pv_tax_shields_mm(gross_debt: float, tax_rate: float) -> float:
    """Modigliani-Miller PV of tax shields for constant perpetual debt: PV = t * D."""
    return float(gross_debt * tax_rate)


def _financing_side_effects(scenario: str, gross_debt: float) -> float:
    """Proxy for cost of financial distress / agency costs by scenario."""
    rate = {"base": 0.00, "bad": -0.01, "extreme": -0.03}.get(scenario, -0.01)
    return float(rate * gross_debt)


def run_apv(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> ApvArtifacts:
    """
    Proper Adjusted Present Value implementation.

    Methodology:
      1. Compute unlevered cost of equity: Ru = Rf + beta_u * ERP
      2. Project FCFF independently for each scenario
      3. Discount explicit FCFF at Ru (NOT at WACC)
      4. Terminal value discounted at Ru
      5. PV(tax shields) via MM perpetuity: t * D (constant debt assumption)
      6. Add financing side effects (distress cost proxy)
      7. Bridge to equity via net cash

    This produces values independent of DCF because Ru != WACC when D/E > 0.
    Under MM with taxes: WACC = Ru * (1 - t * D/V), so APV and DCF converge only
    in the limit; for finite leverage they diverge, which is the desired behavior.
    """
    paths.ensure()
    artifacts = _default_artifacts(paths)

    wacc = pd.read_csv(wacc_components_path)
    if wacc.empty:
        raise ApvError("wacc_components.csv is empty")
    wrow = wacc.iloc[0]

    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if fin.empty:
        raise ApvError("tencent_financials.csv is empty")
    base_fin = fin.iloc[0]

    market_inputs = pd.read_csv(paths.data_processed / "market_inputs.csv")

    # Unlevered cost of equity from CAPM with unlevered (asset) beta
    rf = float(wrow["rf_annual"])
    erp = float(wrow["erp_annual"])
    beta_u = float(wrow["beta_u_target"])
    rd = float(wrow["rd"])
    tax_rate = float(wrow["tax_rate_tencent"])
    crp = float(wrow.get("crp", 0.0))
    ru = _unlevered_cost_of_equity(rf, beta_u, erp) + crp

    net_cash = float(base_fin["net_cash_hkd_bn"])
    shares = float(base_fin["shares_out_bn"])

    target_ticker = str(wrow.get("target_ticker", "0700.HK"))
    ticker_mask = market_inputs["ticker"] == target_ticker
    if ticker_mask.any():
        gross_debt = float(market_inputs.loc[ticker_mask, "gross_debt_hkd_bn"].iloc[0])
    else:
        gross_debt = float(market_inputs.loc[market_inputs["ticker"] == "0700.HK", "gross_debt_hkd_bn"].iloc[0])

    pv_ts = _pv_tax_shields_mm(gross_debt, tax_rate)

    years = int(scenarios_config.get("forecast_years", 7))

    rows: list[dict[str, float | str]] = []
    for scenario in ["base", "bad", "extreme"]:
        cfg = scenarios_config["scenarios"][scenario]
        terminal_g = float(cfg["terminal_g"])
        # Ensure Ru - g spread is at least 20 bps to avoid blow-up
        max_g = ru - 0.002
        if terminal_g >= max_g:
            terminal_g = max_g

        revenue_growth = [float(v) for v in cfg["revenue_growth"]]
        ebit_margin = [float(v) for v in cfg["ebit_margin"]]
        capex_path = [float(v) for v in cfg["capex_pct_revenue"]]
        nwc_path = [float(v) for v in cfg["nwc_pct_revenue"]]

        fcff_df = _project_fcff(
            base_revenue_hkd_bn=float(base_fin["revenue_hkd_bn"]),
            dep_pct_revenue=float(base_fin["dep_pct_revenue"]),
            tax_rate=tax_rate,
            years=years,
            revenue_growth=revenue_growth,
            ebit_margin=ebit_margin,
            capex_pct_revenue=capex_path,
            nwc_pct_revenue=nwc_path,
        )

        # Discount explicit-period FCFFs at Ru (unlevered cost of equity)
        pv_fcff_unlevered = 0.0
        for _, row in fcff_df.iterrows():
            pv_fcff_unlevered += _discount(float(row["fcff_hkd_bn"]), ru, int(row["year"]))

        # Terminal value of unlevered firm at Ru
        final_fcff = float(fcff_df.iloc[-1]["fcff_hkd_bn"])
        tv_unlevered = final_fcff * (1.0 + terminal_g) / (ru - terminal_g)
        pv_tv_unlevered = _discount(tv_unlevered, ru, years)

        unlevered_value = pv_fcff_unlevered + pv_tv_unlevered

        # Financing side effects (proxy for distress costs / agency costs)
        fse = _financing_side_effects(scenario, gross_debt)

        # APV enterprise = unlevered firm value + PV(tax shields) + financing side effects
        apv_enterprise = unlevered_value + pv_ts + fse
        equity = apv_enterprise + net_cash
        fair = equity / shares

        rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "method": "apv",
                "ru": ru,
                "unlevered_value_hkd_bn": round(unlevered_value, 4),
                "pv_tax_shield_hkd_bn": round(pv_ts, 4),
                "financing_side_effect_hkd_bn": round(fse, 4),
                "enterprise_value_hkd_bn": round(apv_enterprise, 4),
                "equity_value_hkd_bn": round(equity, 4),
                "fair_value_hkd_per_share": round(fair, 4),
            }
        )

    out = pd.DataFrame(rows)
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    out.to_csv(artifacts.apv_outputs, index=False)
    return artifacts
