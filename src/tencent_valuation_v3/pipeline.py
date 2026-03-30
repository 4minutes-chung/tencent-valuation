from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .apv import ApvArtifacts, run_apv
from .backtest import BacktestArtifacts, run_backtest
from .comps import CompsArtifacts, run_comps
from .config import load_yaml
from .dcf import DcfArtifacts, run_valuation
from .ensemble import EnsembleArtifacts, run_ensemble
from .eva import EvaArtifacts, run_eva
from .factors import FactorArtifacts, run_factors
from .fetch import FetchArtifacts, run_fetch
from .monte_carlo import MonteCarloArtifacts, run_monte_carlo
from .overrides import OverrideArtifacts, build_overrides
from .paths import ProjectPaths, build_paths
from .qa import QaArtifacts, run_qa
from .real_options import RealOptionsArtifacts, run_real_options
from .report import write_compact_log, write_investment_memo, write_report
from .residual_income import ResidualIncomeArtifacts, run_residual_income
from .reverse_dcf import ReverseDcfArtifacts, run_reverse_dcf
from .sotp import SotpArtifacts, run_tvalue
from .stress import StressArtifacts, run_stress_scenarios
from .wacc import WaccArtifacts, WaccResult, run_wacc


@dataclass(frozen=True)
class PipelineContext:
    paths: ProjectPaths
    wacc_config: dict
    qa_gates: dict
    peers: list[str]
    scenarios_config: dict
    method_weights: dict
    sources: dict


def load_context(project_root: str | Path | None = None) -> PipelineContext:
    paths = build_paths(project_root)
    paths.ensure()

    wacc_config = load_yaml(paths.config / "wacc.yaml")
    qa_gates = load_yaml(paths.config / "qa_gates.yaml")
    peers_cfg = load_yaml(paths.config / "peers.yaml")
    scenarios_config = load_yaml(paths.config / "scenarios.yaml")
    method_weights = load_yaml(paths.config / "method_weights.yaml")
    sources = load_yaml(paths.config / "sources.yaml")

    peers = peers_cfg.get("peers", [])
    if not isinstance(peers, list) or not peers:
        raise RuntimeError("config/peers.yaml must contain non-empty 'peers' list")

    return PipelineContext(
        paths=paths,
        wacc_config=wacc_config,
        qa_gates=qa_gates,
        peers=[str(item) for item in peers],
        scenarios_config=scenarios_config,
        method_weights=method_weights,
        sources=sources,
    )


def _snapshot_sources(asof: str, ctx: PipelineContext) -> Path:
    manifest = {
        "asof": asof,
        "sources": [
            "Tencent IR filings",
            "HKEX filing metadata",
            "SFC short position data",
            "Market returns + factor series",
            "FRED/Treasury rates",
        ],
        "note": "Use `tencent-valuation-v4 fetch` for raw snapshots from web sources.",
    }
    raw_dir = ctx.paths.data_raw / asof
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "pipeline_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest_path


