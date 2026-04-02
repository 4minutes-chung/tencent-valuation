from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "model"
FIGURES_ROOT = ROOT / "docs" / "figures"

SCENARIO_ORDER = ["extreme", "bad", "base"]
SCENARIO_LABELS = {"extreme": "Extreme", "bad": "Bad", "base": "Base"}
PALETTE = {
    "base": "#2D6A4F",
    "bad": "#D9A441",
    "extreme": "#B23A48",
    "market": "#1F1F1F",
    "ensemble": "#2B59C3",
    "dcf": "#A16AE8",
}


def _read_csv(name: str) -> pd.DataFrame:
    path = MODEL_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def _latest_asof(df: pd.DataFrame, asof: str | None) -> str:
    if asof:
        return asof
    if "asof" in df.columns:
        series = df["asof"].dropna().astype(str)
        if not series.empty:
            return series.max()
    raise ValueError("Could not infer as-of date. Pass --asof explicitly.")


def _filter_asof(df: pd.DataFrame, asof: str) -> pd.DataFrame:
    if "asof" not in df.columns:
        return df.copy()
    return df[df["asof"].astype(str) == asof].copy()


def _apply_style() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#222222",
            "axes.titleweight": "bold",
            "axes.labelcolor": "#222222",
            "axes.facecolor": "#FAFAFA",
            "figure.facecolor": "#F5F7FB",
            "savefig.facecolor": "#F5F7FB",
            "grid.alpha": 0.25,
            "grid.color": "#6B7280",
            "axes.grid": True,
            "axes.axisbelow": True,
        }
    )


