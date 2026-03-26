from __future__ import annotations

import hashlib
import io
import json
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from .paths import ProjectPaths


@dataclass(frozen=True)
class FactorArtifacts:
    weekly_returns: Path
    monthly_factors: Path
    monthly_asset_returns: Path
    market_inputs: Path
    tencent_financials: Path
    segment_revenue: Path


class FactorDataError(RuntimeError):
    pass


REQUIRED_TENCENT_FINANCIAL_COLS = {
    "asof",
    "revenue_hkd_bn",
    "ebit_margin",
    "capex_pct_revenue",
    "nwc_pct_revenue",
    "dep_pct_revenue",
    "net_cash_hkd_bn",
    "shares_out_bn",
    "current_price_hkd",
}

REQUIRED_SEGMENT_COLS = {"period", "segment", "revenue_hkd_bn", "total_revenue_hkd_bn"}
REQUIRED_PEER_FUNDAMENTALS_COLS = {
    "ticker",
    "gross_debt_hkd_bn",
    "interest_expense_hkd_bn_3y_avg",
    "effective_tax_rate_3y_avg",
    "shares_out_bn",
}



def _seed_from_asof(asof: str) -> int:
    digest = hashlib.sha256(asof.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32)



def _parse_asof(asof: str) -> pd.Timestamp:
    ts = pd.Timestamp(asof)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts.normalize()



def _http_get_bytes(url: str, timeout: int) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read()



def _read_csv_http(url: str, timeout: int) -> pd.DataFrame:
    payload = _http_get_bytes(url, timeout=timeout)
    return pd.read_csv(io.BytesIO(payload))



def _stooq_symbol(ticker: str) -> str:
    upper = ticker.upper()
    if upper == "HSI":
        return "%5Ehsi"
    if upper.endswith(".HK"):
        code = upper.split(".")[0]
        try:
            code = str(int(code))
        except ValueError:
            code = code.lower()
        return f"{code}.hk"
    return upper.lower()



def _fetch_stooq_close_series(ticker: str, asof: pd.Timestamp, timeout: int) -> pd.Series:
    symbol = _stooq_symbol(ticker)
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    frame = _read_csv_http(url, timeout=timeout)

    if "No data" in frame.columns:
        raise FactorDataError(f"No Stooq data for ticker {ticker} ({symbol})")

    required = {"Date", "Close"}
    if not required.issubset(frame.columns):
        raise FactorDataError(f"Stooq response missing columns for {ticker}: {sorted(required - set(frame.columns))}")

    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
    frame = frame.loc[frame["Date"] <= asof, ["Date", "Close"]]

    if frame.empty:
        raise FactorDataError(f"No usable Stooq rows up to {asof.date()} for {ticker}")

    series = pd.Series(frame["Close"].astype(float).values, index=frame["Date"], name=ticker)
    series = series[~series.index.duplicated(keep="last")]
    return series



