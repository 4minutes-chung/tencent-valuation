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



def write_report(asof: str, paths: ProjectPaths) -> Path:
    paths.ensure()
    report_path = paths.reports / f"tencent_valuation_{asof}.md"

    wacc = pd.read_csv(paths.data_model / "wacc_components.csv").iloc[0]
    valuation = pd.read_csv(paths.data_model / "valuation_outputs.csv")
    qa = _load_qa(asof, paths)

    apt_unstable = bool(wacc.get("apt_is_unstable", False))
    investor_grade = bool(qa.get("summary", {}).get("investor_grade", False))

    lines: list[str] = []
    lines.append(f"# Tencent Valuation Report ({asof})")
    lines.append("")
    lines.append("## WACC Summary")
    lines.append("")
    lines.append(f"- WACC (CAPM-driven): `{float(wacc['wacc']):.2%}`")
    lines.append(f"- Cost of Equity (CAPM official): `{float(wacc['re_capm']):.2%}`")
    lines.append(f"- Cost of Equity (APT guardrailed, diagnostic): `{float(wacc['re_apt_guardrailed']):.2%}`")
    lines.append(f"- Cost of Equity (APT raw): `{float(wacc['re_apt_raw']):.2%}`")
    lines.append(f"- CAPM/APT gap (guardrailed): `{float(wacc['capm_apt_gap_bps']):.1f} bps`")
    lines.append(f"- CAPM/APT gap (raw): `{float(wacc['capm_apt_gap_raw_bps']):.1f} bps`")
    lines.append(f"- APT unstable gate: `{'TRIGGERED' if apt_unstable else 'NOT TRIGGERED'}`")
    lines.append(f"- APT stability score: `{float(wacc.get('apt_stability_score', float('nan'))):.3f}`")
    lines.append(f"- ERP method: `{str(wacc.get('erp_method', 'n/a'))}`")
    lines.append(f"- Beta window (primary): `{str(wacc.get('beta_window_primary', 'n/a'))}`")
    lines.append(f"- Beta window (secondary): `{str(wacc.get('beta_window_secondary', 'n/a')) or 'none'}`")
    lines.append(f"- APT guardrail flags: `{str(wacc.get('apt_guardrail_flags', '')) or 'none'}`")
    lines.append(f"- Target D/E: `{float(wacc['debt_to_equity_target']):.3f}`")
    if apt_unstable:
        lines.append("- Headline valuation policy: `APT excluded; CAPM remains official discount-rate anchor.`")

    lines.append("")
    lines.append("## Scenario Valuation")
    lines.append("")
    lines.append("| Scenario | Fair Value (HKD/share) | Margin of Safety |")
    lines.append("|---|---:|---:|")
    for _, row in valuation.iterrows():
        lines.append(
            f"| {row['scenario']} | {float(row['fair_value_hkd_per_share']):.2f} | {float(row['margin_of_safety']):.2%} |"
        )

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
        lines.append("- Confidence level: `HIGH` (no QA failures and investor-grade gate passed).")
    elif apt_unstable:
        lines.append("- Confidence level: `MEDIUM-LOW` (APT instability and/or QA failures present).")
    else:
        lines.append("- Confidence level: `MEDIUM` (CAPM valuation usable, but QA gaps remain).")
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

    base = valuation.loc[valuation["scenario"] == "base"].iloc[0]
    bad = valuation.loc[valuation["scenario"] == "bad"].iloc[0]
    extreme = valuation.loc[valuation["scenario"] == "extreme"].iloc[0]

    apt_unstable = bool(wacc.get("apt_is_unstable", False))
    investor_grade = bool(qa.get("summary", {}).get("investor_grade", False))

    lines: list[str] = []
    lines.append(f"# Tencent Investment Memo ({asof})")
    lines.append("")
    lines.append("## Thesis")
    lines.append("")
    lines.append("- Tencent valuation is based on a CAPM-anchored WACC with peer-target leverage under MM/Hamada logic.")
    lines.append("- Scenario valuation is decision-framed as base / bad / extreme for downside-aware position sizing.")
    if apt_unstable:
        lines.append(
            "- APT diagnostic is unstable for this run and is excluded from headline discount-rate decisions."
        )
    else:
        lines.append("- APT diagnostic is within stability threshold and retained as a secondary cross-check.")

    lines.append("")
    lines.append("## Key Assumptions")
    lines.append("")
    lines.append(f"- WACC (official): `{float(wacc['wacc']):.2%}`")
    lines.append(f"- Cost of Equity (CAPM): `{float(wacc['re_capm']):.2%}`")
    lines.append(f"- Risk-free annualized: `{float(wacc['rf_annual']):.2%}`")
    lines.append(f"- ERP annualized: `{float(wacc['erp_annual']):.2%}`")
    lines.append(f"- Target D/E: `{float(wacc['debt_to_equity_target']):.3f}`")
    lines.append(f"- APT stability score: `{float(wacc.get('apt_stability_score', float('nan'))):.3f}`")
    lines.append(f"- Investor-grade QA status: `{'PASS' if investor_grade else 'NOT PASS'}`")

    lines.append("")
    lines.append("## Scenario Fair Value")
    lines.append("")
    lines.append("| Scenario | Fair Value (HKD/share) | Margin of Safety |")
    lines.append("|---|---:|---:|")
    for row in [base, bad, extreme]:
        lines.append(
            f"| {row['scenario']} | {float(row['fair_value_hkd_per_share']):.2f} | {float(row['margin_of_safety']):.2%} |"
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
    lines.append("## Confidence")
    lines.append("")
    if investor_grade:
        lines.append("- Overall confidence: HIGH.")
    elif apt_unstable:
        lines.append("- Overall confidence: MEDIUM-LOW (APT instability and QA gaps require conservative sizing).")
    else:
        lines.append("- Overall confidence: MEDIUM (valuation is usable but not investor-grade).")

    lines.append("")
    lines.append("## Decision Checklist")
    lines.append("")
    lines.append("- [ ] Override filing inputs updated for current as-of date.")
    lines.append("- [ ] CAPM inputs reviewed (rf, ERP, beta window).")
    lines.append("- [ ] Scenario assumptions reviewed against current operating trends.")
    lines.append("- [ ] Position sizing and risk limits documented.")

    with memo_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    return memo_path
