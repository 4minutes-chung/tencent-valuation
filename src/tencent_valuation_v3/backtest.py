from __future__ import annotations

import shutil
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_yaml
from .dcf import run_valuation
from .factors import FactorDataError, fetch_close_series_for_ticker, run_factors
from .paths import ProjectPaths, build_paths
from .wacc import run_wacc


class BacktestError(RuntimeError):
    pass


@dataclass(frozen=True)
class BacktestArtifacts:
    summary: Path
    point_results: Path
    regime_breakdown: Path


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

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


def _bucket_interval(bucket: str) -> tuple[float, float]:
    mapping = {
        "<-20%": (-1.0, -0.20),
        "-20%..0%": (-0.20, 0.0),
        "0%..20%": (0.0, 0.20),
        ">=20%": (0.20, 1.0),
    }
    return mapping.get(bucket, (-1.0, 1.0))


def _clip(value: float, abs_cap: float) -> float:
    return float(np.clip(value, -abs_cap, abs_cap))


def _next_price(series: pd.Series, ts: pd.Timestamp) -> float | None:
    later = series.loc[series.index >= ts]
    if later.empty:
        return None
    return float(later.iloc[0])


def _prev_price(series: pd.Series, ts: pd.Timestamp) -> float | None:
    earlier = series.loc[series.index <= ts]
    if earlier.empty:
        return None
    return float(earlier.iloc[-1])


def _annualization_points(index: pd.DatetimeIndex) -> float:
    """Infer points-per-year from observed sampling frequency."""
    if len(index) < 3:
        return 52.0
    deltas = index.to_series().diff().dropna().dt.total_seconds() / 86400.0
    if deltas.empty:
        return 52.0
    step_days = float(deltas.median())
    if step_days <= 2.0:
        return 252.0
    if step_days <= 10.0:
        return 52.0
    if step_days <= 40.0:
        return 12.0
    return max(1.0, 365.25 / step_days)


def _price_series_from_weekly_returns(paths: ProjectPaths, ticker: str) -> pd.Series:
    weekly_path = paths.data_processed / "weekly_returns.csv"
    if not weekly_path.exists():
        raise BacktestError("weekly_returns.csv missing; cannot construct backtest price series")

    weekly = pd.read_csv(weekly_path)
    required = {"date", "ticker", "ret"}
    if not required.issubset(set(weekly.columns)):
        raise BacktestError("weekly_returns.csv missing required columns for backtest price reconstruction")

    block = weekly.loc[weekly["ticker"] == ticker, ["date", "ret"]].copy()
    if block.empty:
        raise BacktestError(f"No weekly return rows for target ticker {ticker}")

    block["date"] = pd.to_datetime(block["date"], errors="coerce")
    block["ret"] = pd.to_numeric(block["ret"], errors="coerce")
    block = block.dropna(subset=["date", "ret"]).sort_values("date")
    if block.empty:
        raise BacktestError(f"No usable weekly return rows for target ticker {ticker}")

    # Reconstruct an index level series from returns; absolute scale is irrelevant for returns.
    index_level = (1.0 + block["ret"].clip(lower=-0.999999)).cumprod() * 100.0
    series = pd.Series(index_level.values, index=block["date"], name=ticker)
    series = series[~series.index.duplicated(keep="last")]
    return series


# ---------------------------------------------------------------------------
# Phase 5D: Enhanced multi-regime classification
# ---------------------------------------------------------------------------

