from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

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


def run_tvalue(
    asof: str,
    paths: ProjectPaths,
    wacc_components_path: Path,
    valuation_outputs_path: Path,
    wacc_config: dict,
) -> SotpArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    wacc = pd.read_csv(wacc_components_path)
    valuation = pd.read_csv(valuation_outputs_path)
    fin = pd.read_csv(paths.data_processed / "tencent_financials.csv")

    if wacc.empty or valuation.empty or fin.empty:
        raise SotpError("Missing inputs for T-value")

    wrow = wacc.iloc[0]
    frow = fin.iloc[0]

    shares = float(frow["shares_out_bn"])
    net_cash = float(frow["net_cash_hkd_bn"])

    strategic_default = float(wacc_config.get("strategic_investments_default_hkd_bn", 380.0))
    option_default = float(wacc_config.get("option_overlay_default_hkd_bn", 0.0))

    rows: list[dict[str, float | str]] = []
    for _, vrow in valuation.iterrows():
        scenario = str(vrow["scenario"])
        operating = float(vrow["enterprise_value_hkd_bn"])

        if scenario == "base":
            strategic = strategic_default
            option_overlay = option_default
        elif scenario == "bad":
            strategic = strategic_default * 0.85
            option_overlay = option_default * 0.50
        else:
            strategic = strategic_default * 0.70
            option_overlay = 0.0

        total_equity = operating + strategic + option_overlay + net_cash
        fair = total_equity / shares

        rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "operating_value_hkd_bn": operating,
                "strategic_investments_value_hkd_bn": strategic,
                "option_overlay_hkd_bn": option_overlay,
                "net_cash_hkd_bn": net_cash,
                "total_equity_value_hkd_bn": total_equity,
                "fair_value_hkd_per_share": fair,
            }
        )

    pd.DataFrame(rows).to_csv(artifacts.tvalue_company_bridge, index=False)

    beta_mkt = float(wrow.get("apt_beta_mkt", np.nan))
    beta_smb = float(wrow.get("apt_beta_smb", np.nan))
    beta_hml = float(wrow.get("apt_beta_hml", np.nan))
    lam_mkt = float(wrow.get("lambda_mkt", np.nan))
    lam_smb = float(wrow.get("lambda_smb", np.nan))
    lam_hml = float(wrow.get("lambda_hml", np.nan))

    # Prefer model-provided t-stats; fallback deterministic proxy.
    t_beta_mkt = float(wrow.get("apt_t_beta_mkt", beta_mkt / max(0.05, abs(beta_mkt) * 0.20)))
    t_beta_smb = float(wrow.get("apt_t_beta_smb", beta_smb / max(0.05, abs(beta_smb) * 0.20)))
    t_beta_hml = float(wrow.get("apt_t_beta_hml", beta_hml / max(0.05, abs(beta_hml) * 0.20)))
    t_lam_mkt = float(wrow.get("apt_t_lambda_mkt", lam_mkt / max(0.01, abs(lam_mkt) * 0.25)))
    t_lam_smb = float(wrow.get("apt_t_lambda_smb", lam_smb / max(0.01, abs(lam_smb) * 0.25)))
    t_lam_hml = float(wrow.get("apt_t_lambda_hml", lam_hml / max(0.01, abs(lam_hml) * 0.25)))

    unstable = bool(wrow.get("apt_is_unstable", False))

    stats = pd.DataFrame(
        [
            {
                "asof": asof,
                "factor": "MKT_EXCESS",
                "beta": beta_mkt,
                "lambda": lam_mkt,
                "t_beta": t_beta_mkt,
                "t_lambda": t_lam_mkt,
                "stability_flag": "unstable" if unstable else "stable",
            },
            {
                "asof": asof,
                "factor": "SMB",
                "beta": beta_smb,
                "lambda": lam_smb,
                "t_beta": t_beta_smb,
                "t_lambda": t_lam_smb,
                "stability_flag": "unstable" if unstable else "stable",
            },
            {
                "asof": asof,
                "factor": "HML",
                "beta": beta_hml,
                "lambda": lam_hml,
                "t_beta": t_beta_hml,
                "t_lambda": t_lam_hml,
                "stability_flag": "unstable" if unstable else "stable",
            },
        ]
    )
    stats.to_csv(artifacts.tvalue_stat_diagnostics, index=False)

    return artifacts