def _run_core(
    asof: str,
    ctx: PipelineContext,
    refresh_factors: bool,
    source_mode: str | None,
) -> tuple[FactorArtifacts, WaccArtifacts, WaccResult, DcfArtifacts]:
    factor_artifacts = run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh_factors,
        source_mode=source_mode,
    )
    wacc_artifacts, wacc_result = run_wacc(asof, ctx.paths, factor_artifacts, ctx.peers, ctx.wacc_config)
    dcf_artifacts = run_valuation(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    return factor_artifacts, wacc_artifacts, wacc_result, dcf_artifacts


def _run_multimethod(
    asof: str,
    ctx: PipelineContext,
    wacc_artifacts: WaccArtifacts,
    dcf_artifacts: DcfArtifacts,
) -> tuple[
    ApvArtifacts,
    ResidualIncomeArtifacts,
    CompsArtifacts,
    SotpArtifacts,
    ReverseDcfArtifacts,
    EvaArtifacts,
    MonteCarloArtifacts,
    RealOptionsArtifacts,
    StressArtifacts,
]:
    apv_artifacts = run_apv(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    residual_artifacts = run_residual_income(
        asof,
        ctx.paths,
        ctx.scenarios_config,
        wacc_artifacts.wacc_components,
    )
    comps_artifacts = run_comps(asof, ctx.paths, ctx.peers, wacc_artifacts.wacc_components, ctx.scenarios_config)
    tvalue_artifacts = run_tvalue(
        asof,
        ctx.paths,
        wacc_artifacts.wacc_components,
        dcf_artifacts.valuation_outputs,
        ctx.wacc_config,
    )
    reverse_artifacts = run_reverse_dcf(
        asof,
        ctx.paths,
        ctx.scenarios_config,
        wacc_artifacts.wacc_components,
    )
    eva_artifacts = run_eva(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    mc_artifacts = run_monte_carlo(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    ro_artifacts = run_real_options(asof, ctx.paths, wacc_artifacts.wacc_components, ctx.wacc_config)
    stress_artifacts = run_stress_scenarios(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    return (
        apv_artifacts, residual_artifacts, comps_artifacts, tvalue_artifacts,
        reverse_artifacts, eva_artifacts, mc_artifacts, ro_artifacts, stress_artifacts,
    )


def fetch_step(asof: str, project_root: str | Path | None = None) -> FetchArtifacts:
    ctx = load_context(project_root)
    return run_fetch(asof=asof, paths=ctx.paths, sources_config=ctx.sources)


def build_overrides_step(asof: str, project_root: str | Path | None = None) -> OverrideArtifacts:
    ctx = load_context(project_root)
    return build_overrides(asof=asof, paths=ctx.paths, wacc_config=ctx.wacc_config, peers=ctx.peers)


def backtest_step(
    start: str,
    end: str,
    freq: str,
    project_root: str | Path | None = None,
    source_mode: str | None = None,
) -> BacktestArtifacts:
    ctx = load_context(project_root)
    return run_backtest(
        start=start,
        end=end,
        freq=freq,
        paths=ctx.paths,
        wacc_config=ctx.wacc_config,
        scenarios_config=ctx.scenarios_config,
        peers=ctx.peers,
        source_mode=source_mode,
    )


def factors_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh: bool = False,
    source_mode: str | None = None,
) -> FactorArtifacts:
    ctx = load_context(project_root)
    _snapshot_sources(asof, ctx)
    return run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh,
        source_mode=source_mode,
    )


def wacc_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> tuple[WaccArtifacts, WaccResult]:
    ctx = load_context(project_root)
    factor_artifacts = run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh_factors,
        source_mode=source_mode,
    )
    return run_wacc(asof, ctx.paths, factor_artifacts, ctx.peers, ctx.wacc_config)


def dcf_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> DcfArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    return dcf_artifacts


def apv_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> ApvArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    apv_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return apv_artifacts


def residual_income_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> ResidualIncomeArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, residual_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return residual_artifacts


def comps_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> CompsArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, _, comps_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return comps_artifacts


def tvalue_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> SotpArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, _, _, tvalue_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return tvalue_artifacts


def reverse_dcf_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> ReverseDcfArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, _, _, _, reverse_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return reverse_artifacts


def monte_carlo_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> MonteCarloArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, _, _, _, _, _, mc_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return mc_artifacts


def eva_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> EvaArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, _, _, _, _, eva_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return eva_artifacts


def real_options_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> RealOptionsArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _, _, _, _, _, _, _, ro_artifacts, *_ = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return ro_artifacts


def stress_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> StressArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    *_, stress_artifacts = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return stress_artifacts


def ensemble_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> EnsembleArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    qa_artifacts = run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)
    return run_ensemble(
        asof,
        ctx.paths,
        ctx.method_weights,
        qa_artifacts.qa_report_json,
        wacc_artifacts.wacc_components,
    )


def qa_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> QaArtifacts:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    return run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)


