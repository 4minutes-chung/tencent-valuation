from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .dcf import run_valuation
from .factors import fetch_close_series_for_ticker, run_factors
from .paths import ProjectPaths
from .wacc import run_wacc


class BacktestError(RuntimeError):
    pass


@dataclass(frozen=True)
class BacktestArtifacts:
    summary: Path
    point_results: Path


def _bucket_mos(value: float) -> str:
    if value < -0.20:
        return "<-20%"
    if value < 0.0:
        return "-20%..0%"
    if value < 0.20:
        return "0%..20%"
    return ">=20%"


def _bucket_expected_return(bucket: str) -> float:
    mapping = {
        "<-20%": -0.25,
        "-20%..0%": -0.10,
        "0%..20%": 0.10,
        ">=20%": 0.25,
    }
    return float(mapping.get(bucket, 0.0))


def _clip(value: float, abs_cap: float) -> float:
    return float(np.clip(value, -abs_cap, abs_cap))


def _next_price(series: pd.Series, ts: pd.Timestamp) -> float | None:
    later = series.loc[series.index >= ts]
    if later.empty:
        return None
    return float(later.iloc[0])


def _asof_dates(start: str, end: str, freq: str) -> list[str]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts > end_ts:
        raise BacktestError("start must be <= end")
    if freq != "quarterly":
        raise BacktestError("Only quarterly frequency is supported")
    dates = pd.date_range(start=start_ts, end=end_ts, freq="QE")
    if len(dates) == 0:
        dates = pd.DatetimeIndex([end_ts])
    return [d.date().isoformat() for d in dates]


def _working_set_paths(paths: ProjectPaths) -> list[Path]:
    return [
        paths.data_processed / "weekly_returns.csv",
        paths.data_processed / "monthly_factors.csv",
        paths.data_processed / "monthly_asset_returns.csv",
        paths.data_processed / "market_inputs.csv",
        paths.data_processed / "tencent_financials.csv",
        paths.data_processed / "segment_revenue.csv",
        paths.data_model / "wacc_components.csv",
        paths.data_model / "capm_apt_compare.csv",
        paths.data_model / "peer_beta_table.csv",
        paths.data_model / "valuation_outputs.csv",
        paths.data_model / "sensitivity_wacc_g.csv",
        paths.data_model / "sensitivity_margin_growth.csv",
        paths.data_model / "scenario_assumptions_used.csv",
    ]


def _snapshot_files(items: list[Path]) -> dict[Path, bytes | None]:
    snapshot: dict[Path, bytes | None] = {}
    for item in items:
        snapshot[item] = item.read_bytes() if item.exists() else None
    return snapshot