def _classify_regime(series: pd.Series, asof: pd.Timestamp) -> str:
    """Classify market regime at asof into one of: crisis, recovery, bull, bear,
    high_vol, low_vol (or 'unknown' if insufficient data)."""
    # Guard: require a DatetimeIndex and minimum data coverage
    if not isinstance(series.index, pd.DatetimeIndex) or len(series) < 4:
        return "unknown"

    px_now = _prev_price(series, asof)
    if px_now is None or px_now <= 0:
        return "unknown"

    # Require series covers at least 2 months back from asof
    earliest = series.index.min()
    if earliest > asof - pd.DateOffset(months=2):
        return "unknown"

    px_3m = _prev_price(series, asof - pd.DateOffset(months=3))
    px_12m = _prev_price(series, asof - pd.DateOffset(months=12))

    ret_3m = None if (px_3m is None or px_3m <= 0) else (px_now / px_3m) - 1.0
    ret_12m = None if (px_12m is None or px_12m <= 0) else (px_now / px_12m) - 1.0

    # Estimate annualized 12m rolling volatility from the price series
    window_start = asof - pd.DateOffset(months=12)
    sub = series.loc[(series.index >= window_start) & (series.index <= asof)]
    if len(sub) >= 4:
        log_rets = np.log(sub / sub.shift(1)).dropna()
        pts_per_year = _annualization_points(sub.index)
        annualized_vol = float(log_rets.std() * np.sqrt(pts_per_year)) if len(log_rets) >= 3 else 0.0
    else:
        annualized_vol = 0.0

    # 1. Crisis: rapid sharp decline in 3 months
    if ret_3m is not None and ret_3m < -0.20:
        return "crisis"

    # 2. Recovery: positive 3m return after a negative 12m cumulative
    if ret_3m is not None and ret_12m is not None and ret_3m > 0.05 and ret_12m < 0.0:
        return "recovery"

    # 3. High / low volatility regardless of direction
    if annualized_vol > 0.30:
        return "high_vol"
    if 0.0 < annualized_vol < 0.15:
        return "low_vol"

    # 4. Bull / Bear by directional return
    if ret_3m is not None:
        return "bull" if ret_3m >= 0 else "bear"

    return "unknown"


# ---------------------------------------------------------------------------
# Phase 5C: New quantitative metrics
# ---------------------------------------------------------------------------

def _information_coefficient(predicted_mos: pd.Series, realized_return: pd.Series) -> float:
    """Spearman rank correlation (IC) between predicted MoS and realized return."""
    df = pd.DataFrame({"pred": predicted_mos, "real": realized_return}).dropna()
    n = len(df)
    if n < 4:
        return float("nan")
    pred_rank = df["pred"].rank()
    real_rank = df["real"].rank()
    d2 = ((pred_rank - real_rank) ** 2).sum()
    ic = 1.0 - 6.0 * float(d2) / (n * (n * n - 1))
    return float(ic)


def _calibration_slope(predicted: pd.Series, realized: pd.Series) -> tuple[float, float]:
    """OLS slope and intercept. Perfect calibration: slope ≈ 1.0, intercept ≈ 0."""
    df = pd.DataFrame({"x": predicted, "y": realized}).dropna()
    if len(df) < 4:
        return float("nan"), float("nan")
    x = df["x"].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=float)
    cov_xy = float(np.cov(x, y, ddof=1)[0, 1])
    var_x = float(np.var(x, ddof=1))
    if var_x < 1e-12:
        return float("nan"), float("nan")
    slope = cov_xy / var_x
    intercept = float(y.mean()) - slope * float(x.mean())
    return float(slope), float(intercept)


def _rmse(predicted: pd.Series, realized: pd.Series) -> float:
    """Root mean squared error between predicted MoS and realized return."""
    df = pd.DataFrame({"pred": predicted, "real": realized}).dropna()
    if len(df) < 2:
        return float("nan")
    return float(np.sqrt(((df["pred"] - df["real"]) ** 2).mean()))


