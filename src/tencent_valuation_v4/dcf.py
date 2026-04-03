from __future__ import annotations

import warnings
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



def _blend_segment_growth(
    segment_df: pd.DataFrame,
    overrides: dict[str, list[float]],
    years: int,
) -> list[float]:
    """Compute revenue-share-weighted blended growth path from per-segment overrides.

    Each key in *overrides* must match a 'segment' value in *segment_df*.
    Weights are derived from the most recent period's revenue shares.
    Segments not present in *overrides* contribute zero weight; the result
    is re-normalised so the weights sum to 1.
    """
    latest_period = segment_df["period"].max()
    seg_data = segment_df[segment_df["period"] == latest_period].copy()

    total_rev = seg_data["revenue_hkd_bn"].sum()
    if total_rev <= 0:
        raise DcfError("segment_revenue.csv has zero total revenue for latest period")

    weights: dict[str, float] = {
        row["segment"]: row["revenue_hkd_bn"] / total_rev
        for _, row in seg_data.iterrows()
    }

    blended = [0.0] * years
    total_weight = 0.0
    for seg_name, growth_path in overrides.items():
        w = weights.get(seg_name, 0.0)
        path = _get_path([float(v) for v in growth_path], years)
        for i in range(years):
            blended[i] += w * path[i]
        total_weight += w

    if total_weight < 1e-6:
        raise DcfError(
            f"segment_growth_overrides contains no recognised segments. "
            f"Known: {list(weights.keys())}"
        )

    # Normalise in case only a subset of segments are overridden
    if abs(total_weight - 1.0) > 0.01:
        blended = [g / total_weight for g in blended]

    return blended


def _project_fcff(
    base_revenue_hkd_bn: float,
    dep_pct_revenue: float,
    tax_rate: float,
    years: int,
    revenue_growth: list[float],
    ebit_margin: list[float],
    capex_pct_revenue: list[float],
    nwc_pct_revenue: list[float],
    sbc_pct_revenue: list[float] | None = None,
) -> pd.DataFrame:
    growth = _get_path(revenue_growth, years)
    margin = _get_path(ebit_margin, years)
    capex = _get_path(capex_pct_revenue, years)
    nwc = _get_path(nwc_pct_revenue, years)
    sbc = _get_path(sbc_pct_revenue, years) if sbc_pct_revenue else [0.0] * years

    rows: list[dict[str, float | int]] = []
    prev_revenue = float(base_revenue_hkd_bn)
    for year in range(1, years + 1):
        rev = prev_revenue * (1.0 + growth[year - 1])
        ebit = rev * margin[year - 1]
        nopat = ebit * (1.0 - tax_rate)
        dep = rev * dep_pct_revenue
        capex_amt = rev * capex[year - 1]
        delta_nwc = (rev - prev_revenue) * nwc[year - 1]
        sbc_amt = rev * sbc[year - 1]
        fcff = nopat + dep - capex_amt - delta_nwc - sbc_amt

        rows.append(
            {
                "year": year,
                "revenue_hkd_bn": rev,
                "ebit_hkd_bn": ebit,
                "sbc_hkd_bn": sbc_amt,
                "fcff_hkd_bn": fcff,
            }
        )
        prev_revenue = rev

    return pd.DataFrame(rows)