def _restore_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, payload in snapshot.items():
        if payload is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def run_backtest(
    start: str,
    end: str,
    freq: str,
    paths: ProjectPaths,
    wacc_config: dict,
    scenarios_config: dict,
    peers: list[str],
    source_mode: str | None = None,
) -> BacktestArtifacts:
    paths.ensure()
    out_points = paths.data_model / "backtest_point_results.csv"
    out_summary = paths.data_model / "backtest_summary.csv"
    snapshot = _snapshot_files(_working_set_paths(paths))

    asof_dates = _asof_dates(start, end, freq)
    target = str(wacc_config.get("target_ticker", "0700.HK"))
    timeout = int(wacc_config.get("http_timeout_seconds", 20))

    price_series = fetch_close_series_for_ticker(target, asof=end, timeout=timeout)
    if price_series.empty:
        raise BacktestError("No price series available for backtest")

    point_columns = [
        "asof",
        "base_mos",
        "mos_bucket",
        "expected_12m_return_from_bucket",
        "forward_6m_return",
        "forward_12m_return",
        "forward_12m_return_clipped",
        "bucket_abs_error_12m",
        "direction_hit_6m",
        "direction_hit_12m",
    ]
    points: list[dict[str, object]] = []
    realized_return_clip_abs = float(wacc_config.get("backtest_realized_return_clip_abs", 0.60))
    try:
        for asof in asof_dates:
            factor_artifacts = run_factors(
                asof=asof,
                paths=paths,
                peers=peers,
                wacc_config=wacc_config,
                refresh=True,
                source_mode=source_mode,
            )
            wacc_artifacts, _ = run_wacc(
                asof=asof,
                paths=paths,
                factor_artifacts=factor_artifacts,
                peers=peers,
                wacc_config=wacc_config,
            )
            run_valuation(asof, paths, scenarios_config, wacc_artifacts.wacc_components)

            valuation = pd.read_csv(paths.data_model / "valuation_outputs.csv")
            base_row = valuation.loc[valuation["scenario"] == "base"].iloc[0]
            mos_base = float(base_row["margin_of_safety"])

            asof_ts = pd.Timestamp(asof)
            px0 = _next_price(price_series, asof_ts)
            if px0 is None:
                continue
            px6 = _next_price(price_series, asof_ts + pd.DateOffset(months=6))
            px12 = _next_price(price_series, asof_ts + pd.DateOffset(months=12))

            ret6 = None if px6 is None else (px6 / px0) - 1.0
            ret12 = None if px12 is None else (px12 / px0) - 1.0

            hit6 = None if ret6 is None else bool(np.sign(mos_base) == np.sign(ret6))
            hit12 = None if ret12 is None else bool(np.sign(mos_base) == np.sign(ret12))
            mos_bucket = _bucket_mos(mos_base)
            expected_12m = _bucket_expected_return(mos_bucket)
            ret12_clipped = None if ret12 is None else _clip(ret12, realized_return_clip_abs)
            bucket_abs_error = None if ret12_clipped is None else abs(expected_12m - ret12_clipped)

            points.append(
                {
                    "asof": asof,
                    "base_mos": mos_base,
                    "mos_bucket": mos_bucket,
                    "expected_12m_return_from_bucket": expected_12m,
                    "forward_6m_return": ret6,
                    "forward_12m_return": ret12,
                    "forward_12m_return_clipped": ret12_clipped,
                    "bucket_abs_error_12m": bucket_abs_error,
                    "direction_hit_6m": hit6,
                    "direction_hit_12m": hit12,
                }
            )
    finally:
        _restore_files(snapshot)

    point_df = pd.DataFrame(points, columns=point_columns)
    point_df.to_csv(out_points, index=False)

    n_points = len(point_df)
    valid6 = point_df["direction_hit_6m"].dropna() if "direction_hit_6m" in point_df.columns else pd.Series(dtype=float)
    valid12 = (
        point_df["direction_hit_12m"].dropna() if "direction_hit_12m" in point_df.columns else pd.Series(dtype=float)
    )
    cali_raw = pd.Series(dtype=float)
    if n_points > 0 and "forward_12m_return" in point_df.columns:
        cali_raw = (point_df["base_mos"] - point_df["forward_12m_return"]).abs().dropna()
    cali_bucket = (
        point_df["bucket_abs_error_12m"].dropna()
        if n_points > 0 and "bucket_abs_error_12m" in point_df.columns
        else pd.Series(dtype=float)
    )

    summary = pd.DataFrame(
        [
            {
                "start": start,
                "end": end,
                "freq": freq,
                "n_points": int(n_points),
                "hit_rate_6m": float(valid6.mean()) if len(valid6) else np.nan,
                "hit_rate_12m": float(valid12.mean()) if len(valid12) else np.nan,
                "calibration_mae_12m": float(cali_bucket.mean()) if len(cali_bucket) else np.nan,
                "calibration_mae_12m_bucket": float(cali_bucket.mean()) if len(cali_bucket) else np.nan,
                "calibration_mae_12m_raw": float(cali_raw.mean()) if len(cali_raw) else np.nan,
            }
        ]
    )
    summary.to_csv(out_summary, index=False)
    return BacktestArtifacts(summary=out_summary, point_results=out_points)
