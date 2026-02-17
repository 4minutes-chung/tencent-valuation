from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .backtest import BacktestArtifacts, run_backtest
from .config import load_yaml
from .dcf import DcfArtifacts, run_valuation
from .fetch import FetchArtifacts, run_fetch
from .factors import FactorArtifacts, run_factors
from .overrides import OverrideArtifacts, build_overrides
from .paths import ProjectPaths, build_paths
from .qa import QaArtifacts, run_qa
from .report import write_investment_memo, write_report
from .wacc import WaccArtifacts, WaccResult, run_wacc


@dataclass(frozen=True)
class PipelineContext:
    paths: ProjectPaths
    wacc_config: dict
    qa_gates: dict
    peers: list[str]
    scenarios_config: dict



def load_context(project_root: str | Path | None = None) -> PipelineContext:
    paths = build_paths(project_root)
    paths.ensure()

    wacc_config = load_yaml(paths.config / "wacc.yaml")
    qa_gates = load_yaml(paths.config / "qa_gates.yaml")
    peers_cfg = load_yaml(paths.config / "peers.yaml")
    scenarios_config = load_yaml(paths.config / "scenarios.yaml")

    peers = peers_cfg.get("peers", [])
    if not isinstance(peers, list) or not peers:
        raise RuntimeError("config/peers.yaml must contain non-empty 'peers' list")

    return PipelineContext(
        paths=paths,
        wacc_config=wacc_config,
        qa_gates=qa_gates,
        peers=[str(item) for item in peers],
        scenarios_config=scenarios_config,
    )



def _snapshot_sources(asof: str, ctx: PipelineContext) -> Path:
    manifest = {
        "asof": asof,
        "sources": [
            "Tencent IR filings",
            "HKEX filing metadata",
            "SFC short position data",
            "Market returns + factor series",
        ],
        "note": "Use `tencent-valuation fetch` for raw snapshots from web sources.",
    }
    raw_dir = ctx.paths.data_raw / asof
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "pipeline_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest_path



def fetch_step(asof: str, project_root: str | Path | None = None) -> FetchArtifacts:
    ctx = load_context(project_root)
    return run_fetch(asof=asof, paths=ctx.paths)



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



def value_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> DcfArtifacts:
    ctx = load_context(project_root)
    factor_artifacts = run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh_factors,
        source_mode=source_mode,
    )
    wacc_artifacts, _ = run_wacc(asof, ctx.paths, factor_artifacts, ctx.peers, ctx.wacc_config)
    return run_valuation(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)



def qa_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> QaArtifacts:
    ctx = load_context(project_root)
    factor_artifacts = run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh_factors,
        source_mode=source_mode,
    )
    wacc_artifacts, _ = run_wacc(asof, ctx.paths, factor_artifacts, ctx.peers, ctx.wacc_config)
    run_valuation(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    return run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)



def report_step(
    asof: str,
    project_root: str | Path | None = None,
    refresh_factors: bool = False,
    source_mode: str | None = None,
) -> Path:
    ctx = load_context(project_root)
    factor_artifacts = run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh_factors,
        source_mode=source_mode,
    )
    wacc_artifacts, _ = run_wacc(asof, ctx.paths, factor_artifacts, ctx.peers, ctx.wacc_config)
    run_valuation(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)
    write_investment_memo(asof, ctx.paths)
    return write_report(asof, ctx.paths)



def run_all(
    asof: str,
    project_root: str | Path | None = None,
    refresh: bool = False,
    source_mode: str | None = None,
) -> dict[str, str]:
    ctx = load_context(project_root)
    _snapshot_sources(asof, ctx)

    factor_artifacts = run_factors(
        asof,
        ctx.paths,
        ctx.peers,
        ctx.wacc_config,
        refresh=refresh,
        source_mode=source_mode,
    )
    wacc_artifacts, wacc_result = run_wacc(asof, ctx.paths, factor_artifacts, ctx.peers, ctx.wacc_config)
    dcf_artifacts = run_valuation(asof, ctx.paths, ctx.scenarios_config, wacc_artifacts.wacc_components)
    qa_artifacts = run_qa(asof, ctx.paths, ctx.wacc_config, ctx.qa_gates, ctx.peers, ctx.scenarios_config)
    report_path = write_report(asof, ctx.paths)
    memo_path = write_investment_memo(asof, ctx.paths)

    return {
        "weekly_returns": str(factor_artifacts.weekly_returns),
        "monthly_factors": str(factor_artifacts.monthly_factors),
        "wacc_components": str(wacc_artifacts.wacc_components),
        "capm_apt_compare": str(wacc_artifacts.capm_apt_compare),
        "valuation_outputs": str(dcf_artifacts.valuation_outputs),
        "sensitivity_wacc_g": str(dcf_artifacts.sensitivity_wacc_g),
        "sensitivity_margin_growth": str(dcf_artifacts.sensitivity_margin_growth),
        "scenario_assumptions_used": str(dcf_artifacts.scenario_assumptions_used),
        "qa_report": str(qa_artifacts.qa_report_json),
        "report": str(report_path),
        "investment_memo": str(memo_path),
        "wacc": f"{wacc_result.wacc:.6f}",
    }