def _save(fig: plt.Figure, out_dir: Path, stem: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_dcf_vs_market(valuation_outputs: pd.DataFrame, out_dir: Path) -> Path:
    df = valuation_outputs.copy()
    df["scenario"] = pd.Categorical(df["scenario"], categories=SCENARIO_ORDER, ordered=True)
    df = df.sort_values("scenario")
    market = float(df["market_price_hkd"].iloc[0])

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    xs = np.arange(len(df))
    colors = [PALETTE[str(s)] for s in df["scenario"]]
    bars = ax.bar(xs, df["fair_value_hkd_per_share"], color=colors, width=0.62, zorder=3)
    ax.axhline(market, color=PALETTE["market"], linestyle="--", linewidth=2.0, label=f"Market ({market:.0f})")
    for bar, mos in zip(bars, df["margin_of_safety"], strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 4,
            f"MoS {mos:.1%}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xticks(xs, [SCENARIO_LABELS[str(s)] for s in df["scenario"]])
    ax.set_ylabel("HKD/share")
    ax.set_title("DCF Fair Value vs Market Price")
    ax.legend(loc="upper right")
    return _save(fig, out_dir, "01_dcf_vs_market")


def _plot_ensemble_vs_dcf(
    valuation_outputs: pd.DataFrame, valuation_ensemble: pd.DataFrame, out_dir: Path
) -> Path:
    dcf = valuation_outputs[["scenario", "fair_value_hkd_per_share"]].rename(
        columns={"fair_value_hkd_per_share": "dcf"}
    )
    ens = valuation_ensemble[valuation_ensemble["scenario"].isin(SCENARIO_ORDER)][
        ["scenario", "ensemble_fair_value_hkd_per_share"]
    ].rename(columns={"ensemble_fair_value_hkd_per_share": "ensemble"})
    df = dcf.merge(ens, on="scenario", how="inner")
    df["scenario"] = pd.Categorical(df["scenario"], categories=SCENARIO_ORDER, ordered=True)
    df = df.sort_values("scenario")

    x = np.arange(len(df))
    w = 0.34
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.bar(x - w / 2, df["dcf"], width=w, color=PALETTE["dcf"], label="DCF")
    ax.bar(x + w / 2, df["ensemble"], width=w, color=PALETTE["ensemble"], label="Ensemble")
    ax.set_xticks(x, [SCENARIO_LABELS[str(s)] for s in df["scenario"]])
    ax.set_ylabel("HKD/share")
    ax.set_title("Scenario Valuation: DCF vs Ensemble")
    ax.legend(loc="upper right")
    return _save(fig, out_dir, "02_ensemble_vs_dcf")


def _plot_method_cross_section(method_outputs: pd.DataFrame, out_dir: Path) -> Path:
    base = method_outputs[method_outputs["scenario"] == "base"].copy()
    base = base.sort_values("fair_value_hkd_per_share")

    fig, ax = plt.subplots(figsize=(10.0, 6.0))
    vals = base["fair_value_hkd_per_share"].to_numpy()
    weights = base["weight"].to_numpy()
    norm = plt.Normalize(float(weights.min()), float(weights.max()))
    colors = plt.cm.viridis(norm(weights))
    bars = ax.barh(base["method"], vals, color=colors, edgecolor="#222222", linewidth=0.4)
    for bar, w in zip(bars, weights, strict=False):
        ax.text(bar.get_width() + 2.0, bar.get_y() + bar.get_height() / 2, f"w={w:.1%}", va="center", fontsize=8)

    ax.set_xlabel("HKD/share")
    ax.set_title("Base Scenario by Method (color = ensemble weight)")
    return _save(fig, out_dir, "03_method_cross_section")


def _plot_capm_apt(capm_apt: pd.DataFrame, wacc_components: pd.DataFrame, out_dir: Path) -> Path:
    ordered = capm_apt.set_index("model").reindex(["CAPM", "APT_RAW", "APT_GUARDRAILED"]).reset_index()
    wacc = float(wacc_components["wacc"].iloc[0])
    gap_bps = float(wacc_components["capm_apt_gap_bps"].iloc[0])

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    colors = ["#375A7F", "#9A6FB0", "#2FA36B"]
    ax.bar(ordered["model"], ordered["cost_of_equity"] * 100.0, color=colors, width=0.6, zorder=3)
    ax.axhline(wacc * 100.0, color="#A83232", linestyle="--", linewidth=2, label=f"WACC {wacc:.2%}")
    ax.set_ylabel("Percent")
    ax.set_title(f"Cost of Equity Diagnostics (CAPM-APT gap: {gap_bps:.0f} bps)")
    ax.legend(loc="upper right")
    return _save(fig, out_dir, "04_capm_apt_diagnostics")


def _plot_monte_carlo_distribution(
    monte_carlo_outputs: pd.DataFrame, valuation_outputs: pd.DataFrame, out_dir: Path
) -> Path:
    market = float(valuation_outputs["market_price_hkd"].iloc[0])
    values = monte_carlo_outputs["fair_value_hkd_per_share"].dropna().to_numpy()
    if values.size == 0:
        raise ValueError("monte_carlo_outputs.csv has no fair_value_hkd_per_share observations.")

    pcts = np.percentile(values, [10, 50, 90])

    fig, ax = plt.subplots(figsize=(10.0, 5.5))
    ax.hist(values, bins=50, color="#5D8AA8", alpha=0.85, edgecolor="#FFFFFF")
    ax.axvline(pcts[0], color="#1C7C54", linestyle=":", linewidth=2, label=f"P10 {pcts[0]:.1f}")
    ax.axvline(pcts[1], color="#0B6E4F", linestyle="-", linewidth=2, label=f"P50 {pcts[1]:.1f}")
    ax.axvline(pcts[2], color="#1C7C54", linestyle=":", linewidth=2, label=f"P90 {pcts[2]:.1f}")
    ax.axvline(market, color=PALETTE["market"], linestyle="--", linewidth=2, label=f"Market {market:.0f}")
    ax.set_xlabel("HKD/share")
    ax.set_ylabel("Simulated count")
    ax.set_title("Monte Carlo Fair-Value Distribution")
    ax.legend(loc="upper right")
    return _save(fig, out_dir, "05_monte_carlo_distribution")


def _plot_stress(valuation_outputs: pd.DataFrame, stress: pd.DataFrame, out_dir: Path) -> Path:
    base_dcf = float(valuation_outputs.loc[valuation_outputs["scenario"] == "base", "fair_value_hkd_per_share"].iloc[0])
    market = float(valuation_outputs["market_price_hkd"].iloc[0])
    df = stress.copy()
    df = df.sort_values("fair_value_hkd_per_share")

    fig, ax = plt.subplots(figsize=(10.0, 5.5))
    bars = ax.bar(df["stress_scenario"], df["fair_value_hkd_per_share"], color="#CD5C5C", width=0.6)
    ax.axhline(base_dcf, color=PALETTE["base"], linestyle="-.", linewidth=2, label=f"Base DCF {base_dcf:.1f}")
    ax.axhline(market, color=PALETTE["market"], linestyle="--", linewidth=2, label=f"Market {market:.0f}")
    for bar, prob in zip(bars, df["probability"], strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 3,
            f"p={prob:.0%}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_ylabel("HKD/share")
    ax.set_title("Stress Scenarios: Fair Value Compression")
    ax.tick_params(axis="x", labelrotation=18)
    ax.legend(loc="upper right")
    return _save(fig, out_dir, "06_stress_scenarios")


def _plot_heatmap(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    val_col: str,
    title: str,
    x_label: str,
    y_label: str,
    stem: str,
    out_dir: Path,
) -> Path:
    pivot = df.pivot(index=row_col, columns=col_col, values=val_col).sort_index().sort_index(axis=1)
    arr = pivot.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(7.6, 6.0))
    im = ax.imshow(arr, cmap="YlGnBu")
    ax.set_xticks(np.arange(pivot.shape[1]), [f"{int(v):+d}" for v in pivot.columns])
    ax.set_yticks(np.arange(pivot.shape[0]), [f"{int(v):+d}" for v in pivot.index])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="HKD/share")

    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f"{arr[i, j]:.1f}", ha="center", va="center", fontsize=8, color="#111111")

    return _save(fig, out_dir, stem)


