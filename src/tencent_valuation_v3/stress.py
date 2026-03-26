"""Phase 6B: Named stress scenario valuations.

Runs a modified DCF for each named stress scenario defined in
scenarios.yaml under 'stress_scenarios'.  Each stress scenario can
override revenue_growth, ebit_margin, and/or add basis points to the
WACC.

Output: stress_scenario_outputs.csv with one row per scenario.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .dcf import _discount, _get_path, _project_fcff
from .paths import ProjectPaths


class StressError(RuntimeError):
    pass


@dataclass(frozen=True)
class StressArtifacts:
    stress_scenario_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> StressArtifacts:
    return StressArtifacts(
        stress_scenario_outputs=paths.data_model / "stress_scenario_outputs.csv"
    )


def _run_stress_scenario(
    name: str,
    stress_cfg: dict,
    base_cfg: dict,
    years: int,
    wacc_base: float,
    tax_rate: float,
    base_fin: pd.Series,
    mid_year: bool,
) -> dict:
    """Compute fair value for a single stress scenario."""
    wacc_adder = float(stress_cfg.get("wacc_adder_bps", 0)) / 10000.0
    wacc = wacc_base + wacc_adder

    revenue_growth = (
        [float(v) for v in stress_cfg["revenue_growth_override"]]
        if "revenue_growth_override" in stress_cfg
        else [float(v) for v in base_cfg["revenue_growth"]]
    )
    ebit_margin = (
        [float(v) for v in stress_cfg["ebit_margin_override"]]
        if "ebit_margin_override" in stress_cfg
        else [float(v) for v in base_cfg["ebit_margin"]]
    )
    capex_pct = [float(v) for v in base_cfg["capex_pct_revenue"]]
    nwc_pct = [float(v) for v in base_cfg["nwc_pct_revenue"]]
    sbc_pct: list[float] | None = (
        [float(v) for v in base_cfg["sbc_pct_revenue"]]
        if "sbc_pct_revenue" in base_cfg
        else None
    )
    terminal_g = min(float(base_cfg["terminal_g"]), wacc - 0.002)

    fcff_df = _project_fcff(
        base_revenue_hkd_bn=float(base_fin["revenue_hkd_bn"]),
        dep_pct_revenue=float(base_fin["dep_pct_revenue"]),
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
    equity = ev + float(base_fin["net_cash_hkd_bn"])
    shares = float(base_fin["shares_out_bn"])
    fair_value = equity / shares
    market_price = float(base_fin["current_price_hkd"])

    return {
        "stress_scenario": name,
        "description": str(stress_cfg.get("description", "")),
        "probability": float(stress_cfg.get("probability", 0.0)),
        "wacc": wacc,
        "wacc_adder_bps": float(stress_cfg.get("wacc_adder_bps", 0)),
        "enterprise_value_hkd_bn": ev,
        "equity_value_hkd_bn": equity,
        "fair_value_hkd_per_share": fair_value,
        "market_price_hkd": market_price,
        "margin_of_safety": (fair_value - market_price) / market_price,
    }


def run_stress_scenarios(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> StressArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    financials = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if financials.empty:
        raise StressError("tencent_financials.csv is empty")
    base_fin = financials.iloc[0]

    wacc_frame = pd.read_csv(wacc_components_path)
    if wacc_frame.empty:
        raise StressError("wacc_components.csv is empty")
    wacc_base = float(wacc_frame.iloc[0]["wacc"])
    tax_rate = float(wacc_frame.iloc[0]["tax_rate_tencent"])

    years = int(scenarios_config["forecast_years"])
    mid_year = bool(scenarios_config.get("mid_year_discounting", False))
    base_cfg = scenarios_config["scenarios"]["base"]
    stress_defs = scenarios_config.get("stress_scenarios", {})

    rows = []
    for name, stress_cfg in stress_defs.items():
        result = _run_stress_scenario(
            name=name,
            stress_cfg=stress_cfg,
            base_cfg=base_cfg,
            years=years,
            wacc_base=wacc_base,
            tax_rate=tax_rate,
            base_fin=base_fin,
            mid_year=mid_year,
        )
        result["asof"] = asof
        rows.append(result)

    if rows:
        pd.DataFrame(rows).to_csv(artifacts.stress_scenario_outputs, index=False)
    else:
        # Write empty CSV with headers for schema consistency
        empty_df = pd.DataFrame(columns=[
            "asof", "stress_scenario", "description", "probability", "wacc",
            "wacc_adder_bps", "enterprise_value_hkd_bn", "equity_value_hkd_bn",
            "fair_value_hkd_per_share", "market_price_hkd", "margin_of_safety",
        ])
        empty_df.to_csv(artifacts.stress_scenario_outputs, index=False)
    return artifacts
