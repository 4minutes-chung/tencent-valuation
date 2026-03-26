from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .factors import FactorArtifacts
from .paths import ProjectPaths


class WaccError(RuntimeError):
    pass


@dataclass(frozen=True)
class WaccArtifacts:
    wacc_components: Path
    capm_apt_compare: Path
    peer_betas: Path


@dataclass(frozen=True)
class WaccResult:
    asof: str
    wacc: float
    re_capm: float
    re_apt: float
    capm_apt_gap_bps: float
    qa_warning: bool
    apt_is_unstable: bool


@dataclass(frozen=True)
class AptEstimate:
    window_months: int
    re_raw: float
    re_guardrailed: float
    betas_raw: dict[str, float]
    betas_guardrailed: dict[str, float]
    lambdas_sample: dict[str, float]
    lambdas_guardrailed: dict[str, float]
    t_betas: dict[str, float]
    t_lambdas: dict[str, float]
    flags: list[str]


def levered_beta(asset_excess: pd.Series, market_excess: pd.Series) -> float:
    aligned = pd.concat([asset_excess, market_excess], axis=1).dropna()
    if len(aligned) < 20:
        raise WaccError(f"Not enough observations for beta estimate: {len(aligned)}")
    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1], ddof=1)[0, 1]
    var = np.var(aligned.iloc[:, 1], ddof=1)
    if np.isclose(var, 0.0):
        raise WaccError("Market excess variance is zero; beta undefined")
    return float(cov / var)


def unlever_beta(beta_l: float, tax_rate: float, debt_to_equity: float) -> float:
    return float(beta_l / (1.0 + (1.0 - tax_rate) * debt_to_equity))


def relever_beta(beta_u: float, tax_rate: float, debt_to_equity: float) -> float:
    return float(beta_u * (1.0 + (1.0 - tax_rate) * debt_to_equity))


def capm_cost_of_equity(rf_annual: float, beta_l: float, erp_annual: float) -> float:
    return float(rf_annual + beta_l * erp_annual)


def apt_cost_of_equity(rf_annual: float, betas: dict[str, float], lambdas: dict[str, float]) -> float:
    premia = sum(float(betas.get(key, 0.0)) * float(lambdas.get(key, 0.0)) for key in lambdas)
    return float(rf_annual + premia)


def winsorize_series(series: pd.Series, pct: float) -> tuple[pd.Series, bool]:
    if pct <= 0.0:
        return series.copy(), False
    lower = float(series.quantile(pct))
    upper = float(series.quantile(1.0 - pct))
    clipped = series.clip(lower=lower, upper=upper)
    changed = bool((clipped != series).any())
    return clipped, changed


def clamp_beta(beta: float, abs_cap: float) -> tuple[float, bool]:
    clipped = float(np.clip(beta, -abs_cap, abs_cap))
    return clipped, not np.isclose(clipped, beta)


def shrink_and_cap_lambda(sample: float, shrinkage: float, abs_cap: float) -> tuple[float, bool, bool]:
    shrunk = float(shrinkage * sample)
    shrink_changed = not np.isclose(shrunk, sample)
    clipped = float(np.clip(shrunk, -abs_cap, abs_cap))
    cap_changed = not np.isclose(clipped, shrunk)
    return clipped, shrink_changed, cap_changed


def is_apt_unstable(re_capm: float, re_apt_guardrailed: float, unstable_gap_bps: float) -> bool:
    gap = abs(re_capm - re_apt_guardrailed) * 10000.0
    return bool(gap > unstable_gap_bps)


def calc_rd(interest_expense_hkd_bn: float, avg_gross_debt_hkd_bn: float, floor: float, ceiling: float) -> float:
    if avg_gross_debt_hkd_bn <= 0.0:
        return float(floor)
    raw = interest_expense_hkd_bn / avg_gross_debt_hkd_bn
    return float(min(max(raw, floor), ceiling))


def vasicek_adjust(
    beta_raw: float,
    beta_prior: float = 1.0,
    se_beta: float = 0.25,
    prior_variance: float = 0.16,
) -> float:
    """Vasicek (1973) shrinkage: w = prior_var / (prior_var + se_beta^2); beta_adj = w*beta_raw + (1-w)*beta_prior."""
    w = prior_variance / (prior_variance + se_beta ** 2)
    return float(w * beta_raw + (1.0 - w) * beta_prior)


def blume_adjust(beta_raw: float) -> float:
    """Blume (1975) mean-reversion: 0.33 + 0.67 * beta_raw."""
    return float(0.33 + 0.67 * beta_raw)


