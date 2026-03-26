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

    # Optional new-method outputs (graceful degradation if not present)
    eva_path = paths.data_model / "eva_outputs.csv"
    mc_pct_path = paths.data_model / "monte_carlo_percentiles.csv"
    ro_path = paths.data_model / "real_options_outputs.csv"
    eva_df = pd.read_csv(eva_path) if eva_path.exists() else pd.DataFrame()
    mc_pct_df = pd.read_csv(mc_pct_path) if mc_pct_path.exists() else pd.DataFrame()
    ro_df = pd.read_csv(ro_path) if ro_path.exists() else pd.DataFrame()

    base_weights = method_weights_config.get("method_weights", {})
    weights: dict[str, float] = {
        "dcf": float(base_weights.get("dcf", 0.25)),
        "apv": float(base_weights.get("apv", 0.15)),
        "residual_income": float(base_weights.get("residual_income", 0.10)),
        "relative": float(base_weights.get("relative", 0.10)),
        "sotp_tvalue": float(base_weights.get("sotp_tvalue", 0.15)),
    }
    if not eva_df.empty:
        weights["eva"] = float(base_weights.get("eva", 0.10))
    if not mc_pct_df.empty:
        weights["monte_carlo"] = float(base_weights.get("monte_carlo", 0.10))
    if not ro_df.empty:
        weights["real_options"] = float(base_weights.get("real_options", 0.05))

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

    # MC p50 per scenario (MC is scenario-agnostic; apply to all three)
    mc_p50: float | None = None
    if not mc_pct_df.empty:
        p50_row = mc_pct_df[mc_pct_df["percentile"] == 50]
        if not p50_row.empty:
            mc_p50 = float(p50_row.iloc[0]["fair_value_hkd_per_share"])

    scenarios = ["base", "bad", "extreme"]
    for scenario in scenarios:
        dcf_row = dcf.loc[dcf["scenario"] == scenario]
        apv_row = apv.loc[apv["scenario"] == scenario]
        ri_row = residual.loc[residual["scenario"] == scenario]
        tv_row = tvalue.loc[tvalue["scenario"] == scenario]

        if dcf_row.empty or apv_row.empty or ri_row.empty or tv_row.empty:
            continue

        rel_filtered = relative.loc[relative["scenario"] == scenario]
        rel_row = rel_filtered.iloc[0] if not rel_filtered.empty else relative.iloc[0]
        rel_fair = float(rel_row["fair_value_hkd_per_share"])

        entries: list[tuple[str, object]] = [
            ("dcf", dcf_row.iloc[0]),
            ("apv", apv_row.iloc[0]),
            ("residual_income", ri_row.iloc[0]),
            ("relative", rel_row),
            ("sotp_tvalue", tv_row.iloc[0]),
        ]

        if not eva_df.empty:
            eva_row = eva_df.loc[eva_df["scenario"] == scenario]
            if not eva_row.empty:
                entries.append(("eva", eva_row.iloc[0]))

        if mc_p50 is not None:
            # MC is distribution-level; use p50 as point estimate regardless of scenario
            entries.append(("monte_carlo", {"fair_value_hkd_per_share": mc_p50, "equity_value_hkd_bn": np.nan}))

        if not ro_df.empty:
            ro_row = ro_df.loc[ro_df["scenario"] == scenario]
            if not ro_row.empty:
                dcf_fair = float(dcf_row.iloc[0]["fair_value_hkd_per_share"])
                ro_adj_fair = dcf_fair + float(ro_row.iloc[0]["option_value_hkd_per_share"])
                entries.append(("real_options", {"fair_value_hkd_per_share": ro_adj_fair, "equity_value_hkd_bn": np.nan}))

        for method, row in entries:
            if isinstance(row, dict):
                fair = float(row["fair_value_hkd_per_share"])
                equity = float(row.get("equity_value_hkd_bn", np.nan))
            else:
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

    # Scenario probabilities for expected-value row
    scenario_probs: dict[str, float] = {}
    raw_probs = method_weights_config.get("scenario_probabilities", {})
    if raw_probs:
        total_p = sum(float(v) for v in raw_probs.values())
        if total_p > 0:
            scenario_probs = {k: float(v) / total_p for k, v in raw_probs.items()}

    ens_rows: list[dict[str, float | str]] = []
    scenario_ensemble_fvs: dict[str, float] = {}

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
        scenario_ensemble_fvs[scenario] = weighted

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

    # Probability-weighted expected value row
    if scenario_probs and scenario_ensemble_fvs:
        expected_fv = sum(
            scenario_probs.get(s, 0.0) * fv
            for s, fv in scenario_ensemble_fvs.items()
        )
        ens_rows.append(
            {
                "asof": asof,
                "scenario": "expected",
                "ensemble_fair_value_hkd_per_share": expected_fv,
                "method_min_hkd_per_share": min(scenario_ensemble_fvs.values()),
                "method_max_hkd_per_share": max(scenario_ensemble_fvs.values()),
                "band_width_hkd_per_share": max(scenario_ensemble_fvs.values()) - min(scenario_ensemble_fvs.values()),
                "band_width_ratio": (
                    (max(scenario_ensemble_fvs.values()) - min(scenario_ensemble_fvs.values()))
                    / max(1e-6, expected_fv)
                ),
            }
        )

    pd.DataFrame(ens_rows).to_csv(artifacts.valuation_ensemble, index=False)
    return artifacts
