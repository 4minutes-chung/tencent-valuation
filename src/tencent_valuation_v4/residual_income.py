from __future__ import annotations

import warnings
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


def _get_path(values: list[float], years: int) -> list[float]:
    """Extend or truncate a parameter path to exactly `years` elements."""
    if not values:
        raise ResidualIncomeError("Scenario path must contain at least one value")
    if len(values) >= years:
        return [float(x) for x in values[:years]]
    last = float(values[-1])
    return [float(x) for x in values] + [last] * (years - len(values))


def run_residual_income(
    asof: str,
    paths: ProjectPaths,
    scenarios_config: dict,
    wacc_components_path: Path,
) -> ResidualIncomeArtifacts:
    """
    Edwards-Bell-Ohlson residual income model.

    Equity value = Book0 + PV(explicit residual incomes) + PV(terminal RI)

    Fixes vs. prior version:
    - Uses actual reported book_value_hkd_bn from tencent_financials.csv when available,
      falling back to proxy (0.42 * revenue) with a warning.
    - Removed the erroneous `equity += net_cash * 0.20` double-count (net cash is already
      included in the opening book value).
    - Retention ratios now read from scenarios_config if present; hardcoded fallback retained
      for backward compatibility.
    - Uses _get_path() for growth/margin arrays (consistent with dcf.py) to avoid IndexError
      when config arrays are shorter than forecast_years.
    """
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

    # Opening book value: prefer actual balance-sheet figure; proxy as fallback.
    # Net cash IS included in book value (as reported equity includes cash holdings).
    # Do NOT add net cash again later.
    if "book_value_hkd_bn" in base.index and not pd.isna(base["book_value_hkd_bn"]):
        book0 = float(base["book_value_hkd_bn"])
    else:
        warnings.warn(
            "book_value_hkd_bn not found in tencent_financials.csv — using proxy "
            "(0.42 * revenue + max(net_cash, 0)). Add book_value_hkd_bn to the "
            "override file for a more accurate residual income valuation.",
            stacklevel=2,
        )
        book0 = 0.42 * revenue0 + max(net_cash, 0.0)

    rows: list[dict[str, float | str]] = []
    for scenario in ["base", "bad", "extreme"]:
        cfg = scenarios_config["scenarios"][scenario]

        # Use _get_path to safely extend arrays to `years` length
        growth = _get_path([float(x) for x in cfg["revenue_growth"]], years)
        margin = _get_path([float(x) for x in cfg["ebit_margin"]], years)

        # Retention ratio: prefer config, fall back to sensible defaults
        # In worse scenarios firms typically retain more (lower dividends/buybacks)
        retention_defaults = {"base": 0.62, "bad": 0.66, "extreme": 0.70}
        if "retention_ratio" in cfg:
            retention = float(cfg["retention_ratio"])
        else:
            retention = retention_defaults[scenario]

        prev_rev = revenue0
        book = book0
        pv_ri = 0.0
        residual_last = 0.0

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

        # Equity = opening book + PV(residual incomes) + PV(terminal RI)
        # Net cash is NOT added separately — it is embedded in book0 per clean surplus.
        equity = book0 + pv_ri + pv_terminal_ri
        fair = equity / shares

        rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "method": "residual_income",
                "book_value_open_hkd_bn": round(book0, 4),
                "pv_residual_income_hkd_bn": round(pv_ri, 4),
                "pv_terminal_residual_income_hkd_bn": round(pv_terminal_ri, 4),
                "equity_value_hkd_bn": round(equity, 4),
                "fair_value_hkd_per_share": round(fair, 4),
            }
        )

    out = pd.DataFrame(rows)
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    out.to_csv(artifacts.residual_income_outputs, index=False)
    return artifacts
