from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .paths import ProjectPaths


class ApvError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApvArtifacts:
    apv_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> ApvArtifacts:
    return ApvArtifacts(apv_outputs=paths.data_model / "apv_outputs.csv")


def run_apv(asof: str, paths: ProjectPaths, valuation_path: Path, wacc_components_path: Path) -> ApvArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    valuation = pd.read_csv(valuation_path)
    if valuation.empty:
        raise ApvError("valuation_outputs.csv is empty")

    wacc = pd.read_csv(wacc_components_path)
    if wacc.empty:
        raise ApvError("wacc_components.csv is empty")
    wrow = wacc.iloc[0]

    market_inputs = pd.read_csv(paths.data_processed / "market_inputs.csv")
    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if fin.empty:
        raise ApvError("tencent_financials.csv is empty")

    target_ticker = str(wrow.get("target_ticker", "0700.HK"))
    if "ticker" in market_inputs.columns and target_ticker in set(market_inputs["ticker"]):
        debt = float(market_inputs.loc[market_inputs["ticker"] == target_ticker, "gross_debt_hkd_bn"].iloc[0])
    else:
        debt = float(market_inputs.loc[market_inputs["ticker"] == "0700.HK", "gross_debt_hkd_bn"].iloc[0])

    tax_rate = float(wrow["tax_rate_tencent"])
    net_cash = float(fin.iloc[0]["net_cash_hkd_bn"])
    shares = float(fin.iloc[0]["shares_out_bn"])

    financing_side_effect_map = {
        "base": 0.00,
        "bad": -0.01,
        "extreme": -0.03,
    }

    rows: list[dict[str, float | str]] = []
    for _, row in valuation.iterrows():
        scenario = str(row["scenario"])
        enterprise = float(row["enterprise_value_hkd_bn"])

        pv_tax_shield = debt * tax_rate
        financing_side_effect = financing_side_effect_map.get(scenario, -0.01) * debt

        unlevered_value = enterprise - pv_tax_shield
        apv_enterprise = unlevered_value + pv_tax_shield + financing_side_effect
        equity = apv_enterprise + net_cash
        fair = equity / shares

        rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "method": "apv",
                "unlevered_value_hkd_bn": unlevered_value,
                "pv_tax_shield_hkd_bn": pv_tax_shield,
                "financing_side_effect_hkd_bn": financing_side_effect,
                "enterprise_value_hkd_bn": apv_enterprise,
                "equity_value_hkd_bn": equity,
                "fair_value_hkd_per_share": fair,
            }
        )

    pd.DataFrame(rows).to_csv(artifacts.apv_outputs, index=False)
    return artifacts