def _resolve_erp(monthly_window: pd.DataFrame, wacc_config: dict) -> float:
    """Resolve ERP based on erp_method config key."""
    erp_method = str(wacc_config.get("erp_method", "rolling_excess_return")).lower()
    if erp_method == "implied":
        return float(wacc_config.get("implied_erp_default", 0.055))
    elif erp_method == "blend":
        implied = float(wacc_config.get("implied_erp_default", 0.055))
        rolling = float(monthly_window["MKT_EXCESS"].mean() * 12.0)
        return float(0.5 * implied + 0.5 * rolling)
    else:
        # rolling_excess_return (default)
        return float(monthly_window["MKT_EXCESS"].mean() * 12.0)


def _resolve_rf(monthly_window: pd.DataFrame, wacc_config: dict) -> float:
    """Resolve risk-free rate based on rf_method config key."""
    rf_method = str(wacc_config.get("rf_method", "rolling_mean")).lower()
    if rf_method == "current_10y":
        return float(monthly_window["RF"].iloc[-1] * 12.0)
    else:
        # rolling_mean (default)
        return float(monthly_window["RF"].mean() * 12.0)


def _resolve_rd(
    rf_annual: float,
    wacc_config: dict,
    interest_expense: float,
    avg_gross_debt: float,
) -> tuple[float, str]:
    """Resolve cost of debt based on rd_method config key."""
    rd_method = str(wacc_config.get("rd_method", "historical")).lower()
    if rd_method == "synthetic_spread":
        spread = float(wacc_config.get("rd_spread_bps", 150)) / 10000.0
        rd = float(np.clip(
            rf_annual + spread,
            float(wacc_config.get("rd_floor", 0.015)),
            float(wacc_config.get("rd_ceiling", 0.12)),
        ))
        return rd, "synthetic_spread"
    else:
        rd = calc_rd(
            interest_expense,
            avg_gross_debt,
            float(wacc_config.get("rd_floor", 0.015)),
            float(wacc_config.get("rd_ceiling", 0.12)),
        )
        return rd, "historical"


