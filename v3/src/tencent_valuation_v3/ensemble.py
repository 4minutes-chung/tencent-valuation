from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import ProjectPaths


class EnsembleError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnsembleArtifacts:
    valuation_method_outputs: Path
    valuation_ensemble: Path


def _default_artifacts(paths: ProjectPaths) -> EnsembleArtifacts:
    return EnsembleArtifacts(
        valuation_method_outputs=paths.data_model / "valuation_method_outputs.csv",
        valuation_ensemble=paths.data_model / "valuation_ensemble.csv",
    )


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = float(sum(max(0.0, float(v)) for v in weights.values()))
    if total <= 0:
        n = max(1, len(weights))
        return {k: 1.0 / n for k in weights}
    return {k: max(0.0, float(v)) / total for k, v in weights.items()}


def run_ensemble(
    asof: str,
    paths: ProjectPaths,
    method_weights_config: dict,
    qa_report_path: Path,
    wacc_components_path: Path,
) -> EnsembleArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    dcf = pd.read_csv(paths.data_model / "valuation_outputs.csv")
    apv = pd.read_csv(paths.data_model / "apv_outputs.csv")
    residual = pd.read_csv(paths.data_model / "residual_income_outputs.csv")
    relative = pd.read_csv(paths.data_model / "relative_valuation_outputs.csv")
    tvalue = pd.read_csv(paths.data_model / "tvalue_company_bridge.csv")

    if dcf.empty or apv.empty or residual.empty or relative.empty or tvalue.empty:
        raise EnsembleError("One or more method output files are missing/empty")

    base_weights = method_weights_config.get("method_weights", {})
    weights = {
        "dcf": float(base_weights.get("dcf", 0.35)),
        "apv": float(base_weights.get("apv", 0.20)),
        "residual_income": float(base_weights.get("residual_income", 0.15)),
        "relative": float(base_weights.get("relative", 0.15)),
        "sotp_tvalue": float(base_weights.get("sotp_tvalue", 0.15)),
    }

    qa = None
    if qa_report_path.exists():
        qa = pd.read_json(qa_report_path, typ="series")

    wacc = pd.read_csv(wacc_components_path)
    apt_unstable = bool(wacc.iloc[0].get("apt_is_unstable", False)) if not wacc.empty else False

    overrides = method_weights_config.get("weight_overrides", {})
    if apt_unstable:
        penalty = float(overrides.get("apt_unstable_penalty", 0.90))
        weights["relative"] *= penalty
        weights["sotp_tvalue"] *= penalty

    if qa is not None:
        summary = qa.get("summary", {})
        failures = int(summary.get("failures", 0)) if isinstance(summary, dict) else 0
        if failures > 0:
            penalty = float(overrides.get("backtest_quality_penalty", 0.85))
            weights["residual_income"] *= penalty
            weights["relative"] *= penalty

    weights = _normalize_weights(weights)

    method_rows: list[dict[str, float | str]] = []

    scenarios = ["base", "bad", "extreme"]
    for scenario in scenarios:
        dcf_row = dcf.loc[dcf["scenario"] == scenario]
        apv_row = apv.loc[apv["scenario"] == scenario]
        ri_row = residual.loc[residual["scenario"] == scenario]
        tv_row = tvalue.loc[tvalue["scenario"] == scenario]

        if dcf_row.empty or apv_row.empty or ri_row.empty or tv_row.empty:
            continue

        rel_row = relative.iloc[0]
        rel_fair = float(rel_row["fair_value_hkd_per_share"])

        entries = [
            ("dcf", dcf_row.iloc[0]),
            ("apv", apv_row.iloc[0]),
            ("residual_income", ri_row.iloc[0]),
            ("relative", rel_row),
            ("sotp_tvalue", tv_row.iloc[0]),
        ]

        for method, row in entries:
            fair = float(row["fair_value_hkd_per_share"])
            equity = float(row.get("equity_value_hkd_bn", np.nan))
            if method == "relative":
                fair = rel_fair
            method_rows.append(
                {
                    "asof": asof,
                    "scenario": scenario,
                    "method": method,
                    "fair_value_hkd_per_share": fair,
                    "equity_value_hkd_bn": equity,
                    "weight": float(weights.get(method, 0.0)),
                }
            )

    method_df = pd.DataFrame(method_rows)
    if method_df.empty:
        raise EnsembleError("No method rows generated")
    method_df.to_csv(artifacts.valuation_method_outputs, index=False)

    ens_rows: list[dict[str, float | str]] = []
    for scenario in sorted(method_df["scenario"].unique()):
        block = method_df.loc[method_df["scenario"] == scenario].copy()
        if block.empty:
            continue
        w = block["weight"].astype(float)
        x = block["fair_value_hkd_per_share"].astype(float)
        weighted = float(np.sum(w * x))
        lo = float(x.min())
        hi = float(x.max())
        width = hi - lo
        width_ratio = width / max(1e-6, weighted)

        ens_rows.append(
            {
                "asof": asof,
                "scenario": scenario,
                "ensemble_fair_value_hkd_per_share": weighted,
                "method_min_hkd_per_share": lo,
                "method_max_hkd_per_share": hi,
                "band_width_hkd_per_share": width,
                "band_width_ratio": width_ratio,
            }
        )

    pd.DataFrame(ens_rows).to_csv(artifacts.valuation_ensemble, index=False)
    return artifacts
