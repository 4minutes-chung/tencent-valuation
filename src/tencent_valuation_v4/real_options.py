"""Phase 4D: Real Options Overlay (Black-Scholes on cloud/AI optionality).

Treats the option to fully develop Tencent's cloud/AI business as a
call option and computes its Black-Scholes value.

Config (in wacc.yaml under 'real_options'):
  cloud_ai_current_value_hkd_bn: 150.0
  investment_needed_hkd_bn: 80.0
  time_to_maturity_years: 7
  volatility: 0.40
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .paths import ProjectPaths


class RealOptionsError(RuntimeError):
    pass


@dataclass(frozen=True)
class RealOptionsArtifacts:
    real_options_outputs: Path


def _default_artifacts(paths: ProjectPaths) -> RealOptionsArtifacts:
    return RealOptionsArtifacts(
        real_options_outputs=paths.data_model / "real_options_outputs.csv"
    )


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_call(s: float, k: float, t: float, r: float, sigma: float) -> float:
    """European call option price (Black-Scholes).

    Parameters
    ----------
    s: current asset value (underlying)
    k: strike / investment needed
    t: time to maturity in years
    r: risk-free rate (continuously compounded)
    sigma: volatility of underlying
    """
    if t <= 0 or sigma <= 0 or s <= 0 or k <= 0:
        return max(0.0, s - k)
    sqrt_t = math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma**2) * t) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return s * _norm_cdf(d1) - k * math.exp(-r * t) * _norm_cdf(d2)


def run_real_options(
    asof: str,
    paths: ProjectPaths,
    wacc_components_path: Path,
    wacc_config: dict,
) -> RealOptionsArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    wacc_frame = pd.read_csv(wacc_components_path)
    if wacc_frame.empty:
        raise RealOptionsError("wacc_components.csv is empty")
    rf = float(wacc_frame.iloc[0].get("rf_annual", 0.04))

    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")
    if fin.empty:
        raise RealOptionsError("tencent_financials.csv is empty")
    shares_bn = float(fin.iloc[0]["shares_out_bn"])
    market_price = float(fin.iloc[0]["current_price_hkd"])

    ro_cfg = wacc_config.get("real_options", {})
    s = float(ro_cfg.get("cloud_ai_current_value_hkd_bn", 150.0))
    k = float(ro_cfg.get("investment_needed_hkd_bn", 80.0))
    t = float(ro_cfg.get("time_to_maturity_years", 7))
    sigma = float(ro_cfg.get("volatility", 0.40))

    option_value_hkd_bn = black_scholes_call(s=s, k=k, t=t, r=rf, sigma=sigma)
    option_value_per_share = option_value_hkd_bn / shares_bn if shares_bn > 0 else 0.0

    rows = []
    for scenario, dcf_premium in [("base", 1.0), ("bad", 0.5), ("extreme", 0.0)]:
        adj_option = option_value_hkd_bn * dcf_premium
        adj_per_share = option_value_per_share * dcf_premium
        rows.append({
            "asof": asof,
            "scenario": scenario,
            "underlying_value_hkd_bn": s,
            "strike_hkd_bn": k,
            "time_to_maturity_years": t,
            "volatility": sigma,
            "risk_free_rate": rf,
            "option_value_hkd_bn": adj_option,
            "option_value_hkd_per_share": adj_per_share,
            "market_price_hkd": market_price,
        })

    pd.DataFrame(rows).to_csv(artifacts.real_options_outputs, index=False)
    return artifacts