def _prices_to_weekly_returns(prices: dict[str, pd.Series]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker, series in prices.items():
        weekly = series.resample("W-FRI").last().pct_change().dropna()
        for date, ret in weekly.items():
            rows.append({"date": date.date().isoformat(), "ticker": ticker, "ret": float(ret)})
    return pd.DataFrame(rows)



def _prices_to_monthly_returns(prices: dict[str, pd.Series]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker, series in prices.items():
        monthly = series.resample("ME").last().pct_change().dropna()
        for date, ret in monthly.items():
            rows.append({"date": date.date().isoformat(), "ticker": ticker, "ret": float(ret)})
    return pd.DataFrame(rows)



def _fetch_ken_french_factors(url: str, timeout: int) -> pd.DataFrame:
    payload = _http_get_bytes(url, timeout=timeout)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
        if not names:
            raise FactorDataError("Ken French ZIP has no files")
        text = zf.read(names[0]).decode("latin-1")

    lines = [line.strip() for line in text.splitlines()]

    data_start: int | None = None
    for idx, line in enumerate(lines):
        if line.startswith(",Mkt-RF") or line.startswith("Mkt-RF"):
            data_start = idx + 1
            break
    if data_start is None:
        raise FactorDataError("Could not find Ken French monthly header")

    rows: list[tuple[str, float, float, float, float]] = []
    for line in lines[data_start:]:
        if not line:
            continue
        first_token = line.split(",", 1)[0].strip()
        if not first_token.isdigit() or len(first_token) != 6:
            # Reached annual block or footer.
            if rows:
                break
            continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            continue

        yyyymm = parts[0]
        try:
            mkt_excess = float(parts[1]) / 100.0
            smb = float(parts[2]) / 100.0
            hml = float(parts[3]) / 100.0
            rf = float(parts[4]) / 100.0
        except ValueError:
            continue

        date = pd.to_datetime(yyyymm + "01", format="%Y%m%d", errors="coerce")
        if pd.isna(date):
            continue
        date = date + pd.offsets.MonthEnd(0)

        rows.append((date.date().isoformat(), mkt_excess, smb, hml, rf))

    if not rows:
        raise FactorDataError("No monthly rows parsed from Ken French factor file")

    out = pd.DataFrame(rows, columns=["date", "MKT_EXCESS", "SMB", "HML", "RF"])
    out = out.sort_values("date").reset_index(drop=True)
    return out



def _fetch_treasury_10y_monthly(asof: pd.Timestamp, years_back: int, timeout: int) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    start_year = max(1990, asof.year - years_back)
    for year in range(start_year, asof.year + 1):
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        )
        try:
            frame = _read_csv_http(url, timeout=timeout)
        except Exception:
            continue
        if "Date" not in frame.columns or "10 Yr" not in frame.columns:
            continue
        frame = frame[["Date", "10 Yr"]].copy()
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        frame["10 Yr"] = pd.to_numeric(frame["10 Yr"], errors="coerce")
        frame = frame.dropna(subset=["Date", "10 Yr"])
        if frame.empty:
            continue
        frames.append(frame)

    if not frames:
        raise FactorDataError("Could not fetch Treasury 10Y yield history")

    daily = pd.concat(frames, ignore_index=True)
    daily = daily.drop_duplicates(subset=["Date"]).sort_values("Date")
    daily = daily.loc[daily["Date"] <= asof]
    # Convert annualized 10Y yield into an approximate monthly risk-free return.
    monthly = daily.set_index("Date")["10 Yr"].resample("ME").mean().dropna() / 100.0 / 12.0

    out = pd.DataFrame({"date": monthly.index.date.astype(str), "RF_TSY": monthly.values})
    return out



def _merge_factor_rf_with_treasury(
    factors: pd.DataFrame,
    asof: pd.Timestamp,
    timeout: int,
    years_back: int,
) -> pd.DataFrame:
    treasury = _fetch_treasury_10y_monthly(asof=asof, years_back=years_back, timeout=timeout)
    merged = factors.merge(treasury, on="date", how="left")
    merged["RF"] = merged["RF_TSY"].fillna(merged["RF"])
    merged = merged.drop(columns=["RF_TSY"])
    return merged



def validate_ticker_coverage(
    frame: pd.DataFrame,
    required_tickers: list[str],
    min_obs: int,
    ticker_col: str = "ticker",
    value_col: str = "ret",
) -> None:
    missing: list[str] = []
    short: list[str] = []
    for ticker in required_tickers:
        block = frame.loc[frame[ticker_col] == ticker, value_col].dropna()
        if block.empty:
            missing.append(ticker)
        elif len(block) < min_obs:
            short.append(f"{ticker} ({len(block)})")

    if missing or short:
        parts: list[str] = []
        if missing:
            parts.append(f"missing: {', '.join(sorted(missing))}")
        if short:
            parts.append(f"insufficient observations: {', '.join(sorted(short))}")
        raise FactorDataError("Ticker coverage failed - " + " | ".join(parts))



def _generate_weekly_returns(
    asof: pd.Timestamp,
    tickers: list[str],
    market_ticker: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    dates = pd.date_range(end=asof, periods=130, freq="W-FRI")
    market = rng.normal(loc=0.0011, scale=0.027, size=len(dates))

    beta_hint = {
        "0700.HK": 1.05,
        "9988.HK": 1.08,
        "3690.HK": 1.18,
        "9999.HK": 0.98,
        "9618.HK": 1.12,
        "9888.HK": 1.10,
    }

    rows: list[dict[str, object]] = []
    for ticker in tickers:
        if ticker == market_ticker:
            returns = market + rng.normal(0.0, 0.003, size=len(dates))
        else:
            beta = beta_hint.get(ticker, float(rng.uniform(0.8, 1.2)))
            alpha = float(rng.normal(0.00005, 0.0002))
            noise = rng.normal(0.0, 0.019, size=len(dates))
            returns = alpha + beta * market + noise

        for date, ret in zip(dates, returns, strict=True):
            rows.append({"date": date.date().isoformat(), "ticker": ticker, "ret": float(ret)})

    return pd.DataFrame(rows)



def _generate_monthly_factors(asof: pd.Timestamp, rng: np.random.Generator) -> pd.DataFrame:
    dates = pd.date_range(end=asof, periods=120, freq="ME")
    rf = np.clip(rng.normal(0.0022, 0.00025, size=len(dates)), 0.0005, None)
    mkt = rng.normal(0.0050, 0.040, size=len(dates))
    smb = rng.normal(0.0012, 0.026, size=len(dates))
    hml = rng.normal(0.0008, 0.023, size=len(dates))

    frame = pd.DataFrame(
        {
            "date": dates.date.astype(str),
            "RF": rf,
            "MKT_EXCESS": mkt,
            "SMB": smb,
            "HML": hml,
        }
    )
    return frame



def _generate_monthly_asset_returns(
    monthly_factors: pd.DataFrame,
    tickers: list[str],
    market_ticker: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    exposures = {
        "0700.HK": (1.03, 0.28, -0.12),
        "9988.HK": (1.10, 0.35, -0.16),
        "3690.HK": (1.22, 0.48, -0.08),
        "9999.HK": (0.95, 0.20, -0.20),
        "9618.HK": (1.15, 0.40, -0.05),
        "9888.HK": (1.07, 0.37, -0.10),
    }

    rows: list[dict[str, object]] = []
    for ticker in tickers:
        if ticker == market_ticker:
            total = monthly_factors["RF"] + monthly_factors["MKT_EXCESS"] + rng.normal(
                0.0, 0.01, size=len(monthly_factors)
            )
        else:
            b_mkt, b_smb, b_hml = exposures.get(ticker, (1.0, 0.2, -0.1))
            eps = rng.normal(0.0, 0.02, size=len(monthly_factors))
            excess = (
                b_mkt * monthly_factors["MKT_EXCESS"]
                + b_smb * monthly_factors["SMB"]
                + b_hml * monthly_factors["HML"]
                + eps
            )
            total = monthly_factors["RF"] + excess

        for date, ret in zip(monthly_factors["date"], total, strict=True):
            rows.append({"date": date, "ticker": ticker, "ret": float(ret)})

    return pd.DataFrame(rows)



def _generate_market_inputs(tickers: list[str]) -> pd.DataFrame:
    defaults = {
        "0700.HK": {
            "tax_rate": 0.20,
            "gross_debt_hkd_bn": 350.0,
            "market_equity_hkd_bn": 3200.0,
            "interest_expense_hkd_bn": 12.0,
            "current_price_hkd": 300.0,
        },
        "9988.HK": {
            "tax_rate": 0.18,
            "gross_debt_hkd_bn": 170.0,
            "market_equity_hkd_bn": 1700.0,
            "interest_expense_hkd_bn": 7.0,
            "current_price_hkd": 74.0,
        },
        "3690.HK": {
            "tax_rate": 0.19,
            "gross_debt_hkd_bn": 120.0,
            "market_equity_hkd_bn": 720.0,
            "interest_expense_hkd_bn": 6.0,
            "current_price_hkd": 112.0,
        },
        "9999.HK": {
            "tax_rate": 0.21,
            "gross_debt_hkd_bn": 90.0,
            "market_equity_hkd_bn": 380.0,
            "interest_expense_hkd_bn": 4.0,
            "current_price_hkd": 132.0,
        },
        "9618.HK": {
            "tax_rate": 0.20,
            "gross_debt_hkd_bn": 110.0,
            "market_equity_hkd_bn": 460.0,
            "interest_expense_hkd_bn": 5.0,
            "current_price_hkd": 101.0,
        },
        "9888.HK": {
            "tax_rate": 0.19,
            "gross_debt_hkd_bn": 95.0,
            "market_equity_hkd_bn": 410.0,
            "interest_expense_hkd_bn": 4.3,
            "current_price_hkd": 80.0,
        },
        "HSI": {
            "tax_rate": 0.20,
            "gross_debt_hkd_bn": 0.0,
            "market_equity_hkd_bn": 1.0,
            "interest_expense_hkd_bn": 0.0,
            "current_price_hkd": 18000.0,
        },
    }

    rows: list[dict[str, object]] = []
    for ticker in tickers:
        payload = defaults.get(ticker)
        if payload is None:
            continue
        row = {"ticker": ticker}
        row.update(payload)
        rows.append(row)

    return pd.DataFrame(rows)



def _generate_tencent_financials(asof: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asof": asof,
                "revenue_hkd_bn": 675.0,
                "ebit_margin": 0.36,
                "capex_pct_revenue": 0.09,
                "nwc_pct_revenue": 0.02,
                "dep_pct_revenue": 0.03,
                "net_cash_hkd_bn": 102.4,
                "shares_out_bn": 9.2,
                "current_price_hkd": 300.0,
            }
        ]
    )



def _generate_segment_revenue(asof: str, total_revenue_hkd_bn: float) -> pd.DataFrame:
    splits = {
        "VAS": 0.34,
        "Marketing Services": 0.21,
        "FinTech and Business Services": 0.41,
        "Other": 0.04,
    }
    rows: list[dict[str, object]] = []
    for segment, ratio in splits.items():
        rows.append(
            {
                "period": asof,
                "segment": segment,
                "revenue_hkd_bn": total_revenue_hkd_bn * ratio,
                "total_revenue_hkd_bn": total_revenue_hkd_bn,
            }
        )
    return pd.DataFrame(rows)



def _read_override_if_valid(path: Path, required_cols: set[str]) -> pd.DataFrame | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    missing = required_cols.difference(frame.columns)
    if missing:
        raise FactorDataError(f"Override file missing columns at {path}: {sorted(missing)}")
    return frame



def _apply_peer_fundamentals_overrides(
    market_inputs: pd.DataFrame,
    asof: str,
    paths: ProjectPaths,
) -> tuple[pd.DataFrame, str]:
    raw_path = paths.data_raw / asof / "peer_fundamentals.csv"
    frame = _read_override_if_valid(raw_path, REQUIRED_PEER_FUNDAMENTALS_COLS)
    if frame is None or frame.empty:
        out = market_inputs.copy()
        out["peer_input_source"] = "default_market_inputs"
        return out, "default_market_inputs"

    out = market_inputs.copy()
    out["peer_input_source"] = "mixed"

    for _, row in frame.iterrows():
        ticker = str(row["ticker"])
        mask = out["ticker"] == ticker
        if not mask.any():
            continue
        out.loc[mask, "gross_debt_hkd_bn"] = float(row["gross_debt_hkd_bn"])
        out.loc[mask, "interest_expense_hkd_bn"] = float(row["interest_expense_hkd_bn_3y_avg"])
        out.loc[mask, "tax_rate"] = float(row["effective_tax_rate_3y_avg"])

        shares_out = float(row["shares_out_bn"])
        current_price = float(out.loc[mask, "current_price_hkd"].iloc[0])
        out.loc[mask, "market_equity_hkd_bn"] = shares_out * current_price
        out.loc[mask, "peer_input_source"] = "peer_fundamentals_csv"

        if "source_doc" in frame.columns:
            out.loc[mask, "peer_source_doc"] = str(row.get("source_doc", ""))
        if "source_date" in frame.columns:
            out.loc[mask, "peer_source_date"] = str(row.get("source_date", ""))

    return out, str(raw_path)


def _default_artifacts(paths: ProjectPaths) -> FactorArtifacts:
    return FactorArtifacts(
        weekly_returns=paths.data_processed / "weekly_returns.csv",
        monthly_factors=paths.data_processed / "monthly_factors.csv",
        monthly_asset_returns=paths.data_processed / "monthly_asset_returns.csv",
        market_inputs=paths.data_processed / "market_inputs.csv",
        tencent_financials=paths.data_processed / "tencent_financials.csv",
        segment_revenue=paths.data_processed / "segment_revenue.csv",
    )



def _write_source_manifest(paths: ProjectPaths, asof: str, payload: dict[str, Any]) -> None:
    raw_dir = paths.data_raw / asof
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "factors_source_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)



def _build_synthetic_inputs(
    asof: str,
    paths: ProjectPaths,
    required_tickers: list[str],
    market_ticker: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ts = _parse_asof(asof)
    rng = np.random.default_rng(_seed_from_asof(asof))

    weekly = _generate_weekly_returns(ts, required_tickers, market_ticker, rng)
    monthly_factors = _generate_monthly_factors(ts, rng)
    monthly_assets = _generate_monthly_asset_returns(monthly_factors, required_tickers, market_ticker, rng)
    market_inputs = _generate_market_inputs(required_tickers)
    market_inputs, peer_source = _apply_peer_fundamentals_overrides(market_inputs, asof=asof, paths=paths)

    tencent_override = _read_override_if_valid(
        paths.data_raw / asof / "tencent_financials.csv", REQUIRED_TENCENT_FINANCIAL_COLS
    )
    if tencent_override is not None:
        tencent_financials = tencent_override.copy()
        fundamentals_source = "override_csv"
    else:
        tencent_financials = _generate_tencent_financials(asof)
        fundamentals_source = "synthetic_default"
    tencent_financials["fundamentals_source"] = fundamentals_source

    segment_override = _read_override_if_valid(paths.data_raw / asof / "segment_revenue.csv", REQUIRED_SEGMENT_COLS)
    if segment_override is not None:
        segment_revenue = segment_override.copy()
        segment_source = "override_csv"
    else:
        segment_revenue = _generate_segment_revenue(asof, float(tencent_financials.iloc[0]["revenue_hkd_bn"]))
        segment_source = "synthetic_default"
    segment_revenue["segment_source"] = segment_source

    _write_source_manifest(
        paths,
        asof,
        {
            "asof": asof,
            "mode": "synthetic",
            "peer_fundamentals_source": peer_source,
        },
    )
    return weekly, monthly_factors, monthly_assets, market_inputs, tencent_financials, segment_revenue



def _build_live_inputs(
    asof: str,
    paths: ProjectPaths,
    required_tickers: list[str],
    wacc_config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ts = _parse_asof(asof)
    timeout = int(wacc_config.get("http_timeout_seconds", 20))

    price_series: dict[str, pd.Series] = {}
    for ticker in required_tickers:
        price_series[ticker] = _fetch_stooq_close_series(ticker, asof=ts, timeout=timeout)

    weekly = _prices_to_weekly_returns(price_series)
    monthly_assets = _prices_to_monthly_returns(price_series)

    factors_url = str(
        wacc_config.get(
            "ken_french_factor_url",
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Asia_Pacific_ex_Japan_3_Factors_CSV.zip",
        )
    )
    monthly_factors = _fetch_ken_french_factors(url=factors_url, timeout=timeout)

    if bool(wacc_config.get("use_treasury_rf", True)):
        years_back = int(wacc_config.get("treasury_years_back", 10))
        monthly_factors = _merge_factor_rf_with_treasury(
            factors=monthly_factors,
            asof=ts,
            timeout=timeout,
            years_back=years_back,
        )

    monthly_factors["date"] = pd.to_datetime(monthly_factors["date"], errors="coerce")
    monthly_factors = monthly_factors.dropna(subset=["date"]).sort_values("date")
    monthly_factors = monthly_factors.loc[monthly_factors["date"] <= ts]
    monthly_factors["date"] = monthly_factors["date"].dt.date.astype(str)

    market_inputs = _generate_market_inputs(required_tickers)
    latest_prices: dict[str, float] = {
        ticker: float(series.iloc[-1]) for ticker, series in price_series.items() if not series.empty
    }

    for idx, row in market_inputs.iterrows():
        ticker = str(row["ticker"])
        if ticker not in latest_prices:
            continue
        latest = latest_prices[ticker]
        prev_price = float(row["current_price_hkd"])
        market_inputs.loc[idx, "current_price_hkd"] = latest
        if prev_price > 0:
            market_inputs.loc[idx, "market_equity_hkd_bn"] = float(row["market_equity_hkd_bn"]) * (
                latest / prev_price
            )

    market_inputs, peer_source = _apply_peer_fundamentals_overrides(market_inputs, asof=asof, paths=paths)

    tencent_override = _read_override_if_valid(
        paths.data_raw / asof / "tencent_financials.csv", REQUIRED_TENCENT_FINANCIAL_COLS
    )
    if tencent_override is not None:
        tencent_financials = tencent_override.copy()
        fundamentals_source = "override_csv"
    else:
        tencent_financials = _generate_tencent_financials(asof)
        fundamentals_source = "synthetic_default"
        target_price = latest_prices.get(str(wacc_config.get("target_ticker", "0700.HK")))
        if target_price is not None:
            tencent_financials.loc[0, "current_price_hkd"] = target_price
    tencent_financials["fundamentals_source"] = fundamentals_source

    segment_override = _read_override_if_valid(paths.data_raw / asof / "segment_revenue.csv", REQUIRED_SEGMENT_COLS)
    if segment_override is not None:
        segment_revenue = segment_override.copy()
        segment_source = "override_csv"
    else:
        segment_revenue = _generate_segment_revenue(asof, float(tencent_financials.iloc[0]["revenue_hkd_bn"]))
        segment_source = "synthetic_default"
    segment_revenue["segment_source"] = segment_source

    _write_source_manifest(
        paths,
        asof,
        {
            "asof": asof,
            "mode": "live",
            "fundamentals_source": fundamentals_source,
            "segment_source": segment_source,
            "peer_fundamentals_source": peer_source,
            "sources": {
                "prices": "stooq",
                "factors": factors_url,
                "risk_free": "US Treasury daily yield CSV",
            },
            "tickers": required_tickers,
        },
    )

    return weekly, monthly_factors, monthly_assets, market_inputs, tencent_financials, segment_revenue



def run_factors(
    asof: str,
    paths: ProjectPaths,
    peers: list[str],
    wacc_config: dict,
    refresh: bool = False,
    source_mode: str | None = None,
) -> FactorArtifacts:
    paths.ensure()
    artifacts = _default_artifacts(paths)
    required_tickers = [wacc_config["target_ticker"], *peers, wacc_config["market_ticker"]]

    mode = str(source_mode or wacc_config.get("source_mode", "auto")).strip().lower()
    if mode not in {"auto", "live", "synthetic"}:
        raise FactorDataError(f"Invalid source mode: {mode}")

    all_exist = all(path.exists() for path in artifacts.__dict__.values())
    if refresh or not all_exist:
        build_frames: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]

        if mode in {"auto", "live"}:
            try:
                build_frames = _build_live_inputs(asof, paths, required_tickers, wacc_config)
            except (FactorDataError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                if mode == "live":
                    raise FactorDataError(f"Live factor build failed: {exc}") from exc
                warnings.warn(f"Live factor build failed ({exc}); using synthetic fallback.", RuntimeWarning)
                build_frames = _build_synthetic_inputs(asof, paths, required_tickers, wacc_config["market_ticker"])
                _write_source_manifest(
                    paths,
                    asof,
                    {
                        "asof": asof,
                        "mode": "synthetic_fallback",
                        "reason": str(exc),
                        "tickers": required_tickers,
                    },
                )
        else:
            build_frames = _build_synthetic_inputs(asof, paths, required_tickers, wacc_config["market_ticker"])
            _write_source_manifest(
                paths,
                asof,
                {
                    "asof": asof,
                    "mode": "synthetic",
                    "tickers": required_tickers,
                },
            )

        weekly, monthly_factors, monthly_assets, market_inputs, tencent_financials, segment_revenue = build_frames

        weekly.to_csv(artifacts.weekly_returns, index=False)
        monthly_factors.to_csv(artifacts.monthly_factors, index=False)
        monthly_assets.to_csv(artifacts.monthly_asset_returns, index=False)
        market_inputs.to_csv(artifacts.market_inputs, index=False)
        tencent_financials.to_csv(artifacts.tencent_financials, index=False)
        segment_revenue.to_csv(artifacts.segment_revenue, index=False)

    weekly = pd.read_csv(artifacts.weekly_returns)
    monthly_factors = pd.read_csv(artifacts.monthly_factors)
    monthly_assets = pd.read_csv(artifacts.monthly_asset_returns)

    validate_ticker_coverage(
        weekly,
        required_tickers,
        min_obs=int(wacc_config.get("min_weekly_obs", 80)),
        ticker_col="ticker",
        value_col="ret",
    )

    validate_ticker_coverage(
        monthly_assets,
        [wacc_config["target_ticker"]],
        min_obs=int(wacc_config.get("apt_min_obs", 36)),
        ticker_col="ticker",
        value_col="ret",
    )

    required_cols = {"RF", "MKT_EXCESS", "SMB", "HML"}
    if not required_cols.issubset(set(monthly_factors.columns)):
        raise FactorDataError(
            f"monthly_factors.csv missing columns: {sorted(required_cols.difference(monthly_factors.columns))}"
        )

    return artifacts


def fetch_close_series_for_ticker(ticker: str, asof: str, timeout: int = 20) -> pd.Series:
    return _fetch_stooq_close_series(ticker=ticker, asof=_parse_asof(asof), timeout=timeout)