def _plot_backtest_scatter(points: pd.DataFrame, summary: pd.DataFrame, out_dir: Path) -> Path:
    df = points.dropna(subset=["base_mos", "forward_12m_return"]).copy()

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.scatter(df["base_mos"], df["forward_12m_return"], color="#1f77b4", alpha=0.85, s=42)
    if len(df) >= 2:
        beta, alpha = np.polyfit(df["base_mos"], df["forward_12m_return"], deg=1)
        xs = np.linspace(df["base_mos"].min(), df["base_mos"].max(), 120)
        ax.plot(xs, alpha + beta * xs, color="#B23A48", linewidth=2.0, label=f"OLS slope {beta:.3f}")

    ic12 = float(summary["information_coefficient_12m"].iloc[0])
    hit12 = float(summary["hit_rate_12m"].iloc[0])
    ax.set_title(f"Backtest Signal vs 12M Return (IC={ic12:.3f}, hit={hit12:.0%})")
    ax.set_xlabel("Base margin of safety")
    ax.set_ylabel("Forward 12M return")
    ax.legend(loc="upper left")
    return _save(fig, out_dir, "09_backtest_scatter")


def _plot_regime_breakdown(regime: pd.DataFrame, out_dir: Path) -> Path:
    df = regime.copy().sort_values("hit_rate_12m", ascending=False)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    bars = ax.bar(df["regime"], df["hit_rate_12m"], color=["#4E79A7", "#F28E2B", "#59A14F"])
    for bar, n in zip(bars, df["n_points"], strict=False):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"n={int(n)}", ha="center", va="bottom")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("12M directional hit rate")
    ax.set_title("Backtest by Market Regime")
    return _save(fig, out_dir, "10_regime_breakdown")


def _plot_scenario_paths(assumptions: pd.DataFrame, out_dir: Path) -> Path:
    df = assumptions.copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8), sharex=True)
    for scenario, color in [("base", PALETTE["base"]), ("bad", PALETTE["bad"]), ("extreme", PALETTE["extreme"])]:
        sub = df[df["scenario"] == scenario].sort_values("year")
        ax1.plot(sub["year"], sub["rev_growth"] * 100, marker="o", color=color, label=SCENARIO_LABELS[scenario])
        ax2.plot(sub["year"], sub["ebit_margin"] * 100, marker="o", color=color, label=SCENARIO_LABELS[scenario])

    ax1.set_title("Revenue Growth Path")
    ax1.set_xlabel("Forecast year")
    ax1.set_ylabel("Percent")
    ax2.set_title("EBIT Margin Path")
    ax2.set_xlabel("Forecast year")
    ax2.set_ylabel("Percent")
    ax2.legend(loc="best")
    return _save(fig, out_dir, "11_scenario_paths")


