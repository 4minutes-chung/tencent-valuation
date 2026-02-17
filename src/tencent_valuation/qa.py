from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .paths import ProjectPaths


@dataclass(frozen=True)
class QaArtifacts:
    qa_report_json: Path



def _default_artifacts(paths: ProjectPaths, asof: str) -> QaArtifacts:
    return QaArtifacts(qa_report_json=paths.reports / f"qa_{asof}.json")



def _status_from_bool(ok: bool, fail_on_false: bool = False) -> str:
    if ok:
        return "pass"
    return "fail" if fail_on_false else "warn"



def run_qa(
    asof: str,
    paths: ProjectPaths,
    wacc_config: dict,
    qa_gates: dict,
    peers: list[str],
    scenarios_config: dict,
) -> QaArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths, asof)

    checks: list[dict[str, Any]] = []
    check_status: dict[str, str] = {}

    segment_path = paths.data_processed / "segment_revenue.csv"
    if segment_path.exists():
        seg = pd.read_csv(segment_path)
        grouped = seg.groupby("period", as_index=False).agg(
            segment_sum=("revenue_hkd_bn", "sum"), total=("total_revenue_hkd_bn", "first")
        )
        max_diff = float((grouped["segment_sum"] - grouped["total"]).abs().max()) if not grouped.empty else 0.0
        status = "pass" if max_diff < 1e-6 else "warn"
        checks.append(
            {
                "check": "segment_sum_to_total",
                "status": status,
                "metric": max_diff,
                "message": "Segment revenues reconcile to total revenue.",
            }
        )
        check_status["segment_sum_to_total"] = status
    else:
        checks.append(
            {
                "check": "segment_sum_to_total",
                "status": "warn",
                "metric": None,
                "message": "segment_revenue.csv missing.",
            }
        )
        check_status["segment_sum_to_total"] = "warn"

    wacc_path = paths.data_model / "wacc_components.csv"
    if wacc_path.exists():
        wacc = pd.read_csv(wacc_path).iloc[0]
        gap_bps = float(wacc["capm_apt_gap_bps"])
        limit = float(wacc_config.get("capm_apt_alert_bps", 150))
        gap_status = "pass" if gap_bps <= limit else "warn"
        checks.append(
            {
                "check": "capm_apt_gap",
                "status": gap_status,
                "metric": gap_bps,
                "message": f"CAPM/APT gap {gap_bps:.1f} bps; threshold {limit:.1f} bps.",
            }
        )
        check_status["capm_apt_gap"] = gap_status

        unstable = bool(wacc.get("apt_is_unstable", False))
        unstable_limit = float(wacc_config.get("apt_unstable_gap_bps", 400.0))
        unstable_status = "warn" if unstable else "pass"
        checks.append(
            {
                "check": "apt_stability_gate",
                "status": unstable_status,
                "metric": {
                    "apt_is_unstable": unstable,
                    "gap_bps": gap_bps,
                    "unstable_threshold_bps": unstable_limit,
                },
                "message": (
                    "APT diagnostic marked unstable and excluded from headline valuation."
                    if unstable
                    else "APT diagnostic is within stability gate."
                ),
            }
        )
        check_status["apt_stability_gate"] = unstable_status

        d_e = float(wacc["debt_to_equity_target"])
        max_de = float(wacc_config.get("max_de_ratio", 2.0))
        de_status = "pass" if 0.0 <= d_e <= max_de else "warn"
        checks.append(
            {
                "check": "target_de_bounds",
                "status": de_status,
                "metric": d_e,
                "message": f"Target D/E {d_e:.3f}; max allowed {max_de:.3f}.",
            }
        )
        check_status["target_de_bounds"] = de_status
    else:
        checks.append(
            {
                "check": "wacc_components",
                "status": "warn",
                "metric": None,
                "message": "wacc_components.csv missing.",
            }
        )
        check_status["wacc_components"] = "warn"

    val_path = paths.data_model / "valuation_outputs.csv"
    if val_path.exists():
        val = pd.read_csv(val_path)
        try:
            base = float(val.loc[val["scenario"] == "base", "fair_value_hkd_per_share"].iloc[0])
            bad = float(val.loc[val["scenario"] == "bad", "fair_value_hkd_per_share"].iloc[0])
            extreme = float(val.loc[val["scenario"] == "extreme", "fair_value_hkd_per_share"].iloc[0])
            ordered = extreme <= bad <= base
            status = "pass" if ordered else "warn"
            checks.append(
                {
                    "check": "scenario_ordering",
                    "status": status,
                    "metric": {"extreme": extreme, "bad": bad, "base": base},
                    "message": "Check extreme <= bad <= base.",
                }
            )
            check_status["scenario_ordering"] = status
        except IndexError:
            checks.append(
                {
                    "check": "scenario_ordering",
                    "status": "warn",
                    "metric": None,
                    "message": "valuation_outputs.csv missing one or more scenarios.",
                }
            )
            check_status["scenario_ordering"] = "warn"
    else:
        checks.append(
            {
                "check": "valuation_outputs",
                "status": "warn",
                "metric": None,
                "message": "valuation_outputs.csv missing.",
            }
        )
        check_status["valuation_outputs"] = "warn"

    require_override = bool(wacc_config.get("investor_grade_require_override", True))
    override_financials_path = paths.data_raw / asof / "tencent_financials.csv"
    override_segment_path = paths.data_raw / asof / "segment_revenue.csv"
    processed_financials_path = paths.data_processed / "tencent_financials.csv"
    processed_segment_path = paths.data_processed / "segment_revenue.csv"

    override_financials_exists = override_financials_path.exists()
    override_segment_exists = override_segment_path.exists()

    fundamentals_source = None
    segment_source = None
    fundamentals_method = None

    if processed_financials_path.exists():
        proc_fin = pd.read_csv(processed_financials_path)
        if not proc_fin.empty:
            if "fundamentals_source" in proc_fin.columns:
                fundamentals_source = str(proc_fin.iloc[0]["fundamentals_source"])
            if "fundamentals_method" in proc_fin.columns:
                fundamentals_method = str(proc_fin.iloc[0]["fundamentals_method"])

    if processed_segment_path.exists():
        proc_seg = pd.read_csv(processed_segment_path)
        if not proc_seg.empty and "segment_source" in proc_seg.columns:
            segment_source = str(proc_seg.iloc[0]["segment_source"])

    if override_financials_exists or override_segment_exists:
        using_expected_fin = (not override_financials_exists) or fundamentals_source == "override_csv"
        using_expected_seg = (not override_segment_exists) or segment_source == "override_csv"
        ok = using_expected_fin and using_expected_seg
        status = _status_from_bool(ok, fail_on_false=True)
        message = (
            "Override files are present and processed data uses override sources."
            if ok
            else "Override files exist but processed fundamentals/segments are not sourced from overrides."
        )
    else:
        status = "fail" if require_override else "warn"
        message = (
            "No override fundamentals found under data/raw/<asof>/; investor-grade run requires overrides."
            if require_override
            else "No override fundamentals found under data/raw/<asof>/; valuation uses default modeled fundamentals."
        )

    checks.append(
        {
            "check": "override_fundamentals_present",
            "status": status,
            "metric": {
                "override_financials_exists": override_financials_exists,
                "override_segment_exists": override_segment_exists,
                "fundamentals_source": fundamentals_source,
                "segment_source": segment_source,
            },
            "message": message,
        }
    )
    check_status["override_fundamentals_present"] = status

    ttm_ok = fundamentals_method == "ttm_4q_from_quarterly"
    ttm_status = _status_from_bool(ttm_ok, fail_on_false=require_override)
    checks.append(
        {
            "check": "fundamentals_ttm_method",
            "status": ttm_status,
            "metric": {"fundamentals_method": fundamentals_method},
            "message": (
                "Fundamentals are derived from strict 4-quarter TTM method."
                if ttm_ok
                else "Fundamentals method is not strict TTM-4Q."
            ),
        }
    )
    check_status["fundamentals_ttm_method"] = ttm_status

    market_inputs_path = paths.data_processed / "market_inputs.csv"
    peer_raw_path = paths.data_raw / asof / "peer_fundamentals.csv"
    peer_status = "warn"
    peer_metric: dict[str, Any] = {}
    if peer_raw_path.exists():
        peer_raw = pd.read_csv(peer_raw_path)
        missing_peers = sorted(set(peers).difference(set(peer_raw.get("ticker", []))))
        peer_ok = len(missing_peers) == 0
        peer_status = _status_from_bool(peer_ok, fail_on_false=True)
        peer_metric["missing_peers"] = missing_peers
    else:
        peer_metric["missing_peers"] = peers
        peer_status = "fail"

    checks.append(
        {
            "check": "peer_input_coverage",
            "status": peer_status,
            "metric": peer_metric,
            "message": "Peer input coverage check against data/raw/<asof>/peer_fundamentals.csv.",
        }
    )
    check_status["peer_input_coverage"] = peer_status

    max_age_months = int(qa_gates.get("peer_source_max_age_months", 18))
    recency_status = "warn"
    recency_metric: dict[str, Any] = {}
    if market_inputs_path.exists():
        market_inputs = pd.read_csv(market_inputs_path)
        if "peer_source_date" in market_inputs.columns:
            dated = market_inputs.loc[market_inputs["ticker"].isin(peers), ["ticker", "peer_source_date"]].copy()
            dated["peer_source_date"] = pd.to_datetime(dated["peer_source_date"], errors="coerce")
            dated = dated.dropna(subset=["peer_source_date"])
            if not dated.empty:
                asof_ts = pd.Timestamp(asof)
                ages = (asof_ts - dated["peer_source_date"]) / pd.Timedelta(days=30.4375)
                max_age = float(ages.max())
                recency_status = "pass" if max_age <= max_age_months else "warn"
                recency_metric = {"max_age_months": max_age, "threshold_months": max_age_months}
            else:
                recency_metric = {"max_age_months": None, "threshold_months": max_age_months}
        else:
            recency_metric = {"max_age_months": None, "threshold_months": max_age_months}

    checks.append(
        {
            "check": "peer_source_recency",
            "status": recency_status,
            "metric": recency_metric,
            "message": "Peer source recency check.",
        }
    )
    check_status["peer_source_recency"] = recency_status

    scen_bounds = qa_gates.get("scenario_bounds", {})
    growth_min = float(scen_bounds.get("growth_min", -0.5))
    growth_max = float(scen_bounds.get("growth_max", 0.5))
    margin_min = float(scen_bounds.get("margin_min", 0.0))
    margin_max = float(scen_bounds.get("margin_max", 0.8))
    capex_min = float(scen_bounds.get("capex_min", 0.0))
    capex_max = float(scen_bounds.get("capex_max", 0.4))
    nwc_min = float(scen_bounds.get("nwc_min", -0.1))
    nwc_max = float(scen_bounds.get("nwc_max", 0.2))

    violations: list[str] = []
    for scenario, cfg in scenarios_config.get("scenarios", {}).items():
        for value in cfg.get("revenue_growth", []):
            if not (growth_min <= float(value) <= growth_max):
                violations.append(f"{scenario}:revenue_growth")
                break
        for value in cfg.get("ebit_margin", []):
            if not (margin_min <= float(value) <= margin_max):
                violations.append(f"{scenario}:ebit_margin")
                break
        for value in cfg.get("capex_pct_revenue", []):
            if not (capex_min <= float(value) <= capex_max):
                violations.append(f"{scenario}:capex_pct_revenue")
                break
        for value in cfg.get("nwc_pct_revenue", []):
            if not (nwc_min <= float(value) <= nwc_max):
                violations.append(f"{scenario}:nwc_pct_revenue")
                break

    scen_status = "pass" if not violations else "fail"
    checks.append(
        {
            "check": "scenario_economic_consistency",
            "status": scen_status,
            "metric": {"violations": violations},
            "message": "Scenario assumptions are within configured economic bounds.",
        }
    )
    check_status["scenario_economic_consistency"] = scen_status

    backtest_summary_path = paths.data_model / "backtest_summary.csv"
    bt_cfg = qa_gates.get("backtest", {})
    min_points = int(bt_cfg.get("min_points", 4))
    min_hit_rate_12m = float(bt_cfg.get("min_hit_rate_12m", 0.45))
    max_cali_mae = float(bt_cfg.get("max_calibration_mae_12m", 0.35))
    calibration_metric = str(bt_cfg.get("calibration_metric", "bucket")).strip().lower()

    if backtest_summary_path.exists():
        bt = pd.read_csv(backtest_summary_path).iloc[0]
        n_points = int(bt.get("n_points", 0))
        hit12 = float(bt.get("hit_rate_12m", float("nan")))
        cali_bucket = float(bt.get("calibration_mae_12m_bucket", bt.get("calibration_mae_12m", float("nan"))))
        cali_raw = float(bt.get("calibration_mae_12m_raw", bt.get("calibration_mae_12m", float("nan"))))
        cali_selected = cali_bucket if calibration_metric == "bucket" else cali_raw

        coverage_ok = n_points >= min_points
        coverage_status = _status_from_bool(coverage_ok, fail_on_false=True)
        checks.append(
            {
                "check": "backtest_minimum_coverage",
                "status": coverage_status,
                "metric": {"n_points": n_points, "min_points": min_points},
                "message": "Backtest minimum coverage check.",
            }
        )
        check_status["backtest_minimum_coverage"] = coverage_status

        quality_ok = (
            coverage_ok
            and pd.notna(hit12)
            and pd.notna(cali_selected)
            and hit12 >= min_hit_rate_12m
            and cali_selected <= max_cali_mae
        )
        quality_status = _status_from_bool(quality_ok, fail_on_false=True)
        checks.append(
            {
                "check": "backtest_quality_flag",
                "status": quality_status,
                "metric": {
                    "hit_rate_12m": hit12,
                    "min_hit_rate_12m": min_hit_rate_12m,
                    "calibration_metric": calibration_metric,
                    "calibration_mae_12m_selected": cali_selected,
                    "calibration_mae_12m_bucket": cali_bucket,
                    "calibration_mae_12m_raw": cali_raw,
                    "max_calibration_mae_12m": max_cali_mae,
                },
                "message": "Backtest quality thresholds.",
            }
        )
        check_status["backtest_quality_flag"] = quality_status
    else:
        checks.append(
            {
                "check": "backtest_minimum_coverage",
                "status": "warn",
                "metric": {"n_points": None, "min_points": min_points},
                "message": "backtest_summary.csv missing.",
            }
        )
        check_status["backtest_minimum_coverage"] = "warn"
        checks.append(
            {
                "check": "backtest_quality_flag",
                "status": "warn",
                "metric": None,
                "message": "Backtest quality cannot be evaluated without backtest_summary.csv.",
            }
        )
        check_status["backtest_quality_flag"] = "warn"

    warnings_count = sum(1 for item in checks if item["status"] == "warn")
    failures_count = sum(1 for item in checks if item["status"] == "fail")

    investor_grade = (
        failures_count == 0
        and check_status.get("override_fundamentals_present") == "pass"
        and check_status.get("fundamentals_ttm_method") == "pass"
        and check_status.get("backtest_minimum_coverage") == "pass"
    )

    payload = {
        "asof": asof,
        "summary": {
            "total_checks": len(checks),
            "warnings": warnings_count,
            "failures": failures_count,
            "investor_grade": investor_grade,
        },
        "checks": checks,
    }

    with artifacts.qa_report_json.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    return artifacts