def _discount(value: float, rate: float, year: float | int) -> float:
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
    mid_year: bool = False,
    check_roic: bool = True,
) -> dict[str, float | str]:
    revenue_growth = [float(v) + growth_shift for v in scenario_cfg["revenue_growth"]]
    ebit_margin = [float(v) + margin_shift for v in scenario_cfg["ebit_margin"]]
    capex_path = [float(v) for v in scenario_cfg["capex_pct_revenue"]]
    nwc_path = [float(v) for v in scenario_cfg["nwc_pct_revenue"]]
    sbc_path: list[float] | None = (
        [float(v) for v in scenario_cfg["sbc_pct_revenue"]]
        if "sbc_pct_revenue" in scenario_cfg
        else None
    )

    fcff = _project_fcff(
        base_revenue_hkd_bn=float(base_fin["revenue_hkd_bn"]),
        dep_pct_revenue=float(base_fin["dep_pct_revenue"]),
        tax_rate=tax_rate,
        years=years,
        revenue_growth=revenue_growth,
        ebit_margin=ebit_margin,
        capex_pct_revenue=capex_path,
        nwc_pct_revenue=nwc_path,
        sbc_pct_revenue=sbc_path,
    )

    terminal_g = float(scenario_cfg["terminal_g"]) + terminal_shift
    wacc_eff = float(wacc)
    max_terminal = wacc_eff - 0.002
    if terminal_g >= max_terminal:
        terminal_g = max_terminal

    pv_fcff = 0.0
    for _, row in fcff.iterrows():
        yr: float = int(row["year"]) - 0.5 if mid_year else float(row["year"])
        pv_fcff += _discount(float(row["fcff_hkd_bn"]), wacc_eff, yr)

    final_fcff = float(fcff.iloc[-1]["fcff_hkd_bn"])
    tv_method = str(scenario_cfg.get("terminal_value_method", "gordon_growth")).lower()
    if tv_method == "h_model":
        # H-model: gradual fade from near-term growth g_S to stable g_L over 2H years
        # TV = FCFF_n * (1 + g_L + H * (g_S - g_L)) / (r - g_L)
        g_short = float(scenario_cfg.get("h_model_g_short", revenue_growth[-1]))
        h_years = float(scenario_cfg.get("h_model_half_life", 5.0))
        H = h_years / 2.0
        terminal_value = final_fcff * (1.0 + terminal_g + H * (g_short - terminal_g)) / (wacc_eff - terminal_g)
    else:
        # Gordon Growth (default)
        terminal_value = final_fcff * (1.0 + terminal_g) / (wacc_eff - terminal_g)
    pv_terminal = _discount(terminal_value, wacc_eff, years)

    # Terminal ROIC sanity check (3C)
    # Implied ROIC = terminal_g / reinvestment_rate
    # reinvestment_rate = 1 - terminal_FCFF / terminal_NOPLAT
    # terminal_NOPLAT = final_year_EBIT * (1 - tax) * (1 + terminal_g)
    final_ebit = float(fcff.iloc[-1]["ebit_hkd_bn"])
    terminal_noplat = final_ebit * (1.0 - tax_rate) * (1.0 + terminal_g)
    terminal_fcff_numer = final_fcff * (1.0 + terminal_g)
    if terminal_noplat > 1e-6:
        reinv_rate = max(0.0, 1.0 - terminal_fcff_numer / terminal_noplat)
        implied_roic = terminal_g / reinv_rate if reinv_rate > 1e-6 else float("inf")
    else:
        implied_roic = float("inf")
    terminal_roic_flag = bool(np.isfinite(implied_roic) and implied_roic > 3.0 * wacc_eff and terminal_g > 0)
    if terminal_roic_flag and check_roic:
        warnings.warn(
            f"[DCF/{scenario_name}] Implied terminal ROIC {implied_roic:.1%} > 3×WACC "
            f"({3.0 * wacc_eff:.1%}). Consider lowering terminal_g or margins.",
            UserWarning,
            stacklevel=3,
        )

    enterprise_hkd_bn = pv_fcff + pv_terminal
    market_price = float(base_fin["current_price_hkd"])

    # Share buyback adjustment (3F)
    # Buybacks retire shares and consume net cash over the forecast period.
    annual_buyback = float(scenario_cfg.get("annual_buyback_hkd_bn", 0.0))
    total_buyback = annual_buyback * years
    net_cash_adj = float(base_fin["net_cash_hkd_bn"]) - total_buyback
    retired_shares_bn = total_buyback / market_price if market_price > 0 else 0.0
    final_shares_bn = max(float(base_fin["shares_out_bn"]) - retired_shares_bn, 1e-6)

    equity_hkd_bn = enterprise_hkd_bn + net_cash_adj
    fair_value = equity_hkd_bn / final_shares_bn
    mos = (fair_value - market_price) / market_price

    return {
        "scenario": scenario_name,
        "enterprise_value_hkd_bn": enterprise_hkd_bn,
        "equity_value_hkd_bn": equity_hkd_bn,
        "fair_value_hkd_per_share": fair_value,
        "market_price_hkd": market_price,
        "margin_of_safety": mos,
        "total_buyback_hkd_bn": total_buyback,
        "shares_retired_bn": retired_shares_bn,
        "terminal_roic_implied": implied_roic if np.isfinite(implied_roic) else None,
        "terminal_roic_flag": terminal_roic_flag,
        "terminal_value_method": tv_method,
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

    seg_path = paths.data_processed / "segment_revenue.csv"
    segment_df: pd.DataFrame | None = pd.read_csv(seg_path) if seg_path.exists() else None

    wacc_frame = pd.read_csv(wacc_components_path)
    if wacc_frame.empty:
        raise DcfError("wacc_components.csv is empty")

    row = wacc_frame.iloc[0]
    wacc = float(row["wacc"])
    tax_rate = float(row["tax_rate_tencent"])

    years = int(scenarios_config["forecast_years"])
    mid_year = bool(scenarios_config.get("mid_year_discounting", False))
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
        if "segment_growth_overrides" in cfg and segment_df is not None:
            blended = _blend_segment_growth(segment_df, cfg["segment_growth_overrides"], years)
            cfg = {**cfg, "revenue_growth": blended}
        val = _scenario_value(name, cfg, years, wacc, tax_rate, base_fin, mid_year=mid_year)
        val["asof"] = asof
        val["wacc"] = wacc
        out_rows.append(val)

        growth = _get_path([float(v) for v in cfg["revenue_growth"]], years)
        margin = _get_path([float(v) for v in cfg["ebit_margin"]], years)
        capex = _get_path([float(v) for v in cfg["capex_pct_revenue"]], years)
        nwc = _get_path([float(v) for v in cfg["nwc_pct_revenue"]], years)
        sbc_assumption = _get_path([float(v) for v in cfg["sbc_pct_revenue"]], years) if "sbc_pct_revenue" in cfg else [0.0] * years
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
                    "sbc_pct_rev": sbc_assumption[year - 1],
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
                mid_year=mid_year,
                check_roic=False,
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
                mid_year=mid_year,
                check_roic=False,
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
