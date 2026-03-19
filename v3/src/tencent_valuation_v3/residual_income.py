from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import ProjectPaths


class ResidualIncomeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResidualIncomeArtifacts:
    residual_income_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> ResidualIncomeArtifacts:
    return ResidualIncomeArtifacts(residual_income_outputs=paths.data_model / "residual_income_outputs.csv")


def _discount(value: float, rate: float, year: int) -> float:
    return float(value / ((1.0 + rate) ** year))


def run_residual_income(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> ResidualIncomeArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if fin.empty:
        raise ResidualIncomeError("tencent_financials.csv is empty")
    base = fin.iloc[0]

    wacc = pd.read_csv(wacc_components_path)
    if wacc.empty:
        raise ResidualIncomeError("wacc_components.csv is empty")
    wrow = wacc.iloc[0]

    years = int(scenarios_config.get("forecast_years", 7))
    re = float(wrow["re_capm"])
    tax_rate = float(wrow["tax_rate_tencent"])

    revenue0 = float(base["revenue_hkd_bn"])
    shares = float(base["shares_out_bn"])
    net_cash = float(base["net_cash_hkd_bn"])

    # Proxy opening book value from current scale; can be overridden in future via filing field.
    book0 = 0.42 * revenue0 + max(net_cash, 0.0)

    rows: list[dict[str, float | str]] = []
    for scenario in ["base", "bad", "extreme"]:
        cfg = scenarios_config["scenarios"][scenario]
        growth = [float(x) for x in cfg["revenue_growth"]][:years]
        margin = [float(x) for x in cfg["ebit_margin"]][:years]

        prev_rev = revenue0
        book = book0
        pv_ri = 0.0
        residual_last = 0.0
        retention = 0.62 if scenario == "base" else (0.66 if scenario == "bad" else 0.70)

        for year in range(1, years + 1):
            rev = prev_rev * (1.0 + growth[year - 1])
            earnings = rev * margin[year - 1] * (1.0 - tax_rate)
            residual = earnings - re * book
            pv_ri += _discount(residual, re, year)

            retained = earnings * retention
            book = max(1e-6, book + retained)
            prev_rev = rev
            residual_last = residual

        g = float(cfg["terminal_g"])
        g = min(g, re - 0.002)
        terminal_ri = residual_last * (1.0 + g) / max(1e-6, re - g)
        pv_terminal_ri = _discount(terminal_ri, re, years)

        equity = book0 + pv_ri + pv_terminal_ri
        equity += net_cash * 0.20
        fair = equity / shares

        rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "method": "residual_income",
                "book_value_open_hkd_bn": book0,
                "pv_residual_income_hkd_bn": pv_ri,
                "pv_terminal_residual_income_hkd_bn": pv_terminal_ri,
                "equity_value_hkd_bn": equity,
                "fair_value_hkd_per_share": fair,
            }
        )

    out = pd.DataFrame(rows)
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    out.to_csv(artifacts.residual_income_outputs, index=False)
    return artifacts
