from __future__ import annotations

import argparse
import json
from typing import Sequence

from .pipeline import (
    backtest_step,
    build_overrides_step,
    fetch_step,
    factors_step,
    qa_step,
    report_step,
    run_all,
    value_step,
    wacc_step,
)



def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tencent-valuation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch raw web snapshots into data/raw/<asof>")
    fetch.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    fetch.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")

    build_overrides = subparsers.add_parser("build-overrides", help="Build filing-derived TTM override pack")
    build_overrides.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    build_overrides.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")

    factors = subparsers.add_parser("factors", help="Build/validate factor and market inputs")
    factors.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    factors.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
    factors.add_argument("--refresh", action="store_true", help="Regenerate factor snapshots")
    factors.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default=None,
        help="Input source mode override",
    )

    wacc = subparsers.add_parser("wacc", help="Run MM + CAPM/APT WACC engine")
    wacc.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    wacc.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
    wacc.add_argument("--refresh-factors", action="store_true", help="Regenerate factor inputs")
    wacc.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default=None,
        help="Input source mode override",
    )

    value = subparsers.add_parser("value", help="Run 3-scenario DCF valuation")
    value.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    value.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
    value.add_argument("--refresh-factors", action="store_true", help="Regenerate factor inputs")
    value.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default=None,
        help="Input source mode override",
    )

    qa = subparsers.add_parser("qa", help="Run QA checks")
    qa.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    qa.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
    qa.add_argument("--refresh-factors", action="store_true", help="Regenerate factor inputs")
    qa.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default=None,
        help="Input source mode override",
    )

    report = subparsers.add_parser("report", help="Build markdown report")
    report.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    report.add_argument("--asof", required=True, help="As-of date (YYYY-MM-DD)")
    report.add_argument("--refresh-factors", action="store_true", help="Regenerate factor inputs")
    report.add_argument(
        "--source-mode",
        choices=["auto", "live", "synthetic"],
        default=None,
        help="Input source mode override",
    )

    backtest = subparsers.add_parser("backtest", help="Run quarterly backtest")
    backtest.add_argument("--project-root", default=".", help="Project root (default: current directory)")
    backtest.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    backtest.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    backtest.add_argument("--freq", default="quarterly", choices=["quarterly"], help="Backtest frequency")
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



def main(argv: Sequence[str] | None = None) -> int:
    parser = _base_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        artifacts = fetch_step(args.asof, project_root=args.project_root)
        print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))
        return 0

    if args.command == "build-overrides":
        artifacts = build_overrides_step(args.asof, project_root=args.project_root)
        print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))
        return 0

    if args.command == "factors":
        artifacts = factors_step(
            args.asof,
            project_root=args.project_root,
            refresh=args.refresh,
            source_mode=args.source_mode,
        )
        print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))
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

    if args.command == "value":
        artifacts = value_step(
            args.asof,
            project_root=args.project_root,
            refresh_factors=args.refresh_factors,
            source_mode=args.source_mode,
        )
        print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))
        return 0

    if args.command == "qa":
        artifacts = qa_step(
            args.asof,
            project_root=args.project_root,
            refresh_factors=args.refresh_factors,
            source_mode=args.source_mode,
        )
        print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))
        return 0

    if args.command == "report":
        report_path = report_step(
            args.asof,
            project_root=args.project_root,
            refresh_factors=args.refresh_factors,
            source_mode=args.source_mode,
        )
        memo_path = report_path.parent / f"tencent_investment_memo_{args.asof}.md"
        print(json.dumps({"report": str(report_path), "investment_memo": str(memo_path)}, indent=2))
        return 0

    if args.command == "backtest":
        artifacts = backtest_step(
            start=args.start,
            end=args.end,
            freq=args.freq,
            project_root=args.project_root,
            source_mode=args.source_mode,
        )
        print(json.dumps({k: str(v) for k, v in artifacts.__dict__.items()}, indent=2))
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
