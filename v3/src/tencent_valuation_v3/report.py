from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .paths import ProjectPaths


def _load_qa(asof: str, paths: ProjectPaths) -> dict:
    qa_path = paths.reports / f"qa_{asof}.json"
    if not qa_path.exists():
        return {
            "summary": {
                "warnings": "n/a",
                "failures": "n/a",
                "total_checks": "n/a",
                "investor_grade": False,
            },
            "checks": [],
        }
    with qa_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def write_report(asof: str, paths: ProjectPaths) -> Path:
    paths.ensure()
    report_path = paths.reports / f"tencent_valuation_{asof}.md"

    wacc = pd.read_csv(paths.data_model / "wacc_components.csv").iloc[0]
    valuation = pd.read_csv(paths.data_model / "valuation_outputs.csv")
    qa = _load_qa(asof, paths)

    ensemble = _safe_read_csv(paths.data_model / "valuation_ensemble.csv")
    reverse = _safe_read_csv(paths.data_model / "reverse_dcf_outputs.csv")
    tvalue = _safe_read_csv(paths.data_model / "tvalue_company_bridge.csv")

    apt_unstable = bool(wacc.get("apt_is_unstable", False))
    investor_grade = bool(qa.get("summary", {}).get("investor_grade", False))

    lines: list[str] = []
    lines.append(f"# Tencent Valuation V3 Report ({asof})")
    lines.append("")
    lines.append("## WACC Summary")
    lines.append("")
    lines.append(f"- WACC (CAPM official): `{float(wacc['wacc']):.2%}`")
    lines.append(f"- CAPM Re: `{float(wacc['re_capm']):.2%}`")
    lines.append(f"- APT Re (guardrailed, diagnostic): `{float(wacc['re_apt_guardrailed']):.2%}`")
    lines.append(f"- CAPM/APT gap: `{float(wacc['capm_apt_gap_bps']):.1f} bps`")
    lines.append(f"- Beta stability score: `{float(wacc.get('beta_stability_score', float('nan'))):.3f}`")
    lines.append(f"- APT stability score: `{float(wacc.get('apt_stability_score', float('nan'))):.3f}`")
    lines.append(f"- APT unstable reason codes: `{str(wacc.get('apt_unstable_reason_codes', 'none'))}`")
    lines.append(f"- ERP decomposition: `{str(wacc.get('erp_decomposition', '{}'))}`")

    lines.append("")
    lines.append("## Scenario DCF Valuation")
    lines.append("")
    lines.append("| Scenario | Fair Value (HKD/share) | Margin of Safety |")
    lines.append("|---|---:|---:|")
    for _, row in valuation.iterrows():
        lines.append(
            f"| {row['scenario']} | {float(row['fair_value_hkd_per_share']):.2f} | {float(row['margin_of_safety']):.2%} |"
        )

    if not ensemble.empty:
        lines.append("")
        lines.append("## Ensemble Fair Value")
        lines.append("")
        lines.append("| Scenario | Ensemble Fair Value | Min Method | Max Method | Band Width Ratio |")
        lines.append("|---|---:|---:|---:|---:|")
        for _, row in ensemble.iterrows():
            lines.append(
                "| "
                f"{row['scenario']} | {float(row['ensemble_fair_value_hkd_per_share']):.2f} | "
                f"{float(row['method_min_hkd_per_share']):.2f} | {float(row['method_max_hkd_per_share']):.2f} | "
                f"{float(row['band_width_ratio']):.2f} |"
            )

    if not tvalue.empty:
        lines.append("")
        lines.append("## T-Value Company Bridge")
        lines.append("")
        lines.append("| Scenario | Operating | Strategic Inv. | Net Cash | Total Equity | HKD/share |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for _, row in tvalue.iterrows():
            lines.append(
                "| "
                f"{row['scenario']} | {float(row['operating_value_hkd_bn']):.2f} | "
                f"{float(row['strategic_investments_value_hkd_bn']):.2f} | {float(row['net_cash_hkd_bn']):.2f} | "
                f"{float(row['total_equity_value_hkd_bn']):.2f} | {float(row['fair_value_hkd_per_share']):.2f} |"
            )

    if not reverse.empty:
        r = reverse.iloc[0]
        lines.append("")
        lines.append("## Reverse DCF")
        lines.append("")
        lines.append(f"- Implied terminal growth for current price: `{float(r['implied_terminal_g']):.2%}`")
        lines.append(f"- Implied margin shift vs base: `{float(r['implied_margin_shift_bps']):.1f} bps`")
        lines.append(f"- Implied growth shift vs base: `{float(r['implied_growth_shift_bps']):.1f} bps`")

    lines.append("")
    lines.append("## QA Summary")
    lines.append("")
    lines.append(f"- Total checks: `{qa['summary']['total_checks']}`")
    lines.append(f"- Warnings: `{qa['summary']['warnings']}`")
    lines.append(f"- Failures: `{qa['summary'].get('failures', 0)}`")
    lines.append(f"- Investor-grade: `{'YES' if investor_grade else 'NO'}`")

    lines.append("")
    lines.append("## Confidence")
    lines.append("")
    if investor_grade:
        lines.append("- Confidence level: `HIGH`.")
    elif apt_unstable:
        lines.append("- Confidence level: `MEDIUM-LOW` (APT instability and/or QA failures).")
    else:
        lines.append("- Confidence level: `MEDIUM`.")

    lines.append("")
    for item in qa.get("checks", []):
        lines.append(f"- `{item['check']}`: **{item['status']}** - {item['message']}")

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    return report_path


def write_investment_memo(asof: str, paths: ProjectPaths) -> Path:
    paths.ensure()
    memo_path = paths.reports / f"tencent_investment_memo_{asof}.md"

    wacc = pd.read_csv(paths.data_model / "wacc_components.csv").iloc[0]
    valuation = pd.read_csv(paths.data_model / "valuation_outputs.csv")
    qa = _load_qa(asof, paths)

    ensemble = _safe_read_csv(paths.data_model / "valuation_ensemble.csv")

    base = valuation.loc[valuation["scenario"] == "base"].iloc[0]
    bad = valuation.loc[valuation["scenario"] == "bad"].iloc[0]
    extreme = valuation.loc[valuation["scenario"] == "extreme"].iloc[0]

    apt_unstable = bool(wacc.get("apt_is_unstable", False))
    investor_grade = bool(qa.get("summary", {}).get("investor_grade", False))

    lines: list[str] = []
    lines.append(f"# Tencent Investment Memo V3 ({asof})")
    lines.append("")
    lines.append("## Thesis")
    lines.append("")
    lines.append("- Official valuation discount rate remains CAPM-based WACC under MM/Hamada target structure.")
    lines.append("- V3 adds APV, residual income, relative valuation, SOTP/T-value, and reverse DCF cross-checks.")
    if apt_unstable:
        lines.append("- APT diagnostic is unstable and excluded from headline discount-rate decisions.")

    lines.append("")
    lines.append("## Key Assumptions")
    lines.append("")
    lines.append(f"- WACC (official): `{float(wacc['wacc']):.2%}`")
    lines.append(f"- CAPM cost of equity: `{float(wacc['re_capm']):.2%}`")
    lines.append(f"- APT diagnostic cost of equity: `{float(wacc['re_apt_guardrailed']):.2%}`")
    lines.append(f"- Target D/E: `{float(wacc['debt_to_equity_target']):.3f}`")
    lines.append(f"- Beta stability score: `{float(wacc.get('beta_stability_score', float('nan'))):.3f}`")
    lines.append(f"- Investor-grade QA status: `{'PASS' if investor_grade else 'NOT PASS'}`")

    lines.append("")
    lines.append("## DCF Scenario Fair Value")
    lines.append("")
    lines.append("| Scenario | Fair Value (HKD/share) | Margin of Safety |")
    lines.append("|---|---:|---:|")
    for row in [base, bad, extreme]:
        lines.append(
            f"| {row['scenario']} | {float(row['fair_value_hkd_per_share']):.2f} | {float(row['margin_of_safety']):.2%} |"
        )

    if not ensemble.empty:
        lines.append("")
        lines.append("## Ensemble Cross-Check")
        lines.append("")
        for _, row in ensemble.iterrows():
            lines.append(
                f"- {row['scenario']}: ensemble `{float(row['ensemble_fair_value_hkd_per_share']):.2f}` "
                f"(range `{float(row['method_min_hkd_per_share']):.2f}` to `{float(row['method_max_hkd_per_share']):.2f}`)."
            )

    lines.append("")
    lines.append("## Risks")
    lines.append("")
    risk_checks = [item for item in qa.get("checks", []) if item.get("status") in {"warn", "fail"}]
    if risk_checks:
        for item in risk_checks:
            lines.append(f"- {item['check']}: {item['message']}")
    else:
        lines.append("- No QA warnings/failures in this run.")

    lines.append("")
    lines.append("## Decision Checklist")
    lines.append("")
    lines.append("- [ ] Override filing inputs updated for current as-of date.")
    lines.append("- [ ] CAPM inputs reviewed (rf, ERP, beta windows).")
    lines.append("- [ ] Scenario assumptions reviewed against current operating trends.")
    lines.append("- [ ] Position sizing and risk limits documented.")

    with memo_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    return memo_path


def write_compact_log(asof: str, paths: ProjectPaths) -> Path:
    paths.ensure()
    out = paths.reports / f"tencent_v3_compact_log_{asof}.md"

    qa = _load_qa(asof, paths)
    wacc = _safe_read_csv(paths.data_model / "wacc_components.csv")
    ensemble = _safe_read_csv(paths.data_model / "valuation_ensemble.csv")
    report = _safe_read_csv(paths.data_model / "valuation_outputs.csv")

    lines: list[str] = []
    lines.append(f"# Tencent V3 Compact Log ({asof})")
    lines.append("")
    lines.append("## Process")
    lines.append("")
    lines.append("1. fetch")
    lines.append("2. build-overrides")
    lines.append("3. factors")
    lines.append("4. wacc")
    lines.append("5. dcf/apv/residual/comps/tvalue/reverse-dcf")
    lines.append("6. ensemble")
    lines.append("7. qa/report")

    lines.append("")
    lines.append("## Headline Output")
    lines.append("")
    if not report.empty:
        for _, row in report.iterrows():
            lines.append(
                f"- DCF {row['scenario']}: fair `{float(row['fair_value_hkd_per_share']):.2f}` HKD/share, "
                f"MOS `{float(row['margin_of_safety']):.2%}`."
            )
    if not ensemble.empty:
        for _, row in ensemble.iterrows():
            lines.append(
                f"- Ensemble {row['scenario']}: `{float(row['ensemble_fair_value_hkd_per_share']):.2f}` "
                f"(band `{float(row['method_min_hkd_per_share']):.2f}`..`{float(row['method_max_hkd_per_share']):.2f}`)."
            )
    if not wacc.empty:
        w = wacc.iloc[0]
        lines.append(f"- WACC: `{float(w['wacc']):.2%}`; CAPM Re `{float(w['re_capm']):.2%}`; APT unstable `{bool(w.get('apt_is_unstable', False))}`.")

    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append(f"- QA checks: `{qa['summary']['total_checks']}`")
    lines.append(f"- Warnings: `{qa['summary']['warnings']}`")
    lines.append(f"- Failures: `{qa['summary'].get('failures', 0)}`")
    lines.append(f"- Investor grade: `{'YES' if qa['summary'].get('investor_grade') else 'NO'}`")

    lines.append("")
    lines.append("## Known Limits")
    lines.append("")
    lines.append("- Relative valuation peer fundamentals still use proxy anchors unless manually refreshed.")
    lines.append("- APT remains diagnostic and may be unstable across regimes.")

    with out.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return out
