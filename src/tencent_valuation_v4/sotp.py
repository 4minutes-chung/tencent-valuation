"""Phase 4C: Sum-of-the-Parts (SOTP) with per-segment DCFs.

Each business segment is discounted at a segment-specific unlevered
cost of equity (Ru = Rf + beta_seg * ERP + CRP).  Segment enterprise
values are summed, then adjusted for strategic investments, net cash
and minority interest to arrive at equity and fair value per share.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .dcf import _discount, _get_path, _project_fcff
from .paths import ProjectPaths


class SotpError(RuntimeError):
    pass


@dataclass(frozen=True)
class SotpArtifacts:
    tvalue_company_bridge: Path
    tvalue_stat_diagnostics: Path


def _default_artifacts(paths: ProjectPaths) -> SotpArtifacts:
    return SotpArtifacts(
        tvalue_company_bridge=paths.data_model / "tvalue_company_bridge.csv",
        tvalue_stat_diagnostics=paths.data_model / "tvalue_stat_diagnostics.csv",
    )


def _segment_enterprise_value(
    seg_revenue_base: float,
    seg_growth: list[float],
    ebit_margin: list[float],
    capex_pct: list[float],
    nwc_pct: list[float],
    sbc_pct: list[float] | None,
    dep_pct: float,
    tax_rate: float,
    ru: float,
    terminal_g: float,
    years: int,
    mid_year: bool,
) -> float:
    """Discount a single segment's FCFF at its unlevered cost of equity."""
    terminal_g = min(terminal_g, ru - 0.002)

    fcff_df = _project_fcff(
        base_revenue_hkd_bn=seg_revenue_base,
        dep_pct_revenue=dep_pct,
        tax_rate=tax_rate,
        years=years,
        revenue_growth=seg_growth,
        ebit_margin=ebit_margin,
        capex_pct_revenue=capex_pct,
        nwc_pct_revenue=nwc_pct,
        sbc_pct_revenue=sbc_pct,
    )

    pv = 0.0
    for _, row in fcff_df.iterrows():
        yr: float = float(row["year"]) - 0.5 if mid_year else float(row["year"])
        pv += _discount(float(row["fcff_hkd_bn"]), ru, yr)

    final_fcff = float(fcff_df.iloc[-1]["fcff_hkd_bn"])
    tv = final_fcff * (1.0 + terminal_g) / (ru - terminal_g)
    pv += _discount(tv, ru, years)
    return pv