def _fama_macbeth_lambdas(
    monthly_assets_df: pd.DataFrame,
    monthly_factors_df: pd.DataFrame,
    tickers: list[str],
    min_obs: int = 24,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """
    Fama-MacBeth (1973) two-pass lambda estimation.

    Pass 1: Time-series OLS per ticker → beta_mkt, beta_smb, beta_hml.
    Pass 2: Cross-sectional OLS per date → lambda_mkt_t, lambda_smb_t, lambda_hml_t.
    Average lambdas over time, annualize by *12, compute t-stats.

    Returns (lambdas_annual, t_stats, se_annual) each a dict with keys
    'MKT_EXCESS', 'SMB', 'HML'.
    """
    factors_cols = ["date", "RF", "MKT_EXCESS", "SMB", "HML"]
    mf = monthly_factors_df[factors_cols].copy()
    mf["date"] = pd.to_datetime(mf["date"])

    # Pass 1: per-ticker time-series betas
    ticker_betas: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        asset_sub = monthly_assets_df.loc[monthly_assets_df["ticker"] == ticker, ["date", "ret"]].copy()
        asset_sub["date"] = pd.to_datetime(asset_sub["date"])
        merged = asset_sub.merge(mf, on="date", how="inner").dropna()
        if len(merged) < min_obs:
            continue
        excess_ret = merged["ret"] - merged["RF"]
        x = sm.add_constant(merged[["MKT_EXCESS", "SMB", "HML"]])
        fit = sm.OLS(excess_ret, x).fit()
        ticker_betas[ticker] = {
            "MKT_EXCESS": float(fit.params.get("MKT_EXCESS", 0.0)),
            "SMB": float(fit.params.get("SMB", 0.0)),
            "HML": float(fit.params.get("HML", 0.0)),
        }

    if len(ticker_betas) < 3:
        raise WaccError(
            f"Fama-MacBeth requires at least 3 tickers with sufficient data; "
            f"got {len(ticker_betas)} (min_obs={min_obs})"
        )

    # Build panel of betas
    beta_rows = []
    for ticker, betas in ticker_betas.items():
        beta_rows.append({"ticker": ticker, **betas})
    beta_df = pd.DataFrame(beta_rows)

    # Pass 2: cross-sectional regression per date
    # Merge excess returns for each date across tickers
    asset_panel = monthly_assets_df.loc[monthly_assets_df["ticker"].isin(list(ticker_betas.keys()))].copy()
    asset_panel["date"] = pd.to_datetime(asset_panel["date"])
    asset_panel = asset_panel.merge(mf[["date", "RF"]], on="date", how="inner")
    asset_panel["excess_ret"] = asset_panel["ret"] - asset_panel["RF"]
    asset_panel = asset_panel.merge(beta_df, on="ticker", how="inner")

    dates = sorted(asset_panel["date"].unique())
    lambda_series: dict[str, list[float]] = {"MKT_EXCESS": [], "SMB": [], "HML": []}

    for dt in dates:
        sub = asset_panel.loc[asset_panel["date"] == dt].dropna(
            subset=["excess_ret", "MKT_EXCESS", "SMB", "HML"]
        )
        if len(sub) < 3:
            continue
        y_cs = sub["excess_ret"].values
        x_cs = sm.add_constant(sub[["MKT_EXCESS", "SMB", "HML"]].values, has_constant="add")
        try:
            cs_fit = sm.OLS(y_cs, x_cs).fit()
            # params: [const, MKT, SMB, HML]
            if len(cs_fit.params) >= 4:
                lambda_series["MKT_EXCESS"].append(float(cs_fit.params[1]))
                lambda_series["SMB"].append(float(cs_fit.params[2]))
                lambda_series["HML"].append(float(cs_fit.params[3]))
        except Exception:
            continue

    T = len(lambda_series["MKT_EXCESS"])
    if T < 2:
        raise WaccError(f"Fama-MacBeth: not enough time periods for cross-section ({T})")

    lambdas_annual: dict[str, float] = {}
    t_stats: dict[str, float] = {}
    se_annual: dict[str, float] = {}

    for key in ["MKT_EXCESS", "SMB", "HML"]:
        arr = np.array(lambda_series[key])
        mean_m = float(np.mean(arr))
        se_m = float(np.std(arr, ddof=1) / np.sqrt(T))
        lambdas_annual[key] = mean_m * 12.0
        se_annual[key] = se_m * 12.0
        t_stats[key] = float(mean_m / se_m) if se_m > 1e-12 else 0.0

    return lambdas_annual, t_stats, se_annual


def calc_wacc(re: float, debt_to_equity: float, rd: float, tax_rate: float) -> float:
    equity_weight = 1.0 / (1.0 + debt_to_equity)
    debt_weight = debt_to_equity / (1.0 + debt_to_equity)
    return float(equity_weight * re + debt_weight * rd * (1.0 - tax_rate))


def _default_artifacts(paths: ProjectPaths) -> WaccArtifacts:
    return WaccArtifacts(
        wacc_components=paths.data_model / "wacc_components.csv",
        capm_apt_compare=paths.data_model / "capm_apt_compare.csv",
        peer_betas=paths.data_model / "peer_beta_table.csv",
    )


def _safe_tax(market_inputs: pd.DataFrame, ticker: str, default_tax: float) -> float:
    row = market_inputs.loc[market_inputs["ticker"] == ticker]
    if row.empty:
        return float(default_tax)
    val = float(row.iloc[0]["tax_rate"])
    if not np.isfinite(val):
        return float(default_tax)
    return float(val)


def _fit_apt_window(
    merged: pd.DataFrame,
    rf_annual: float,
    wacc_config: dict,
    window_months: int,
) -> AptEstimate:
    min_obs = int(wacc_config.get("apt_min_obs", 36))
    if len(merged) < min_obs:
        raise WaccError(
            f"APT window {window_months}m requires at least {min_obs} observations, found {len(merged)}"
        )

    winsor_pct = float(wacc_config.get("apt_winsor_pct", 0.01))
    beta_abs_cap = float(wacc_config.get("apt_beta_abs_cap", 2.0))
    lambda_shrinkage = float(wacc_config.get("apt_lambda_shrinkage", 0.6))
    lambda_cap_mkt = float(wacc_config.get("apt_lambda_cap_mkt", 0.12))
    lambda_cap_style = float(wacc_config.get("apt_lambda_cap_style", 0.08))
    max_lags = int(wacc_config.get("apt_hac_lags", 3))

    flags: list[str] = []
    y = merged["ret"] - merged["RF"]
    x = merged[["MKT_EXCESS", "SMB", "HML"]].copy()

    winsorized = x.copy()
    winsor_changed = False
    for col in ["MKT_EXCESS", "SMB", "HML"]:
        wins_col, changed = winsorize_series(winsorized[col], winsor_pct)
        winsorized[col] = wins_col
        winsor_changed = winsor_changed or changed
    if winsor_changed:
        flags.append(f"winsorized_factors_{window_months}m")

    x_reg = sm.add_constant(winsorized)
    apt_fit = sm.OLS(y, x_reg).fit(cov_type="HAC", cov_kwds={"maxlags": max_lags})

    raw_betas = {
        "MKT_EXCESS": float(apt_fit.params.get("MKT_EXCESS", 0.0)),
        "SMB": float(apt_fit.params.get("SMB", 0.0)),
        "HML": float(apt_fit.params.get("HML", 0.0)),
    }
    t_betas = {
        "MKT_EXCESS": float(apt_fit.tvalues.get("MKT_EXCESS", 0.0)),
        "SMB": float(apt_fit.tvalues.get("SMB", 0.0)),
        "HML": float(apt_fit.tvalues.get("HML", 0.0)),
    }

    betas: dict[str, float] = {}
    for key, val in raw_betas.items():
        clipped, changed = clamp_beta(val, beta_abs_cap)
        betas[key] = clipped
        if changed:
            flags.append(f"beta_capped_{key.lower()}_{window_months}m")

    lambda_sample = {
        "MKT_EXCESS": float(winsorized["MKT_EXCESS"].mean() * 12.0),
        "SMB": float(winsorized["SMB"].mean() * 12.0),
        "HML": float(winsorized["HML"].mean() * 12.0),
    }

    lambdas: dict[str, float] = {}
    t_lambdas: dict[str, float] = {}
    for key in ["MKT_EXCESS", "SMB", "HML"]:
        cap = lambda_cap_mkt if key == "MKT_EXCESS" else lambda_cap_style
        clipped, shrink_changed, cap_changed = shrink_and_cap_lambda(
            sample=lambda_sample[key],
            shrinkage=lambda_shrinkage,
            abs_cap=cap,
        )
        lambdas[key] = clipped
        t_lambdas[key] = clipped / max(1e-6, abs(clipped) * 0.25)
        if shrink_changed:
            flags.append(f"lambda_shrunk_{key.lower()}_{window_months}m")
        if cap_changed:
            flags.append(f"lambda_capped_{key.lower()}_{window_months}m")

    re_apt_raw = apt_cost_of_equity(rf_annual, raw_betas, lambda_sample)
    re_apt_guardrailed = apt_cost_of_equity(rf_annual, betas, lambdas)

    return AptEstimate(
        window_months=window_months,
        re_raw=re_apt_raw,
        re_guardrailed=re_apt_guardrailed,
        betas_raw=raw_betas,
        betas_guardrailed=betas,
        lambdas_sample=lambda_sample,
        lambdas_guardrailed=lambdas,
        t_betas=t_betas,
        t_lambdas=t_lambdas,
        flags=flags,
    )


def _evaluate_apt_stability(
    primary: AptEstimate,
    windows: list[AptEstimate],
    wacc_config: dict,
) -> tuple[float, bool, dict[str, float], float, int]:
    gap_threshold = float(wacc_config.get("apt_stability_gap_bps", 300.0))
    beta_gap_threshold = float(wacc_config.get("apt_stability_beta_gap", 0.60))
    sign_flip_floor = float(wacc_config.get("apt_stability_sign_flip_floor", 0.15))

    max_gap_bps = 0.0
    max_beta_gap = 0.0
    sign_flips = 0
    details: dict[str, float] = {}

    for estimate in windows:
        if estimate.window_months == primary.window_months:
            continue

        gap_bps = abs(primary.re_guardrailed - estimate.re_guardrailed) * 10000.0
        details[f"gap_vs_{estimate.window_months}m_bps"] = gap_bps
        max_gap_bps = max(max_gap_bps, gap_bps)

        for key in ["MKT_EXCESS", "SMB", "HML"]:
            p = float(primary.betas_guardrailed[key])
            o = float(estimate.betas_guardrailed[key])
            max_beta_gap = max(max_beta_gap, abs(p - o))

            if abs(p) >= sign_flip_floor and abs(o) >= sign_flip_floor and np.sign(p) != np.sign(o):
                sign_flips += 1

    stable = max_gap_bps <= gap_threshold and max_beta_gap <= beta_gap_threshold and sign_flips == 0
    score_gap = 1.0 if gap_threshold <= 0 else max(0.0, 1.0 - (max_gap_bps / gap_threshold))
    score_beta = 1.0 if beta_gap_threshold <= 0 else max(0.0, 1.0 - (max_beta_gap / beta_gap_threshold))
    score_sign = 1.0 if sign_flips == 0 else max(0.0, 1.0 - (0.5 * sign_flips))
    score = float(max(0.0, min(1.0, (score_gap + score_beta + score_sign) / 3.0)))

    details["max_window_gap_bps"] = max_gap_bps
    details["max_beta_gap"] = max_beta_gap
    details["sign_flip_count"] = float(sign_flips)

    return score, (not stable), details, max_beta_gap, sign_flips


def _premia_sanity(
    estimate: AptEstimate,
    wacc_config: dict,
) -> tuple[str, list[str]]:
    warn_mkt = float(wacc_config.get("apt_premia_warn_mkt", 0.10))
    warn_style = float(wacc_config.get("apt_premia_warn_style", 0.06))
    fail_mkt = float(wacc_config.get("apt_premia_fail_mkt", 0.14))
    fail_style = float(wacc_config.get("apt_premia_fail_style", 0.10))

    flags: list[str] = []
    status = "pass"

    for key, value in estimate.lambdas_guardrailed.items():
        value_abs = abs(float(value))
        warn = warn_mkt if key == "MKT_EXCESS" else warn_style
        fail = fail_mkt if key == "MKT_EXCESS" else fail_style

        if value_abs > fail:
            status = "fail"
            flags.append(f"lambda_fail_{key.lower()}")
        elif value_abs > warn:
            if status != "fail":
                status = "warn"
            flags.append(f"lambda_warn_{key.lower()}")

    return status, flags


def _weekly_beta_stability(
    weekly_pivot: pd.DataFrame,
    ticker: str,
    market_ticker: str,
    rf_weekly: float,
    primary_weeks: int,
    secondary_weeks: list[int],
) -> tuple[float, dict[str, float], str]:
    market_excess_full = weekly_pivot[market_ticker] - rf_weekly
    asset_excess_full = weekly_pivot[ticker] - rf_weekly

    beta_primary = levered_beta(asset_excess_full.tail(primary_weeks), market_excess_full.tail(primary_weeks))
    beta_secondary: dict[str, float] = {}
    max_gap = 0.0

    for window in secondary_weeks:
        if window <= 10:
            continue
        asset_slice = asset_excess_full.tail(window)
        market_slice = market_excess_full.tail(window)
        if len(asset_slice.dropna()) < 20 or len(market_slice.dropna()) < 20:
            continue
        beta_window = levered_beta(asset_slice, market_slice)
        beta_secondary[f"{window}w"] = beta_window
        max_gap = max(max_gap, abs(beta_window - beta_primary))

    score = max(0.0, 1.0 - (max_gap / 0.80))
    second_label = ",".join(beta_secondary.keys())
    return float(score), beta_secondary, second_label


def run_wacc(
    asof: str,
    paths: ProjectPaths,
    factor_artifacts: FactorArtifacts,
    peers: list[str],
    wacc_config: dict,
) -> tuple[WaccArtifacts, WaccResult]:
    paths.ensure()
    artifacts = _default_artifacts(paths)

    weekly = pd.read_csv(factor_artifacts.weekly_returns)
    monthly_factors = pd.read_csv(factor_artifacts.monthly_factors)
    monthly_assets = pd.read_csv(factor_artifacts.monthly_asset_returns)
    market_inputs = pd.read_csv(factor_artifacts.market_inputs)

    market_ticker = wacc_config["market_ticker"]
    target_ticker = wacc_config["target_ticker"]

    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly = weekly.sort_values("date")
    weekly_pivot = weekly.pivot(index="date", columns="ticker", values="ret")

    beta_window_weeks = int(wacc_config["beta_window_weeks"])
    weekly_window = weekly_pivot.tail(beta_window_weeks)

    lookback_m = int(wacc_config["erp_lookback_months"])
    monthly_factors = monthly_factors.sort_values("date")
    monthly_window = monthly_factors.tail(lookback_m)

    rf_annual = _resolve_rf(monthly_window, wacc_config)
    rf_method = str(wacc_config.get("rf_method", "rolling_mean")).lower()
    rf_weekly = float(monthly_window["RF"].mean() / 4.345)
    erp_annual = _resolve_erp(monthly_window, wacc_config)
    erp_method = str(wacc_config.get("erp_method", "rolling_excess_return"))

    market_excess = weekly_window[market_ticker] - rf_weekly
    beta_secondary_windows = [int(x) for x in wacc_config.get("beta_secondary_windows_weeks", [156])]
    beta_stability_score, beta_secondary_map, beta_secondary_label = _weekly_beta_stability(
        weekly_pivot=weekly_pivot,
        ticker=target_ticker,
        market_ticker=market_ticker,
        rf_weekly=rf_weekly,
        primary_weeks=beta_window_weeks,
        secondary_weeks=beta_secondary_windows,
    )
    default_tax = float(wacc_config.get("default_tax_rate", 0.20))

    peer_rows: list[dict[str, float | str]] = []
    for peer in peers:
        asset_excess = weekly_window[peer] - rf_weekly
        beta_l = levered_beta(asset_excess, market_excess)

        row = market_inputs.loc[market_inputs["ticker"] == peer]
        if row.empty:
            raise WaccError(f"Missing market_inputs row for peer: {peer}")

        debt = float(row.iloc[0]["gross_debt_hkd_bn"])
        equity = float(row.iloc[0]["market_equity_hkd_bn"])
        if equity <= 0:
            raise WaccError(f"Peer market equity must be positive: {peer}")
        d_e = debt / equity
        tax = _safe_tax(market_inputs, peer, default_tax)
        beta_u = unlever_beta(beta_l, tax, d_e)

        peer_rows.append(
            {
                "asof": asof,
                "ticker": peer,
                "beta_l": beta_l,
                "beta_u": beta_u,
                "tax_rate": tax,
                "debt_to_equity": d_e,
            }
        )

    peer_frame = pd.DataFrame(peer_rows)
    beta_u_target = float(peer_frame["beta_u"].median())
    d_e_target = float(peer_frame["debt_to_equity"].median())

    max_de = float(wacc_config.get("max_de_ratio", 2.0))
    if d_e_target < 0 or d_e_target > max_de:
        raise WaccError(f"Target D/E out of bounds: {d_e_target:.4f}")

    tencent_row = market_inputs.loc[market_inputs["ticker"] == target_ticker]
    if tencent_row.empty:
        raise WaccError(f"Missing market_inputs row for target: {target_ticker}")

    tencent_tax = _safe_tax(market_inputs, target_ticker, default_tax)
    beta_l_tencent = relever_beta(beta_u_target, tencent_tax, d_e_target)

    # Beta adjustment (Vasicek / Blume)
    beta_adjustment = str(wacc_config.get("beta_adjustment", "none")).lower()
    beta_l_adj = beta_l_tencent
    if beta_adjustment == "vasicek":
        beta_l_adj = vasicek_adjust(
            beta_l_tencent,
            beta_prior=float(wacc_config.get("vasicek_prior", 1.0)),
            se_beta=float(wacc_config.get("vasicek_se", 0.25)),
            prior_variance=float(wacc_config.get("vasicek_prior_variance", 0.16)),
        )
    elif beta_adjustment == "blume":
        beta_l_adj = blume_adjust(beta_l_tencent)

    # Country risk premium
    crp = float(wacc_config.get("country_risk_premium", 0.0))

    re_capm = capm_cost_of_equity(rf_annual, beta_l_adj, erp_annual) + crp

    apt_lookback = int(wacc_config["apt_lookback_months"])
    factor_slice = monthly_factors.tail(apt_lookback).copy()
    asset_slice = monthly_assets.loc[monthly_assets["ticker"] == target_ticker].copy()
    merged_all = factor_slice.merge(asset_slice[["date", "ret"]], on="date", how="inner")

    min_obs = int(wacc_config["apt_min_obs"])
    if len(merged_all) < min_obs:
        raise WaccError(f"APT requires at least {min_obs} observations, found {len(merged_all)}")

    guardrail_flags: list[str] = []
    primary_estimate = _fit_apt_window(
        merged=merged_all.tail(apt_lookback),
        rf_annual=rf_annual,
        wacc_config=wacc_config,
        window_months=apt_lookback,
    )
    guardrail_flags.extend(primary_estimate.flags)

    windows_cfg = [int(x) for x in wacc_config.get("apt_stability_windows_months", [24, 36, 60])]
    windows = sorted(set([apt_lookback, *windows_cfg]))
    stability_min_obs = int(wacc_config.get("apt_stability_min_obs", 24))
    window_estimates: list[AptEstimate] = [primary_estimate]

    for win in windows:
        if win == apt_lookback:
            continue
        merged_window = merged_all.tail(win)
        if len(merged_window) < stability_min_obs:
            continue
        if len(merged_window) < min_obs:
            continue
        estimate = _fit_apt_window(
            merged=merged_window,
            rf_annual=rf_annual,
            wacc_config=wacc_config,
            window_months=win,
        )
        window_estimates.append(estimate)
        guardrail_flags.extend(estimate.flags)

    apt_stability_score, unstable_by_windows, stability_details, max_beta_gap, sign_flips = _evaluate_apt_stability(
        primary=primary_estimate,
        windows=window_estimates,
        wacc_config=wacc_config,
    )
    if unstable_by_windows:
        guardrail_flags.append("apt_unstable_windows")
    if max_beta_gap > float(wacc_config.get("apt_stability_beta_gap", 0.60)):
        guardrail_flags.append("apt_unstable_beta_gap")
    if sign_flips > 0:
        guardrail_flags.append("apt_unstable_sign_flip")

    premia_status, premia_flags = _premia_sanity(primary_estimate, wacc_config)
    guardrail_flags.extend(premia_flags)
    if premia_status == "warn":
        guardrail_flags.append("apt_premia_warn")
    if premia_status == "fail":
        guardrail_flags.append("apt_premia_fail")

    re_apt_raw = primary_estimate.re_raw
    re_apt_guardrailed = primary_estimate.re_guardrailed

    debt = float(tencent_row.iloc[0]["gross_debt_hkd_bn"])
    interest_expense = float(tencent_row.iloc[0]["interest_expense_hkd_bn"])
    rd, rd_method = _resolve_rd(rf_annual, wacc_config, interest_expense, debt)

    wacc = calc_wacc(re_capm, d_e_target, rd, tencent_tax)

    gap_bps = abs(re_capm - re_apt_guardrailed) * 10000.0
    gap_raw_bps = abs(re_capm - re_apt_raw) * 10000.0
    gap_limit = float(wacc_config["capm_apt_alert_bps"])
    qa_warning = bool(gap_bps > gap_limit)

    unstable_gap_bps = float(wacc_config.get("apt_unstable_gap_bps", 400.0))
    unstable_by_capm_gap = is_apt_unstable(re_capm, re_apt_guardrailed, unstable_gap_bps)
    apt_is_unstable = bool(unstable_by_capm_gap or unstable_by_windows or premia_status == "fail")
    if unstable_by_capm_gap:
        guardrail_flags.append("apt_unstable_gap")

    unstable_reason_codes: list[str] = []
    if unstable_by_capm_gap:
        unstable_reason_codes.append("capm_apt_gap")
    if unstable_by_windows:
        unstable_reason_codes.append("window_instability")
    if premia_status == "fail":
        unstable_reason_codes.append("premia_fail")
    if beta_stability_score < 0.40:
        unstable_reason_codes.append("beta_window_instability")

    beta_window_primary = f"{beta_window_weeks}w"
    secondary_windows = sorted(
        [estimate.window_months for estimate in window_estimates if estimate.window_months != apt_lookback]
    )
    beta_window_secondary = ",".join(f"{item}m" for item in secondary_windows) if secondary_windows else ""
    if beta_secondary_label:
        beta_window_secondary = (
            f"{beta_window_secondary}|{beta_secondary_label}" if beta_window_secondary else beta_secondary_label
        )

    # Fama-MacBeth lambda override
    lambda_method = str(wacc_config.get("lambda_method", "sample_mean")).lower()
    fm_lambdas_annual: dict[str, float] | None = None
    fm_t_stats: dict[str, float] | None = None
    if lambda_method == "fama_macbeth":
        fm_min_obs = int(wacc_config.get("fm_min_obs", 24))
        try:
            all_tickers = list(monthly_assets["ticker"].unique())
            fm_lambdas_annual, fm_t_stats, _fm_se = _fama_macbeth_lambdas(
                monthly_assets_df=monthly_assets,
                monthly_factors_df=monthly_factors,
                tickers=all_tickers,
                min_obs=fm_min_obs,
            )
        except WaccError as exc:
            warnings.warn(f"Fama-MacBeth lambda estimation failed, falling back to sample mean: {exc}", stacklevel=2)
            fm_lambdas_annual = None
            fm_t_stats = None

    # Resolve final lambda values for components output
    if fm_lambdas_annual is not None:
        out_lambda_mkt = fm_lambdas_annual["MKT_EXCESS"]
        out_lambda_smb = fm_lambdas_annual["SMB"]
        out_lambda_hml = fm_lambdas_annual["HML"]
        out_t_lambda_mkt = fm_t_stats["MKT_EXCESS"] if fm_t_stats else 0.0
        out_t_lambda_smb = fm_t_stats["SMB"] if fm_t_stats else 0.0
        out_t_lambda_hml = fm_t_stats["HML"] if fm_t_stats else 0.0
    else:
        out_lambda_mkt = primary_estimate.lambdas_guardrailed["MKT_EXCESS"]
        out_lambda_smb = primary_estimate.lambdas_guardrailed["SMB"]
        out_lambda_hml = primary_estimate.lambdas_guardrailed["HML"]
        out_t_lambda_mkt = primary_estimate.t_lambdas["MKT_EXCESS"]
        out_t_lambda_smb = primary_estimate.t_lambdas["SMB"]
        out_t_lambda_hml = primary_estimate.t_lambdas["HML"]

    erp_decomposition = json.dumps(
        {
            "rf_annual": rf_annual,
            "market_excess_annual": erp_annual,
            "method": erp_method,
            "lookback_months": lookback_m,
        }
    )

    components = pd.DataFrame(
        [
            {
                "asof": asof,
                "rf_annual": rf_annual,
                "rf_method": rf_method,
                "erp_annual": erp_annual,
                "target_ticker": target_ticker,
                "erp_method": erp_method,
                "erp_decomposition": erp_decomposition,
                "beta_u_target": beta_u_target,
                "beta_l_tencent": beta_l_tencent,
                "beta_adjustment": beta_adjustment,
                "beta_l_adjusted": beta_l_adj,
                "crp": crp,
                "beta_stability_score": beta_stability_score,
                "debt_to_equity_target": d_e_target,
                "tax_rate_tencent": tencent_tax,
                "re_capm": re_capm,
                "re_apt": re_apt_guardrailed,
                "re_apt_raw": re_apt_raw,
                "re_apt_guardrailed": re_apt_guardrailed,
                "rd": rd,
                "rd_method": rd_method,
                "wacc": wacc,
                "capm_apt_gap_bps": gap_bps,
                "capm_apt_gap_raw_bps": gap_raw_bps,
                "qa_warning": qa_warning,
                "apt_is_unstable": apt_is_unstable,
                "apt_premia_status": premia_status,
                "apt_stability_score": apt_stability_score,
                "apt_stability_max_gap_bps": float(stability_details.get("max_window_gap_bps", 0.0)),
                "apt_stability_max_beta_gap": float(stability_details.get("max_beta_gap", 0.0)),
                "apt_stability_sign_flips": int(stability_details.get("sign_flip_count", 0.0)),
                "beta_window_primary": beta_window_primary,
                "beta_window_secondary": beta_window_secondary,
                "apt_window_diagnostics": json.dumps(stability_details),
                "apt_unstable_reason_codes": ";".join(unstable_reason_codes),
                "apt_guardrail_flags": ";".join(dict.fromkeys(guardrail_flags)),
                "apt_beta_mkt": primary_estimate.betas_guardrailed["MKT_EXCESS"],
                "apt_beta_smb": primary_estimate.betas_guardrailed["SMB"],
                "apt_beta_hml": primary_estimate.betas_guardrailed["HML"],
                "lambda_mkt": out_lambda_mkt,
                "lambda_smb": out_lambda_smb,
                "lambda_hml": out_lambda_hml,
                "apt_t_beta_mkt": primary_estimate.t_betas["MKT_EXCESS"],
                "apt_t_beta_smb": primary_estimate.t_betas["SMB"],
                "apt_t_beta_hml": primary_estimate.t_betas["HML"],
                "apt_t_lambda_mkt": out_t_lambda_mkt,
                "apt_t_lambda_smb": out_t_lambda_smb,
                "apt_t_lambda_hml": out_t_lambda_hml,
            }
        ]
    )

    capm_apt = pd.DataFrame(
        [
            {"asof": asof, "model": "CAPM", "cost_of_equity": re_capm, "is_official": True},
            {"asof": asof, "model": "APT_RAW", "cost_of_equity": re_apt_raw, "is_official": False},
            {
                "asof": asof,
                "model": "APT_GUARDRAILED",
                "cost_of_equity": re_apt_guardrailed,
                "is_official": False,
            },
        ]
    )

    peer_frame.to_csv(artifacts.peer_betas, index=False)
    components.to_csv(artifacts.wacc_components, index=False)
    capm_apt.to_csv(artifacts.capm_apt_compare, index=False)

    result = WaccResult(
        asof=asof,
        wacc=wacc,
        re_capm=re_capm,
        re_apt=re_apt_guardrailed,
        capm_apt_gap_bps=gap_bps,
        qa_warning=qa_warning,
        apt_is_unstable=apt_is_unstable,
    )

    return artifacts, result
