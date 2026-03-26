from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .paths import ProjectPaths
from .provenance import validate_required_columns


@dataclass(frozen=True)
class QaArtifacts:
    qa_report_json: Path


def _default_artifacts(paths: ProjectPaths, asof: str) -> QaArtifacts:
    return QaArtifacts(qa_report_json=paths.reports / f"qa_{asof}.json")


def _status_from_bool(ok: bool, fail_on_false: bool = False) -> str:
    if ok:
        return "pass"
    return "fail" if fail_on_false else "warn"


def _append_check(checks: list[dict[str, Any]], name: str, status: str, metric: Any, message: str) -> None:
    checks.append(
        {
            "check": name,
            "status": status,
            "metric": metric,
            "message": message,
        }
    )


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
        _append_check(
            checks,
            "segment_sum_to_total",
            status,
            max_diff,
            "Segment revenues reconcile to total revenue.",
        )
        check_status["segment_sum_to_total"] = status
    else:
        _append_check(
            checks,
            "segment_sum_to_total",
            "warn",
            None,
            "segment_revenue.csv missing.",
        )
        check_status["segment_sum_to_total"] = "warn"

    wacc_path = paths.data_model / "wacc_components.csv"
    if wacc_path.exists():
        wacc = pd.read_csv(wacc_path).iloc[0]
        gap_bps = float(wacc["capm_apt_gap_bps"])
        limit = float(wacc_config.get("capm_apt_alert_bps", 150))
        gap_status = "pass" if gap_bps <= limit else "warn"
        _append_check(
            checks,
            "capm_apt_gap",
            gap_status,
            gap_bps,
            f"CAPM/APT gap {gap_bps:.1f} bps; threshold {limit:.1f} bps.",
        )
        check_status["capm_apt_gap"] = gap_status

        unstable = bool(wacc.get("apt_is_unstable", False))
        unstable_limit = float(wacc_config.get("apt_unstable_gap_bps", 400.0))
        unstable_status = "warn" if unstable else "pass"
        _append_check(
            checks,
            "apt_stability_gate",
            unstable_status,
            {
                "apt_is_unstable": unstable,
                "gap_bps": gap_bps,
                "unstable_threshold_bps": unstable_limit,
                "reason_codes": str(wacc.get("apt_unstable_reason_codes", "")),
            },
            (
                "APT diagnostic marked unstable and excluded from headline valuation."
                if unstable
                else "APT diagnostic is within stability gate."
            ),
        )
        check_status["apt_stability_gate"] = unstable_status

        d_e = float(wacc["debt_to_equity_target"])
        max_de = float(wacc_config.get("max_de_ratio", 2.0))
        de_status = "pass" if 0.0 <= d_e <= max_de else "warn"
        _append_check(
            checks,
            "target_de_bounds",
            de_status,
            d_e,
            f"Target D/E {d_e:.3f}; max allowed {max_de:.3f}.",
        )
        check_status["target_de_bounds"] = de_status

        # Phase 6C: ERP reasonableness
        if "erp_annual" in wacc.index:
            erp_val = float(wacc["erp_annual"])
            erp_ok = 0.03 <= erp_val <= 0.10
            erp_status = "pass" if erp_ok else "warn"
            _append_check(
                checks,
                "erp_reasonableness",
                erp_status,
                {"erp": erp_val, "bounds": [0.03, 0.10]},
                f"ERP {erp_val:.3f} {'within' if erp_ok else 'outside'} [3%, 10%] bounds.",
            )
            check_status["erp_reasonableness"] = erp_status

        # Phase 6C: CRP reasonableness
        if "crp" in wacc.index:
            crp_val = float(wacc["crp"])
            crp_ok = 0.0 <= crp_val <= 0.05
            crp_status = "pass" if crp_ok else "warn"
            _append_check(
                checks,
                "crp_reasonableness",
                crp_status,
                {"crp": crp_val, "bounds": [0.0, 0.05]},
                f"CRP {crp_val:.4f} {'within' if crp_ok else 'outside'} [0%, 5%] bounds.",
            )
            check_status["crp_reasonableness"] = crp_status

        # Phase 6C: Beta adjustment applied flag
        beta_adj = str(wacc_config.get("beta_adjustment", "none")).lower()
        beta_adj_ok = beta_adj in ("vasicek", "blume")
        beta_adj_status = "pass" if beta_adj_ok else "warn"
        _append_check(
            checks,
            "beta_adjustment_applied",
            beta_adj_status,
            {"beta_adjustment": beta_adj},
            f"Beta adjustment method: {beta_adj!r}. Vasicek or Blume required for investor-grade.",
        )
        check_status["beta_adjustment_applied"] = beta_adj_status
    else:
        _append_check(
            checks,
            "wacc_components",
            "warn",
            None,
            "wacc_components.csv missing.",
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
            status = "pass" if ordered else "fail"
            _append_check(
                checks,
                "scenario_ordering",
                status,
                {"extreme": extreme, "bad": bad, "base": base},
                "Check extreme <= bad <= base.",
            )
            check_status["scenario_ordering"] = status
        except IndexError:
            _append_check(
                checks,
                "scenario_ordering",
                "fail",
                None,
                "valuation_outputs.csv missing one or more scenarios.",
            )
            check_status["scenario_ordering"] = "fail"
    else:
        _append_check(
            checks,
            "valuation_outputs",
            "warn",
            None,
            "valuation_outputs.csv missing.",
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

    _append_check(
        checks,
        "override_fundamentals_present",
        status,
        {
            "override_financials_exists": override_financials_exists,
            "override_segment_exists": override_segment_exists,
            "fundamentals_source": fundamentals_source,
            "segment_source": segment_source,
        },
        message,
    )
    check_status["override_fundamentals_present"] = status

    ttm_ok = fundamentals_method == "ttm_4q_from_quarterly"
    ttm_status = _status_from_bool(ttm_ok, fail_on_false=require_override)
    _append_check(
        checks,
        "fundamentals_ttm_method",
        ttm_status,
        {"fundamentals_method": fundamentals_method},
        (
            "Fundamentals are derived from strict 4-quarter TTM method."
            if ttm_ok
            else "Fundamentals method is not strict TTM-4Q."
        ),
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

    _append_check(
        checks,
        "peer_input_coverage",
        peer_status,
        peer_metric,
        "Peer input coverage check against data/raw/<asof>/peer_fundamentals.csv.",
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

    _append_check(
        checks,
        "peer_source_recency",
        recency_status,
        recency_metric,
        "Peer source recency check.",
    )
    check_status["peer_source_recency"] = recency_status

    source_manifest_path = paths.data_raw / asof / "source_manifest.json"
    if source_manifest_path.exists():
        source = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        entries = source.get("entries", []) if isinstance(source, dict) else []
        n_errors = sum(1 for item in entries if str(item.get("status", "")).lower() == "error")
        s_status = "pass" if n_errors == 0 else "warn"
        _append_check(
            checks,
            "source_manifest_health",
            s_status,
            {"entries": len(entries), "errors": n_errors},
            "Source manifest ingestion status.",
        )
        check_status["source_manifest_health"] = s_status
    else:
        _append_check(
            checks,
            "source_manifest_health",
            "warn",
            None,
            "source_manifest.json missing.",
        )
        check_status["source_manifest_health"] = "warn"

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
    _append_check(
        checks,
        "scenario_economic_consistency",
        scen_status,
        {"violations": violations},
        "Scenario assumptions are within configured economic bounds.",
    )
    check_status["scenario_economic_consistency"] = scen_status

    # Phase 6C: Stress scenario coverage (≥ 2 defined)
    stress_scenarios = scenarios_config.get("stress_scenarios", {})
    n_stress = len(stress_scenarios)
    stress_ok = n_stress >= 2
    stress_cov_status = "pass" if stress_ok else "warn"
    _append_check(
        checks,
        "stress_scenario_coverage",
        stress_cov_status,
        {"n_stress_scenarios": n_stress, "min_required": 2},
        f"{n_stress} stress scenarios defined; minimum 2 recommended.",
    )
    check_status["stress_scenario_coverage"] = stress_cov_status

    # Phase 6C: FX staleness (check market_inputs.csv for fx_date if present)
    if market_inputs_path.exists():
        market_inputs_df = pd.read_csv(market_inputs_path)
        if "fx_cny_hkd_date" in market_inputs_df.columns and not market_inputs_df.empty:
            fx_date_raw = market_inputs_df.iloc[0].get("fx_cny_hkd_date")
            try:
                fx_date = pd.Timestamp(fx_date_raw)
                asof_ts_fx = pd.Timestamp(asof)
                fx_age_days = int((asof_ts_fx - fx_date).days)
                recency_fail = int(wacc_config.get("source_recency_fail_days", 90))
                recency_warn_days = int(wacc_config.get("source_recency_warn_days", 30))
                if fx_age_days > recency_fail:
                    fx_status = "fail"
                elif fx_age_days > recency_warn_days:
                    fx_status = "warn"
                else:
                    fx_status = "pass"
                _append_check(
                    checks,
                    "fx_staleness",
                    fx_status,
                    {"fx_age_days": fx_age_days, "warn_days": recency_warn_days, "fail_days": recency_fail},
                    f"CNY/HKD FX rate is {fx_age_days} days old.",
                )
                check_status["fx_staleness"] = fx_status
            except Exception:
                _append_check(checks, "fx_staleness", "warn", None, "FX date could not be parsed.")
                check_status["fx_staleness"] = "warn"

    # Schema contract checks
    schema_checks = {
        paths.data_model / "wacc_components.csv": [
            "asof",
            "wacc",
            "re_capm",
            "re_apt_guardrailed",
            "beta_stability_score",
            "apt_unstable_reason_codes",
        ],
        paths.data_model / "valuation_outputs.csv": ["scenario", "fair_value_hkd_per_share", "margin_of_safety"],
        paths.data_model / "valuation_method_outputs.csv": [
            "scenario",
            "method",
            "fair_value_hkd_per_share",
            "weight",
        ],
        paths.data_model / "valuation_ensemble.csv": [
            "scenario",
            "ensemble_fair_value_hkd_per_share",
            "band_width_ratio",
        ],
        paths.data_model / "tvalue_company_bridge.csv": [
            "scenario",
            "total_equity_value_hkd_bn",
            "fair_value_hkd_per_share",
        ],
        paths.data_model / "reverse_dcf_outputs.csv": [
            "implied_terminal_g",
            "implied_margin_shift_bps",
            "implied_growth_shift_bps",
        ],
    }
    for path, required_cols in schema_checks.items():
        result = validate_required_columns(path, required_cols)
        status = "pass" if result.ok else "fail"
        _append_check(
            checks,
            f"schema::{path.name}",
            status,
            {"missing_columns": result.missing_columns},
            f"Schema contract for {path.name}.",
        )
        check_status[f"schema::{path.name}"] = status

    headline_cfg = qa_gates.get("headline", {})
    fail_on_nan = bool(headline_cfg.get("fail_on_nan", True))
    max_band_width_ratio = float(headline_cfg.get("max_band_width_ratio", 3.5))

    ensemble_path = paths.data_model / "valuation_ensemble.csv"
    if ensemble_path.exists():
        ensemble = pd.read_csv(ensemble_path)
        headline_cols = ["ensemble_fair_value_hkd_per_share", "method_min_hkd_per_share", "method_max_hkd_per_share"]
        nan_any = bool(ensemble[headline_cols].isna().any().any()) if not ensemble.empty else True
        nan_status = _status_from_bool(not nan_any, fail_on_false=fail_on_nan)
        _append_check(
            checks,
            "headline_nan_check",
            nan_status,
            {"has_nan": nan_any},
            "No NaN values in ensemble headline outputs.",
        )
        check_status["headline_nan_check"] = nan_status

        bw = float(ensemble["band_width_ratio"].max()) if not ensemble.empty else float("inf")
        bw_status = "pass" if bw <= max_band_width_ratio else "warn"
        _append_check(
            checks,
            "ensemble_band_width",
            bw_status,
            {"max_band_width_ratio": bw, "threshold": max_band_width_ratio},
            "Ensemble valuation band width sanity check.",
        )
        check_status["ensemble_band_width"] = bw_status
    else:
        _append_check(
            checks,
            "headline_nan_check",
            "warn",
            None,
            "valuation_ensemble.csv missing.",
        )
        check_status["headline_nan_check"] = "warn"
        _append_check(
            checks,
            "ensemble_band_width",
            "warn",
            None,
            "valuation_ensemble.csv missing.",
        )
        check_status["ensemble_band_width"] = "warn"

    backtest_summary_path = paths.data_model / "backtest_summary.csv"
    bt_cfg = qa_gates.get("backtest", {})
    min_points = int(bt_cfg.get("min_points", 4))
    min_hit_rate_12m = float(bt_cfg.get("min_hit_rate_12m", 0.45))
    max_cali_mae = float(bt_cfg.get("max_calibration_mae_12m", 0.35))
    min_interval_cov = float(bt_cfg.get("min_interval_coverage_12m", 0.40))
    calibration_metric = str(bt_cfg.get("calibration_metric", "bucket")).strip().lower()

    min_ic_12m = float(bt_cfg.get("min_ic_12m", 0.10))
    max_slope_dev = float(bt_cfg.get("max_calibration_slope_deviation", 0.50))

    if backtest_summary_path.exists():
        bt = pd.read_csv(backtest_summary_path).iloc[0]
        n_points = int(bt.get("n_points", 0))
        hit12 = float(bt.get("hit_rate_12m", float("nan")))
        cali_bucket = float(bt.get("calibration_mae_12m_bucket", bt.get("calibration_mae_12m", float("nan"))))
        cali_raw = float(bt.get("calibration_mae_12m_raw", bt.get("calibration_mae_12m", float("nan"))))
        interval_cov = float(bt.get("interval_coverage_12m", float("nan")))
        cali_selected = cali_bucket if calibration_metric == "bucket" else cali_raw

        coverage_ok = n_points >= min_points
        coverage_status = _status_from_bool(coverage_ok, fail_on_false=True)
        _append_check(
            checks,
            "backtest_minimum_coverage",
            coverage_status,
            {"n_points": n_points, "min_points": min_points},
            "Backtest minimum coverage check.",
        )
        check_status["backtest_minimum_coverage"] = coverage_status

        quality_ok = (
            coverage_ok
            and pd.notna(hit12)
            and pd.notna(cali_selected)
            and hit12 >= min_hit_rate_12m
            and cali_selected <= max_cali_mae
            and pd.notna(interval_cov)
            and interval_cov >= min_interval_cov
        )
        quality_status = _status_from_bool(quality_ok, fail_on_false=True)
        _append_check(
            checks,
            "backtest_quality_flag",
            quality_status,
            {
                "hit_rate_12m": hit12,
                "min_hit_rate_12m": min_hit_rate_12m,
                "calibration_metric": calibration_metric,
                "calibration_mae_12m_selected": cali_selected,
                "calibration_mae_12m_bucket": cali_bucket,
                "calibration_mae_12m_raw": cali_raw,
                "max_calibration_mae_12m": max_cali_mae,
                "interval_coverage_12m": interval_cov,
                "min_interval_coverage_12m": min_interval_cov,
            },
            "Backtest quality thresholds.",
        )
        check_status["backtest_quality_flag"] = quality_status

        # Phase 6C: IC gate (new)
        ic_12m = float(bt.get("information_coefficient_12m", float("nan")))
        if pd.notna(ic_12m):
            ic_ok = ic_12m >= min_ic_12m
            ic_status = _status_from_bool(ic_ok, fail_on_false=False)
            _append_check(
                checks,
                "backtest_ic_gate",
                ic_status,
                {"ic_12m": ic_12m, "min_ic_12m": min_ic_12m},
                f"Backtest IC (12m) {ic_12m:.3f}; threshold {min_ic_12m:.3f}.",
            )
            check_status["backtest_ic_gate"] = ic_status

        # Phase 6C: Calibration slope deviation (new)
        slope_12m = float(bt.get("calibration_slope_12m", float("nan")))
        if pd.notna(slope_12m):
            slope_dev = abs(slope_12m - 1.0)
            slope_ok = slope_dev <= max_slope_dev
            slope_status = _status_from_bool(slope_ok, fail_on_false=False)
            _append_check(
                checks,
                "backtest_calibration_slope",
                slope_status,
                {"calibration_slope_12m": slope_12m, "deviation_from_1": slope_dev, "max_deviation": max_slope_dev},
                f"Calibration slope {slope_12m:.3f}; |deviation from 1.0| = {slope_dev:.3f}.",
            )
            check_status["backtest_calibration_slope"] = slope_status
    else:
        _append_check(
            checks,
            "backtest_minimum_coverage",
            "warn",
            {"n_points": None, "min_points": min_points},
            "backtest_summary.csv missing.",
        )
        check_status["backtest_minimum_coverage"] = "warn"
        _append_check(
            checks,
            "backtest_quality_flag",
            "warn",
            None,
            "Backtest quality cannot be evaluated without backtest_summary.csv.",
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