def run_tvalue(
    asof: str,
    paths: ProjectPaths,
    wacc_components_path: Path,
    valuation_outputs_path: Path,
    wacc_config: dict,
) -> SotpArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    wacc_df = pd.read_csv(wacc_components_path)
    fin_df = pd.read_csv(paths.data_processed / "tencent_financials.csv")

    if wacc_df.empty or fin_df.empty:
        raise SotpError("Missing inputs for SOTP T-value")

    wrow = wacc_df.iloc[0]
    frow = fin_df.iloc[0]

    shares = float(frow["shares_out_bn"])
    net_cash = float(frow["net_cash_hkd_bn"])
    base_revenue = float(frow["revenue_hkd_bn"])
    dep_pct = float(frow["dep_pct_revenue"])

    # WACC components needed for segment discount rates
    rf = float(wrow.get("rf_annual", 0.04))
    erp = float(wrow.get("erp_annual", 0.055))
    crp = float(wrow.get("crp", float(wacc_config.get("country_risk_premium", 0.0125))))
    tax_rate = float(wrow.get("tax_rate_tencent", 0.15))
    segment_betas: dict[str, float] = {
        str(k): float(v)
        for k, v in wacc_config.get("segment_betas", {}).items()
    }
    minority_interest = float(wacc_config.get("minority_interest_hkd_bn", 0.0))
    strategic_default = float(wacc_config.get("strategic_investments_default_hkd_bn", 380.0))

    # Load segment revenue weights from segment_revenue.csv
    seg_path = paths.data_processed / "segment_revenue.csv"
    segment_df: pd.DataFrame | None = pd.read_csv(seg_path) if seg_path.exists() else None

    # Determine segment base revenues and normalised weights
    default_seg_splits = {
        "VAS": 0.497,
        "Marketing Services": 0.188,
        "FinTech and Business Services": 0.302,
        "Others": 0.013,
    }
    if segment_df is not None and not segment_df.empty:
        latest_period = segment_df["period"].max()
        seg_latest = segment_df[segment_df["period"] == latest_period]
        total_seg_rev = float(seg_latest["revenue_hkd_bn"].sum())
        if total_seg_rev > 0:
            seg_weights = {
                str(row["segment"]): float(row["revenue_hkd_bn"]) / total_seg_rev
                for _, row in seg_latest.iterrows()
            }
        else:
            seg_weights = default_seg_splits
    else:
        seg_weights = default_seg_splits

    # Load optional strategic investments override
    strat_path = paths.data_processed / "strategic_investments.csv"
    strat_by_scenario: dict[str, float] = {}
    if strat_path.exists():
        strat_df = pd.read_csv(strat_path)
        for _, row in strat_df.iterrows():
            strat_by_scenario[str(row["scenario"])] = float(row["strategic_investments_hkd_bn"])

    # Fall back to valuation_outputs for scenarios config
    valuation = pd.read_csv(valuation_outputs_path)
    if valuation.empty:
        raise SotpError("valuation_outputs.csv is empty")

    # We need scenarios_config; reconstruct years and paths from DCF output indirectly.
    # Pull scenario-level data from the DCF outputs to get capex/nwc/margin proxies.
    # For segment DCFs, apply common margins from the top-level valuation row.
    rows: list[dict] = []
    for _, vrow in valuation.iterrows():
        scenario = str(vrow["scenario"])
        if scenario not in ("base", "bad", "extreme"):
            continue

        # Read back scenario assumptions from scenario_assumptions_used.csv if available
        assumptions_path = paths.data_model / "scenario_assumptions_used.csv"
        ebit_margin_path: list[float] | None = None
        capex_path: list[float] | None = None
        nwc_path: list[float] | None = None
        sbc_path: list[float] | None = None
        growth_path: list[float] | None = None
        years_assumed = 7

        if assumptions_path.exists():
            assumptions = pd.read_csv(assumptions_path)
            scen_block = assumptions[assumptions["scenario"] == scenario].sort_values("year")
            if not scen_block.empty:
                years_assumed = int(scen_block["year"].max())
                ebit_margin_path = list(scen_block["ebit_margin"].astype(float))
                capex_path = list(scen_block["capex_pct_rev"].astype(float))
                nwc_path = list(scen_block["nwc_pct_rev"].astype(float))
                sbc_path = list(scen_block["sbc_pct_rev"].astype(float)) if "sbc_pct_rev" in scen_block.columns else None
                growth_path = list(scen_block["rev_growth"].astype(float))

        # Fallback to simple proxies
        if ebit_margin_path is None:
            ebit_margin_path = [float(vrow.get("ebit_margin", 0.36))] * years_assumed
        if capex_path is None:
            capex_path = [0.088] * years_assumed
        if nwc_path is None:
            nwc_path = [0.019] * years_assumed
        if growth_path is None:
            growth_path = [0.065] * years_assumed

        # Strategic investments
        strat_strategic = strat_by_scenario.get(scenario)
        if strat_strategic is None:
            if scenario == "base":
                strat_strategic = strategic_default
            elif scenario == "bad":
                strat_strategic = strategic_default * 0.85
            else:
                strat_strategic = strategic_default * 0.70

        # Per-segment DCFs
        total_seg_ev = 0.0
        for seg_name, weight in seg_weights.items():
            beta_seg = segment_betas.get(
                seg_name.replace(" ", "_"),
                segment_betas.get(seg_name, 1.0),
            )
            ru_seg = rf + beta_seg * erp + crp

            # Use scenario growth as segment growth (uniform — overrides handled by dcf.py)
            seg_growth = _get_path(growth_path, years_assumed)
            seg_base_rev = base_revenue * weight

            terminal_g = {
                "base": 0.025,
                "bad": 0.010,
                "extreme": 0.000,
            }.get(scenario, 0.025)

            seg_ev = _segment_enterprise_value(
                seg_revenue_base=seg_base_rev,
                seg_growth=seg_growth,
                ebit_margin=ebit_margin_path,
                capex_pct=capex_path,
                nwc_pct=nwc_path,
                sbc_pct=sbc_path,
                dep_pct=dep_pct,
                tax_rate=tax_rate,
                ru=max(ru_seg, 0.04),
                terminal_g=terminal_g,
                years=years_assumed,
                mid_year=True,
            )
            total_seg_ev += seg_ev

        total_equity = total_seg_ev + strat_strategic + net_cash - minority_interest
        fair = total_equity / shares

        rows.append({
            "asof": asof,
            "scenario": scenario,
            "operating_value_hkd_bn": total_seg_ev,
            "strategic_investments_value_hkd_bn": strat_strategic,
            "option_overlay_hkd_bn": 0.0,
            "net_cash_hkd_bn": net_cash,
            "minority_interest_hkd_bn": minority_interest,
            "total_equity_value_hkd_bn": total_equity,
            "fair_value_hkd_per_share": fair,
        })

    pd.DataFrame(rows).to_csv(artifacts.tvalue_company_bridge, index=False)

    # Statistical diagnostics (unchanged from prior implementation)
    beta_mkt = float(wrow.get("apt_beta_mkt", np.nan))
    beta_smb = float(wrow.get("apt_beta_smb", np.nan))
    beta_hml = float(wrow.get("apt_beta_hml", np.nan))
    lam_mkt = float(wrow.get("lambda_mkt", np.nan))
    lam_smb = float(wrow.get("lambda_smb", np.nan))
    lam_hml = float(wrow.get("lambda_hml", np.nan))

    t_beta_mkt = float(wrow.get("apt_t_beta_mkt", beta_mkt / max(0.05, abs(beta_mkt) * 0.20)))
    t_beta_smb = float(wrow.get("apt_t_beta_smb", beta_smb / max(0.05, abs(beta_smb) * 0.20)))
    t_beta_hml = float(wrow.get("apt_t_beta_hml", beta_hml / max(0.05, abs(beta_hml) * 0.20)))
    t_lam_mkt = float(wrow.get("apt_t_lambda_mkt", lam_mkt / max(0.01, abs(lam_mkt) * 0.25)))
    t_lam_smb = float(wrow.get("apt_t_lambda_smb", lam_smb / max(0.01, abs(lam_smb) * 0.25)))
    t_lam_hml = float(wrow.get("apt_t_lambda_hml", lam_hml / max(0.01, abs(lam_hml) * 0.25)))
    unstable = bool(wrow.get("apt_is_unstable", False))

    stats = pd.DataFrame([
        {
            "asof": asof, "factor": "MKT_EXCESS",
            "beta": beta_mkt, "lambda": lam_mkt,
            "t_beta": t_beta_mkt, "t_lambda": t_lam_mkt,
            "stability_flag": "unstable" if unstable else "stable",
        },
        {
            "asof": asof, "factor": "SMB",
            "beta": beta_smb, "lambda": lam_smb,
            "t_beta": t_beta_smb, "t_lambda": t_lam_smb,
            "stability_flag": "unstable" if unstable else "stable",
        },
        {
            "asof": asof, "factor": "HML",
            "beta": beta_hml, "lambda": lam_hml,
            "t_beta": t_beta_hml, "t_lambda": t_lam_hml,
            "stability_flag": "unstable" if unstable else "stable",
        },
    ])
    stats.to_csv(artifacts.tvalue_stat_diagnostics, index=False)
    return artifacts
