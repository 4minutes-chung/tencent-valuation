from __future__ import annotations

import argparse
import json
from typing import Sequence

from .pipeline import (
    apv_step,
    backtest_step,
    build_overrides_step,
    comps_step,
    dcf_step,
    ensemble_step,
    eva_step,
    factors_step,
    fetch_step,
    monte_carlo_step,
    qa_step,
    real_options_step,
    report_step,
    residual_income_step,
    reverse_dcf_step,
    run_all,
    stress_step,
    tvalue_step,
    wacc_step,
)


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tencent-valuation-v4")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch raw web snapshots into data/raw/<asof>")
    fetch.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    fetch.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")

    build_overrides = subparsers.add_parser("build-overrides", help="Build filing-derived TTM override pack")
    build_overrides.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    build_overrides.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")

    for cmd, help_text in [
        ("factors", "Build/validate factor and market inputs"),
        ("wacc", "Run MM + CAPM/APT WACC engine"),
        ("dcf", "Run 3-scenario DCF valuation"),
        ("apv", "Run APV valuation module"),
        ("residual-income", "Run residual income valuation module"),
        ("comps", "Run peer multiple valuation module"),
        ("tvalue", "Run T-value company bridge + factor t-stat diagnostics"),
        ("reverse-dcf", "Run reverse DCF implied assumptions"),
        ("monte-carlo", "Run Monte Carlo simulation"),
        ("eva", "Run Excess Return / EVA model"),
        ("real-options", "Run real options (Black-Scholes) overlay"),
        ("stress", "Run named stress scenario valuations"),
        ("ensemble", "Run cross-method ensemble valuation"),
        ("qa", "Run QA checks"),
        ("report", "Build markdown report and memo"),
    ]:
        p = subparsers.add_parser(cmd, help=help_text)
        p.add_argument("--project-root", default=".", help="Project root (default: current directory)")
        p.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
        p.add_argument("--refresh-factors", action="store_true", help="Regenerate factor inputs")
        p.add_argument(
            "--source-mode",
            choices=["auto", "live", "synthetic"],
            default=None,
            help="Input source mode override",
        )
        if cmd == "factors":
            p.add_argument("--refresh", action="store_true", help="Regenerate factor inputs")

    backtest = subparsers.add_parser("backtest", help="Run rolling backtest (quarterly or monthly)")
    backtest.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    backtest.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    backtest.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    backtest.add_argument("--freq", default="quarterly", choices=["quarterly", "monthly"], help="Backtest frequency")
    backtest.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default="auto",
        help="Input source mode override",
    )

    runall = subparsers.add_parser("run-all", help="Run full pipeline")
    runall.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    runall.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
    runall.add_argument("--refresh", action="store_true", help="Regenerate factor inputs")
    runall.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default=None,
        help="Input source mode override",
    )

    return parser


def _print_artifact(artifacts: object) -> None:
    print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _base_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        _print_artifact(fetch_step(args.asof, project_root=args.project_root))
        return 0

    if args.command == "build-overrides":
        _print_artifact(build_overrides_step(args.asof, project_root=args.project_root))
        return 0

    if args.command == "factors":
        _print_artifact(
            factors_step(
                args.asof,
                project_root=args.project_root,
                refresh=args.refresh,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "wacc":
        artifacts, result = wacc_step(
            args.asof,
            project_root=args.project_root,
            refresh_factors=args.refresh_factors,
            source_mode=args.source_mode,
        )
        payload = {k: str(v) for k, v in artifacts.__dict__.items()}
        payload.update(
            {
                "wacc": result.wacc,
                "re_capm": result.re_capm,
                "re_apt": result.re_apt,
                "capm_apt_gap_bps": result.capm_apt_gap_bps,
                "qa_warning": result.qa_warning,
                "apt_is_unstable": result.apt_is_unstable,
            }
        )
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "dcf":
        _print_artifact(
            dcf_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "apv":
        _print_artifact(
            apv_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "residual-income":
        _print_artifact(
            residual_income_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "comps":
        _print_artifact(
            comps_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "tvalue":
        _print_artifact(
            tvalue_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "reverse-dcf":
        _print_artifact(
            reverse_dcf_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "monte-carlo":
        _print_artifact(
            monte_carlo_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "eva":
        _print_artifact(
            eva_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "real-options":
        _print_artifact(
            real_options_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "stress":
        _print_artifact(
            stress_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "ensemble":
        _print_artifact(
            ensemble_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "qa":
        _print_artifact(
            qa_step(
                args.asof,
                project_root=args.project_root,
                refresh_factors=args.refresh_factors,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "report":
        report_path = report_step(
            args.asof,
            project_root=args.project_root,
            refresh_factors=args.refresh_factors,
            source_mode=args.source_mode,
        )
        memo_path = report_path.parent / f"tencent_investment_memo_{args.asof}.md"
        compact_log = report_path.parent / f"tencent_v3_compact_log_{args.asof}.md"
        print(json.dumps({"report": str(report_path), "investment_memo": str(memo_path), "compact_log": str(compact_log)}, indent=2))
        return 0

    if args.command == "backtest":
        _print_artifact(
            backtest_step(
                start=args.start,
                end=args.end,
                freq=args.freq,
                project_root=args.project_root,
                source_mode=args.source_mode,
            )
        )
        return 0

    if args.command == "run-all":
        payload = run_all(
            args.asof,
            project_root=args.project_root,
            refresh=args.refresh,
            source_mode=args.source_mode,
        )
        print(json.dumps(payload, indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