def _hit_rate_by_quintile(predicted: pd.Series, realized: pd.Series) -> dict[str, float]:
    """Direction accuracy within each quintile of predicted MoS values."""
    df = pd.DataFrame({"pred": predicted, "real": realized}).dropna()
    if len(df) < 5:
        return {f"hit_rate_q{q}": float("nan") for q in range(1, 6)}
    try:
        df["quintile"] = pd.qcut(df["pred"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    except ValueError:
        return {f"hit_rate_q{q}": float("nan") for q in range(1, 6)}
    df["direction_hit"] = (np.sign(df["pred"]) == np.sign(df["real"])).astype(float)
    by_q = df.groupby("quintile", observed=True)["direction_hit"].mean()
    result = {}
    for q in range(1, 6):
        result[f"hit_rate_q{q}"] = float(by_q.get(q, float("nan")))
    return result


def _compute_metrics(df: pd.DataFrame, suffix: str = "") -> dict[str, object]:
    """Compute all backtest metrics for a subset of point_df."""
    suf = f"_{suffix}" if suffix else ""
    out: dict[str, object] = {}
    n = len(df)
    out[f"n_points{suf}"] = int(n)

    valid6 = df["direction_hit_6m"].dropna() if "direction_hit_6m" in df.columns else pd.Series(dtype=float)
    valid12 = df["direction_hit_12m"].dropna() if "direction_hit_12m" in df.columns else pd.Series(dtype=float)
    out[f"hit_rate_6m{suf}"] = float(valid6.mean()) if len(valid6) else float("nan")
    out[f"hit_rate_12m{suf}"] = float(valid12.mean()) if len(valid12) else float("nan")

    cali_bucket = (
        df["bucket_abs_error_12m"].dropna()
        if n > 0 and "bucket_abs_error_12m" in df.columns
        else pd.Series(dtype=float)
    )
    out[f"calibration_mae_12m{suf}"] = float(cali_bucket.mean()) if len(cali_bucket) else float("nan")
    out[f"calibration_mae_12m_bucket{suf}"] = out[f"calibration_mae_12m{suf}"]
    cali_raw = (df["base_mos"] - df["forward_12m_return"]).abs().dropna() if n > 0 else pd.Series(dtype=float)
    out[f"calibration_mae_12m_raw{suf}"] = float(cali_raw.mean()) if len(cali_raw) else float("nan")
    out[f"interval_coverage_12m{suf}"] = (
        float(df["interval_hit_12m"].dropna().mean())
        if n > 0 and "interval_hit_12m" in df.columns
        else float("nan")
    )

    pred = df["base_mos"] if "base_mos" in df.columns else pd.Series(dtype=float)
    ret6 = df["forward_6m_return"] if "forward_6m_return" in df.columns else pd.Series(dtype=float)
    ret12 = df["forward_12m_return"] if "forward_12m_return" in df.columns else pd.Series(dtype=float)

    out[f"information_coefficient_6m{suf}"] = _information_coefficient(pred, ret6)
    out[f"information_coefficient_12m{suf}"] = _information_coefficient(pred, ret12)

    slope12, intercept12 = _calibration_slope(pred, ret12)
    out[f"calibration_slope_12m{suf}"] = slope12
    out[f"calibration_intercept_12m{suf}"] = intercept12
    out[f"rmse_12m{suf}"] = _rmse(pred, ret12)

    quintile_hits = _hit_rate_by_quintile(pred, ret12)
    for k, v in quintile_hits.items():
        out[f"{k}{suf}"] = v

    return out


# ---------------------------------------------------------------------------
# Phase 5B: Vintage config loader (anti-look-ahead bias)
# ---------------------------------------------------------------------------

def _load_vintage_config(asof: str, config_dir: Path, fallback: dict) -> dict:
    """Load scenario config from the matching vintage year.

    Tries the asof year, then walks back up to 7 years. Falls back to the
    provided fallback (current scenarios_config) if no vintage file is found.
    """
    year = int(asof[:4])
    vintages_dir = config_dir / "backtest_vintages"
    for y in range(year, year - 8, -1):
        path = vintages_dir / f"{y}.yaml"
        if path.exists():
            return load_yaml(path)
    return fallback


# ---------------------------------------------------------------------------
# Temp project isolation
# ---------------------------------------------------------------------------

def _make_temp_project(source_paths: ProjectPaths) -> tuple[ProjectPaths, Path]:
    """
    Create an isolated temporary project directory for a single backtest iteration.

    Copies the config directory into a fresh temp tree so the main pipeline's data
    files are never touched during backtest. The caller is responsible for cleaning up
    the returned temp_root with shutil.rmtree().
    """
    temp_root = Path(tempfile.mkdtemp(prefix="tencent_bt_"))
    shutil.copytree(source_paths.config, temp_root / "config")
    processed_src = source_paths.data_processed
    processed_dst = temp_root / "data" / "processed"
    if processed_src.exists():
        shutil.copytree(processed_src, processed_dst)
    raw_src = source_paths.data_raw
    raw_dst = temp_root / "data" / "raw"
    if raw_src.exists():
        shutil.copytree(raw_src, raw_dst)
    (temp_root / "data" / "model").mkdir(parents=True, exist_ok=True)
    (temp_root / "reports").mkdir(parents=True, exist_ok=True)

    temp_paths = build_paths(temp_root)
    temp_paths.ensure()
    return temp_paths, temp_root


def _asof_dates(start: str, end: str, freq: str) -> list[str]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts > end_ts:
        raise BacktestError("start must be <= end")
    if freq == "quarterly":
        dates = pd.date_range(start=start_ts, end=end_ts, freq="QE")
    elif freq == "monthly":
        dates = pd.date_range(start=start_ts, end=end_ts, freq="ME")
    else:
        raise BacktestError(f"Unsupported frequency: {freq!r}. Use 'quarterly' or 'monthly'.")
    if len(dates) == 0:
        dates = pd.DatetimeIndex([end_ts])
    return [d.date().isoformat() for d in dates]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

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
    """
    Rolling backtest for valuation model validation.

    Each historical date is evaluated in a fully isolated temporary directory so that
    the main pipeline's processed/model files are never mutated during the backtest run.
    Uses per-year vintage scenario configs to eliminate look-ahead bias (Phase 5B).

    Supports quarterly and monthly frequency. Computes IC, calibration slope, RMSE,
    and hit-rate-by-quintile metrics (Phase 5C). Classifies market regimes using a
    6-category model (Phase 5D). Reports calibration vs validation OOS split (Phase 5E).
    """
    paths.ensure()
    out_points = paths.data_model / "backtest_point_results.csv"
    out_summary = paths.data_model / "backtest_summary.csv"
    out_regime = paths.data_model / "backtest_regime_breakdown.csv"

    asof_dates = _asof_dates(start, end, freq)
    target = str(wacc_config.get("target_ticker", "0700.HK"))
    timeout = int(wacc_config.get("http_timeout_seconds", 20))

    mode = str(source_mode or wacc_config.get("source_mode", "auto")).strip().lower()
    if mode not in {"auto", "live", "synthetic"}:
        raise BacktestError(f"Invalid source mode for backtest: {mode}")

    price_series: pd.Series
    if mode == "synthetic":
        try:
            price_series = _price_series_from_weekly_returns(paths, target)
        except BacktestError as exc:
            warnings.warn(
                f"Synthetic backtest series unavailable ({exc}); falling back to fetched close prices.",
                RuntimeWarning,
                stacklevel=2,
            )
            price_series = fetch_close_series_for_ticker(target, asof=end, timeout=timeout)
    else:
        try:
            price_series = fetch_close_series_for_ticker(target, asof=end, timeout=timeout)
        except (FactorDataError, pd.errors.EmptyDataError, OSError, ValueError) as exc:
            # Fallback path keeps backtest usable when live price API fails.
            warnings.warn(
                f"Live backtest price fetch failed ({exc}); using reconstructed weekly return index.",
                RuntimeWarning,
                stacklevel=2,
            )
            price_series = _price_series_from_weekly_returns(paths, target)

    if price_series.empty:
        raise BacktestError("No price series available for backtest")

    point_columns = [
        "asof",
        "regime",
        "vintage_year",
        "base_mos",
        "mos_bucket",
        "bucket_return_low_12m",
        "bucket_return_high_12m",
        "expected_12m_return_from_bucket",
        "forward_6m_return",
        "forward_12m_return",
        "forward_12m_return_clipped",
        "bucket_abs_error_12m",
        "interval_hit_12m",
        "direction_hit_6m",
        "direction_hit_12m",
    ]
    points: list[dict[str, object]] = []
    realized_return_clip_abs = float(wacc_config.get("backtest_realized_return_clip_abs", 0.60))

    for asof in asof_dates:
        temp_paths: ProjectPaths | None = None
        temp_root: Path | None = None
        try:
            # Phase 5B: Load vintage config for the asof year to avoid look-ahead bias
            vintage_cfg = _load_vintage_config(asof, paths.config, scenarios_config)
            vintage_year = int(asof[:4])

            # Each iteration runs in a fresh isolated directory — main paths are never touched
            temp_paths, temp_root = _make_temp_project(paths)

            factor_artifacts = run_factors(
                asof=asof,
                paths=temp_paths,
                peers=peers,
                wacc_config=wacc_config,
                refresh=True,
                source_mode=source_mode,
            )
            wacc_artifacts, _ = run_wacc(
                asof=asof,
                paths=temp_paths,
                factor_artifacts=factor_artifacts,
                peers=peers,
                wacc_config=wacc_config,
            )
            run_valuation(asof, temp_paths, vintage_cfg, wacc_artifacts.wacc_components)

            valuation = pd.read_csv(temp_paths.data_model / "valuation_outputs.csv")
            base_row = valuation.loc[valuation["scenario"] == "base"].iloc[0]
            mos_base = float(base_row["margin_of_safety"])

        except Exception as exc:  # noqa: BLE001
            warnings.warn(f"Backtest skipped asof={asof} due to error: {exc}", RuntimeWarning, stacklevel=2)
            continue
        finally:
            if temp_root is not None and temp_root.exists():
                shutil.rmtree(temp_root, ignore_errors=True)

        asof_ts = pd.Timestamp(asof)
        px0 = _prev_price(price_series, asof_ts)
        if px0 is None:
            continue
        px6 = _next_price(price_series, asof_ts + pd.DateOffset(months=6))
        px12 = _next_price(price_series, asof_ts + pd.DateOffset(months=12))

        ret6 = None if px6 is None else (px6 / px0) - 1.0
        ret12 = None if px12 is None else (px12 / px0) - 1.0

        hit6 = None if ret6 is None else bool(np.sign(mos_base) == np.sign(ret6))
        hit12 = None if ret12 is None else bool(np.sign(mos_base) == np.sign(ret12))
        mos_bucket = _bucket_mos(mos_base)
        low12, high12 = _bucket_interval(mos_bucket)
        expected_12m = _bucket_expected_return(mos_bucket)
        ret12_clipped = None if ret12 is None else _clip(ret12, realized_return_clip_abs)
        bucket_abs_error = None if ret12_clipped is None else abs(expected_12m - ret12_clipped)
        interval_hit_12m = None
        if ret12_clipped is not None:
            interval_hit_12m = bool(low12 <= ret12_clipped <= high12)

        # Phase 5D: enhanced regime classification
        regime = _classify_regime(price_series, asof_ts)

        points.append(
            {
                "asof": asof,
                "regime": regime,
                "vintage_year": vintage_year,
                "base_mos": mos_base,
                "mos_bucket": mos_bucket,
                "bucket_return_low_12m": low12,
                "bucket_return_high_12m": high12,
                "expected_12m_return_from_bucket": expected_12m,
                "forward_6m_return": ret6,
                "forward_12m_return": ret12,
                "forward_12m_return_clipped": ret12_clipped,
                "bucket_abs_error_12m": bucket_abs_error,
                "interval_hit_12m": interval_hit_12m,
                "direction_hit_6m": hit6,
                "direction_hit_12m": hit12,
            }
        )

    point_df = pd.DataFrame(points, columns=point_columns)
    point_df.to_csv(out_points, index=False)

    n_points = len(point_df)

    # Phase 5E: out-of-sample split (first 60% = calibration, last 40% = validation)
    if n_points >= 5:
        sorted_asofs = sorted(point_df["asof"].unique())
        cutoff_idx = max(1, int(len(sorted_asofs) * 0.60))
        cutoff_date = sorted_asofs[cutoff_idx - 1]
        calib_df = point_df[point_df["asof"] <= cutoff_date]
        valid_df = point_df[point_df["asof"] > cutoff_date]
    else:
        calib_df = point_df
        valid_df = pd.DataFrame(columns=point_df.columns)

    # Phase 5C: compute all metrics for full, calibration, and validation sets
    full_metrics = _compute_metrics(point_df)
    calib_metrics = _compute_metrics(calib_df, suffix="calibration")
    valid_metrics = _compute_metrics(valid_df, suffix="validation")

    summary_row: dict[str, object] = {"start": start, "end": end, "freq": freq}
    summary_row.update(full_metrics)
    summary_row.update(calib_metrics)
    summary_row.update(valid_metrics)

    pd.DataFrame([summary_row]).to_csv(out_summary, index=False)

    # Regime breakdown with per-regime IC and calibration slope
    regime_rows: list[dict[str, object]] = []
    if n_points > 0 and "regime" in point_df.columns:
        for regime_name, block in point_df.groupby("regime"):
            if block.empty:
                continue
            pred = block["base_mos"]
            ret12 = block["forward_12m_return"] if "forward_12m_return" in block.columns else pd.Series(dtype=float)
            slope, intercept = _calibration_slope(pred, ret12)
            regime_rows.append(
                {
                    "regime": regime_name,
                    "n_points": int(len(block)),
                    "hit_rate_12m": float(block["direction_hit_12m"].dropna().mean())
                    if "direction_hit_12m" in block.columns
                    else float("nan"),
                    "calibration_mae_12m_bucket": float(block["bucket_abs_error_12m"].dropna().mean())
                    if "bucket_abs_error_12m" in block.columns
                    else float("nan"),
                    "interval_coverage_12m": float(block["interval_hit_12m"].dropna().mean())
                    if "interval_hit_12m" in block.columns
                    else float("nan"),
                    "information_coefficient_12m": _information_coefficient(pred, ret12),
                    "calibration_slope_12m": slope,
                    "calibration_intercept_12m": intercept,
                }
            )
    pd.DataFrame(regime_rows).to_csv(out_regime, index=False)

    return BacktestArtifacts(summary=out_summary, point_results=out_points, regime_breakdown=out_regime)