def report_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> Path:
    ctx = load_context(project_root)
    _, wacc_artifacts, _, dcf_artifacts = _run_core(asof, ctx, refresh_factors, source_mode)
    _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    qa_artifacts = run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)
    run_ensemble(
        asof,
        ctx.paths,
        ctx.method_weights,
        qa_artifacts.qa_report_json,
        wacc_artifacts.wacc_components,
    )
    write_investment_memo(asof, ctx.paths)
    write_compact_log(asof, ctx.paths)
    return write_report(asof, ctx.paths)


def run_all(
    asof: str,
    project_root: str | Path | None = None,
    refresh: bool = False,
    source_mode: str | None = None,
) -> dict[str, str]:
    ctx = load_context(project_root)
    _snapshot_sources(asof, ctx)

    factor_artifacts, wacc_artifacts, wacc_result, dcf_artifacts = _run_core(asof, ctx, refresh, source_mode)
    (
        apv_artifacts, residual_artifacts, comps_artifacts, tvalue_artifacts,
        reverse_artifacts, eva_artifacts, mc_artifacts, ro_artifacts, stress_artifacts,
    ) = _run_multimethod(asof, ctx, wacc_artifacts, dcf_artifacts)
    backtest_artifacts = run_backtest(
        start="2018-01-01",
        end=asof,
        freq="quarterly",
        paths=ctx.paths,
        wacc_config=ctx.wacc_config,
        scenarios_config=ctx.scenarios_config,
        peers=ctx.peers,
        source_mode=source_mode,
    )
    qa_artifacts = run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)
    ensemble_artifacts = run_ensemble(
        asof,
        ctx.paths,
        ctx.method_weights,
        qa_artifacts.qa_report_json,
        wacc_artifacts.wacc_components,
    )

    report_path = write_report(asof, ctx.paths)
    memo_path = write_investment_memo(asof, ctx.paths)
    compact_log_path = write_compact_log(asof, ctx.paths)

    return {
        "weekly_returns": str(factor_artifacts.weekly_returns),
        "monthly_factors": str(factor_artifacts.monthly_factors),
        "wacc_components": str(wacc_artifacts.wacc_components),
        "capm_apt_compare": str(wacc_artifacts.capm_apt_compare),
        "valuation_outputs": str(dcf_artifacts.valuation_outputs),
        "apv_outputs": str(apv_artifacts.apv_outputs),
        "residual_income_outputs": str(residual_artifacts.residual_income_outputs),
        "peer_multiples": str(comps_artifacts.peer_multiples),
        "relative_valuation_outputs": str(comps_artifacts.relative_valuation_outputs),
        "tvalue_company_bridge": str(tvalue_artifacts.tvalue_company_bridge),
        "tvalue_stat_diagnostics": str(tvalue_artifacts.tvalue_stat_diagnostics),
        "reverse_dcf_outputs": str(reverse_artifacts.reverse_dcf_outputs),
        "eva_outputs": str(eva_artifacts.eva_outputs),
        "monte_carlo_outputs": str(mc_artifacts.monte_carlo_outputs),
        "monte_carlo_percentiles": str(mc_artifacts.monte_carlo_percentiles),
        "real_options_outputs": str(ro_artifacts.real_options_outputs),
        "stress_scenario_outputs": str(stress_artifacts.stress_scenario_outputs),
        "valuation_method_outputs": str(ensemble_artifacts.valuation_method_outputs),
        "valuation_ensemble": str(ensemble_artifacts.valuation_ensemble),
        "sensitivity_wacc_g": str(dcf_artifacts.sensitivity_wacc_g),
        "sensitivity_margin_growth": str(dcf_artifacts.sensitivity_margin_growth),
        "scenario_assumptions_used": str(dcf_artifacts.scenario_assumptions_used),
        "backtest_summary": str(backtest_artifacts.summary),
        "backtest_point_results": str(backtest_artifacts.point_results),
        "backtest_regime_breakdown": str(backtest_artifacts.regime_breakdown),
        "qa_report": str(qa_artifacts.qa_report_json),
        "report": str(report_path),
        "investment_memo": str(memo_path),
        "compact_log": str(compact_log_path),
        "wacc": f"{wacc_result.wacc:.6f}",
    }