def generate(asof: str | None) -> dict[str, str]:
    valuation_outputs = _read_csv("valuation_outputs.csv")
    asof_value = _latest_asof(valuation_outputs, asof)

    data = {
        "valuation_outputs": _filter_asof(valuation_outputs, asof_value),
        "valuation_ensemble": _filter_asof(_read_csv("valuation_ensemble.csv"), asof_value),
        "valuation_method_outputs": _filter_asof(_read_csv("valuation_method_outputs.csv"), asof_value),
        "wacc_components": _filter_asof(_read_csv("wacc_components.csv"), asof_value),
        "capm_apt_compare": _filter_asof(_read_csv("capm_apt_compare.csv"), asof_value),
        "monte_carlo_outputs": _filter_asof(_read_csv("monte_carlo_outputs.csv"), asof_value),
        "stress_scenario_outputs": _filter_asof(_read_csv("stress_scenario_outputs.csv"), asof_value),
        "sensitivity_wacc_g": _filter_asof(_read_csv("sensitivity_wacc_g.csv"), asof_value),
        "sensitivity_margin_growth": _filter_asof(_read_csv("sensitivity_margin_growth.csv"), asof_value),
        "backtest_summary": _read_csv("backtest_summary.csv"),
        "backtest_points": _read_csv("backtest_point_results.csv"),
        "regime_breakdown": _read_csv("backtest_regime_breakdown.csv"),
        "scenario_assumptions_used": _filter_asof(_read_csv("scenario_assumptions_used.csv"), asof_value),
    }

    out_dir = FIGURES_ROOT / asof_value
    _apply_style()

    generated: dict[str, str] = {}
    generated["dcf_vs_market"] = str(_plot_dcf_vs_market(data["valuation_outputs"], out_dir))
    generated["ensemble_vs_dcf"] = str(
        _plot_ensemble_vs_dcf(data["valuation_outputs"], data["valuation_ensemble"], out_dir)
    )
    generated["method_cross_section"] = str(_plot_method_cross_section(data["valuation_method_outputs"], out_dir))
    generated["capm_apt_diagnostics"] = str(
        _plot_capm_apt(data["capm_apt_compare"], data["wacc_components"], out_dir)
    )
    generated["monte_carlo_distribution"] = str(
        _plot_monte_carlo_distribution(data["monte_carlo_outputs"], data["valuation_outputs"], out_dir)
    )
    generated["stress_scenarios"] = str(
        _plot_stress(data["valuation_outputs"], data["stress_scenario_outputs"], out_dir)
    )
    generated["sensitivity_wacc_g"] = str(
        _plot_heatmap(
            data["sensitivity_wacc_g"],
            row_col="wacc_shift_bps",
            col_col="terminal_g_shift_bps",
            val_col="fair_value_hkd_per_share",
            title="Sensitivity Heatmap: WACC Shift vs Terminal Growth Shift",
            x_label="Terminal growth shift (bps)",
            y_label="WACC shift (bps)",
            stem="07_sensitivity_wacc_g",
            out_dir=out_dir,
        )
    )
    generated["sensitivity_margin_growth"] = str(
        _plot_heatmap(
            data["sensitivity_margin_growth"],
            row_col="margin_shift_bps",
            col_col="growth_shift_bps",
            val_col="fair_value_hkd_per_share",
            title="Sensitivity Heatmap: Margin Shift vs Growth Shift",
            x_label="Growth shift (bps)",
            y_label="Margin shift (bps)",
            stem="08_sensitivity_margin_growth",
            out_dir=out_dir,
        )
    )
    generated["backtest_scatter"] = str(
        _plot_backtest_scatter(data["backtest_points"], data["backtest_summary"], out_dir)
    )
    generated["regime_breakdown"] = str(_plot_regime_breakdown(data["regime_breakdown"], out_dir))
    generated["scenario_paths"] = str(_plot_scenario_paths(data["scenario_assumptions_used"], out_dir))

    manifest_path = out_dir / "manifest.json"
    manifest = {"asof": asof_value, "figures": generated}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    generated["manifest"] = str(manifest_path)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate V4 publication visuals from model outputs.")
    parser.add_argument("--asof", default=None, help="As-of date (YYYY-MM-DD). Defaults to latest in valuation outputs.")
    args = parser.parse_args()

    figures = generate(args.asof)
    print(json.dumps(figures, indent=2))


if __name__ == "__main__":
    main()
