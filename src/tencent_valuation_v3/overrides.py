from __future__ import annotations

import io
import re
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .paths import ProjectPaths


class OverrideBuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class OverrideArtifacts:
    quarterly_financials: Path
    tencent_financials: Path
    segment_revenue: Path
    peer_fundamentals: Path


_RELEASE_SPECS: list[dict[str, str]] = [
    {
        "title": "Tencent Announces 2024 First Quarter Results",
        "slug": "tencent_announces_2024_first_quarter_results",
        "current_quarter": "1Q2024",
        "prev_quarter": "1Q2023",
    },
    {
        "title": "Tencent Announces 2024 Second Quarter Results",
        "slug": "tencent_announces_2024_second_quarter_results",
        "current_quarter": "2Q2024",
        "prev_quarter": "2Q2023",
    },
    {
        "title": "Tencent Announces 2024 Third Quarter Results",
        "slug": "tencent_announces_2024_third_quarter_results",
        "current_quarter": "3Q2024",
        "prev_quarter": "3Q2023",
    },
    {
        "title": "Tencent Announces 2024 Annual and Fourth Quarter Results",
        "slug": "tencent_announces_2024_annual_and_fourth_quarter_results",
        "current_quarter": "4Q2024",
        "prev_quarter": "4Q2023",
    },
    {
        "title": "Tencent Announces 2025 First Quarter Results",
        "slug": "tencent_announces_2025_first_quarter_results",
        "current_quarter": "1Q2025",
        "prev_quarter": "4Q2024",
    },
    {
        "title": "Tencent Announces 2025 Second Quarter Results",
        "slug": "tencent_announces_2025_second_quarter_results",
        "current_quarter": "2Q2025",
        "prev_quarter": "1Q2025",
    },
    {
        "title": "Tencent Announces 2025 Third Quarter Results",
        "slug": "tencent_announces_2025_third_quarter_results",
        "current_quarter": "3Q2025",
        "prev_quarter": "2Q2025",
    },
]


def _http_get_bytes(url: str, timeout: int = 30) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _quarter_end(quarter_label: str) -> str:
    if len(quarter_label) != 6 or quarter_label[1] != "Q":
        raise OverrideBuildError(f"Invalid quarter label: {quarter_label}")
    quarter = quarter_label[:2]
    year = quarter_label[2:]
    month_day = {
        "1Q": "03-31",
        "2Q": "06-30",
        "3Q": "09-30",
        "4Q": "12-31",
    }.get(quarter)
    if month_day is None:
        raise OverrideBuildError(f"Invalid quarter label: {quarter_label}")
    return f"{year}-{month_day}"


def _parse_numeric_tokens(line: str) -> list[float]:
    tokens = re.findall(r"\(?-?\d[\d,]*(?:\.\d+)?\)?", line)
    values: list[float] = []
    for token in tokens:
        sign = -1.0 if token.startswith("(") and token.endswith(")") else 1.0
        raw = token.strip("()").replace(",", "")
        try:
            values.append(sign * float(raw))
        except ValueError:
            continue
    return values


def _extract_first_last(lines: list[str], prefix: str, min_abs: float | None = None) -> tuple[float, float, int]:
    for idx, line in enumerate(lines, start=1):
        stripped = " ".join(line.strip().split())
        if not stripped.startswith(prefix):
            continue
        numbers = _parse_numeric_tokens(stripped)
        if min_abs is not None:
            numbers = [value for value in numbers if abs(value) >= min_abs]
        if len(numbers) >= 2:
            return numbers[0], numbers[1], idx
    raise OverrideBuildError(f"Could not find row '{prefix}' in filing text")


def _extract_release_metrics(
    txt_path: Path,
    source_doc: str,
    current_quarter: str,
    prev_quarter: str,
) -> list[dict[str, Any]]:
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    rev_cur, rev_prev, rev_line = _extract_first_last(lines, "Revenues", min_abs=1000.0)
    op_cur, op_prev, op_line = _extract_first_last(lines, "Non-IFRS operating profit", min_abs=1000.0)
    cash_cur, cash_prev, cash_line = _extract_first_last(lines, "Net cash", min_abs=1000.0)
    capex_cur, capex_prev, capex_line = _extract_first_last(lines, "Capital expenditures", min_abs=1000.0)

    # Shares = profit attributable to equity holders / basic EPS.
    shares_cur: float | None = None
    shares_prev: float | None = None
    try:
        attr_cur, attr_prev, attr_line = _extract_first_last(lines, "Equity holders of the Company", min_abs=1000.0)
        eps_cur, eps_prev, eps_line = _extract_first_last(lines, "- basic")
        if eps_cur != 0:
            shares_cur = attr_cur / eps_cur / 1000.0
        if eps_prev != 0:
            shares_prev = attr_prev / eps_prev / 1000.0
    except OverrideBuildError:
        attr_line = op_line
        eps_line = op_line

    return [
        {
            "period_end": _quarter_end(current_quarter),
            "revenue_rmb_bn": rev_cur / 1000.0,
            "non_ifrs_op_profit_rmb_bn": op_cur / 1000.0,
            "capex_rmb_bn": capex_cur / 1000.0,
            "net_cash_rmb_bn": cash_cur / 1000.0,
            "shares_out_bn": shares_cur,
            "source_doc": source_doc,
            "source_page_hint": (
                f"{txt_path.name}:lines{rev_line},{op_line},{cash_line},{capex_line},{attr_line},{eps_line}"
            ),
            "priority": 2,
        },
        {
            "period_end": _quarter_end(prev_quarter),
            "revenue_rmb_bn": rev_prev / 1000.0,
            "non_ifrs_op_profit_rmb_bn": op_prev / 1000.0,
            "capex_rmb_bn": capex_prev / 1000.0,
            "net_cash_rmb_bn": cash_prev / 1000.0,
            "shares_out_bn": shares_prev,
            "source_doc": source_doc,
            "source_page_hint": (
                f"{txt_path.name}:lines{rev_line},{op_line},{cash_line},{capex_line},{attr_line},{eps_line}"
            ),
            "priority": 1,
        },
    ]


def _extract_latest_segment_values(txt_path: Path) -> tuple[dict[str, float], str]:
    lines = txt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    mapping = {
        "VAS": "VAS",
        "Marketing Services": "Marketing Services",
        "FinTech and Business Services": "FinTech and Business Services",
        "Others": "Others",
    }
    output: dict[str, float] = {}
    hint_lines: list[int] = []
    for idx, line in enumerate(lines, start=1):
        stripped = " ".join(line.strip().split())
        for prefix, key in mapping.items():
            if not stripped.startswith(prefix):
                continue
            nums = _parse_numeric_tokens(stripped)
            if nums:
                output[key] = nums[0] / 1000.0
                hint_lines.append(idx)
    if len(output) != 4:
        raise OverrideBuildError("Could not parse latest-quarter segment values from filing")
    return output, f"{txt_path.name}:lines{','.join(str(x) for x in hint_lines)}"


def _fetch_cny_hkd(asof: str, timeout: int = 20) -> tuple[float, str]:
    frame = pd.read_csv(io.BytesIO(_http_get_bytes("https://stooq.com/q/d/l/?s=cnyhkd&i=d", timeout=timeout)))
    if "No data" in frame.columns:
        raise OverrideBuildError("No CNYHKD data from Stooq")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
    frame = frame.loc[frame["Date"] <= pd.Timestamp(asof)]
    if frame.empty:
        raise OverrideBuildError("No CNYHKD rows <= asof")
    return float(frame.iloc[-1]["Close"]), "stooq_cnyhkd_close"


def _fetch_spot_price_hkd(ticker: str, asof: str, timeout: int = 20) -> float:
    symbol = ticker.lower()
    if ticker.upper().endswith(".HK"):
        symbol = f"{int(ticker.split('.')[0])}.hk"
    frame = pd.read_csv(io.BytesIO(_http_get_bytes(f"https://stooq.com/q/d/l/?s={symbol}&i=d", timeout=timeout)))
    if "No data" in frame.columns:
        raise OverrideBuildError(f"No price data for {ticker}")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
    frame = frame.loc[frame["Date"] <= pd.Timestamp(asof)]
    if frame.empty:
        raise OverrideBuildError(f"No price rows <= asof for {ticker}")
    return float(frame.iloc[-1]["Close"])


def _collect_result_links(financial_news_html: Path) -> dict[str, str]:
    if not financial_news_html.exists():
        raise OverrideBuildError(f"Missing financial news page: {financial_news_html}")
    soup = BeautifulSoup(financial_news_html.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    links: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        title_tag = anchor.find("h3")
        if title_tag is None:
            continue
        title = " ".join(title_tag.get_text(" ", strip=True).split())
        href = str(anchor["href"])
        if "Results" in title and href.lower().endswith(".pdf"):
            links[title] = href
    return links


def _ensure_release_files(asof: str, paths: ProjectPaths) -> dict[str, Path]:
    raw_dir = paths.data_raw / asof
    filings_dir = raw_dir / "filings"
    filings_dir.mkdir(parents=True, exist_ok=True)

    links = _collect_result_links(raw_dir / "tencent_ir_financial_news.html")
    out: dict[str, Path] = {}
    for spec in _RELEASE_SPECS:
        title = spec["title"]
        if title not in links:
            raise OverrideBuildError(f"Missing filing link for '{title}' in financial-news page")
        pdf_path = filings_dir / f"{spec['slug']}.pdf"
        txt_path = filings_dir / f"{spec['slug']}.txt"
        if not pdf_path.exists():
            pdf_path.write_bytes(_http_get_bytes(links[title], timeout=30))
        if not txt_path.exists():
            reader = PdfReader(str(pdf_path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            txt_path.write_text(text, encoding="utf-8")
        out[title] = txt_path
    return out


def _merge_quarter_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        raise OverrideBuildError("No quarterly records parsed")
    frame["period_end"] = pd.to_datetime(frame["period_end"])
    frame = frame.sort_values(["period_end", "priority"], ascending=[True, False])
    frame = frame.drop_duplicates(subset=["period_end"], keep="first")
    frame = frame.sort_values("period_end")
    frame["shares_out_bn"] = frame["shares_out_bn"].ffill().bfill()
    frame["period_end"] = frame["period_end"].dt.date.astype(str)
    frame = frame[
        [
            "period_end",
            "revenue_rmb_bn",
            "non_ifrs_op_profit_rmb_bn",
            "capex_rmb_bn",
            "net_cash_rmb_bn",
            "shares_out_bn",
            "source_doc",
            "source_page_hint",
        ]
    ]
    if len(frame) < 8:
        raise OverrideBuildError(f"Need at least 8 quarterly records, found {len(frame)}")
    return frame.tail(8).reset_index(drop=True)


def _create_peer_fundamentals_if_missing(asof: str, paths: ProjectPaths, peers: list[str], target_ticker: str) -> Path:
    path = paths.data_raw / asof / "peer_fundamentals.csv"
    if path.exists():
        return path

    template = {
        "0700.HK": {"gross_debt": 350.0, "interest": 12.0, "tax": 0.20, "shares_out": 9.09},
        "9988.HK": {"gross_debt": 170.0, "interest": 7.0, "tax": 0.18, "shares_out": 22.97},
        "3690.HK": {"gross_debt": 120.0, "interest": 6.0, "tax": 0.19, "shares_out": 6.43},
        "9999.HK": {"gross_debt": 90.0, "interest": 4.0, "tax": 0.21, "shares_out": 2.88},
        "9618.HK": {"gross_debt": 110.0, "interest": 5.0, "tax": 0.20, "shares_out": 4.55},
        "9888.HK": {"gross_debt": 95.0, "interest": 4.3, "tax": 0.19, "shares_out": 5.13},
    }
    rows: list[dict[str, Any]] = []
    for ticker in [target_ticker, *peers]:
        payload = template.get(ticker)
        if payload is None:
            continue
        rows.append(
            {
                "ticker": ticker,
                "gross_debt_hkd_bn": payload["gross_debt"],
                "interest_expense_hkd_bn_3y_avg": payload["interest"],
                "effective_tax_rate_3y_avg": payload["tax"],
                "shares_out_bn": payload["shares_out"],
                "source_doc": "peer_fundamentals_template",
                "source_date": asof,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def build_overrides(
    asof: str,
    paths: ProjectPaths,
    wacc_config: dict,
    peers: list[str],
) -> OverrideArtifacts:
    paths.ensure()
    release_files = _ensure_release_files(asof, paths)

    quarter_records: list[dict[str, Any]] = []
    for spec in _RELEASE_SPECS:
        title = spec["title"]
        parsed = _extract_release_metrics(
            txt_path=release_files[title],
            source_doc=title,
            current_quarter=spec["current_quarter"],
            prev_quarter=spec["prev_quarter"],
        )
        quarter_records.extend(parsed)

    quarterly = _merge_quarter_records(quarter_records)
    quarterly_path = paths.data_processed / "tencent_quarterly_financials.csv"
    quarterly.to_csv(quarterly_path, index=False)

    latest4 = quarterly.tail(4)
    ttm_revenue_rmb_bn = float(latest4["revenue_rmb_bn"].sum())
    ttm_non_ifrs_rmb_bn = float(latest4["non_ifrs_op_profit_rmb_bn"].sum())
    ttm_capex_rmb_bn = float(latest4["capex_rmb_bn"].sum())
    latest_net_cash_rmb_bn = float(latest4.iloc[-1]["net_cash_rmb_bn"])
    latest_shares_out_bn = float(latest4.iloc[-1]["shares_out_bn"])

    if ttm_revenue_rmb_bn <= 0:
        raise OverrideBuildError("TTM revenue must be positive")

    timeout = int(wacc_config.get("http_timeout_seconds", 20))
    try:
        fx_cny_hkd, fx_source = _fetch_cny_hkd(asof, timeout=timeout)
    except Exception as exc:
        fx_cny_hkd = float(wacc_config.get("fx_fallback_cny_hkd", 1.08))
        fx_source = "fallback_fixed"
        warnings.warn(
            f"CNY/HKD fetch failed ({exc}); using hardcoded fallback rate {fx_cny_hkd}. "
            "Set fx_fallback_cny_hkd in wacc.yaml to override.",
            RuntimeWarning,
            stacklevel=2,
        )

    try:
        current_price_hkd = _fetch_spot_price_hkd(wacc_config.get("target_ticker", "0700.HK"), asof, timeout=timeout)
    except Exception as exc:
        current_price_hkd = float(wacc_config.get("fallback_market_price_hkd", 533.0))
        warnings.warn(
            f"Spot price fetch for {wacc_config.get('target_ticker', '0700.HK')} failed ({exc}); "
            f"using fallback price HKD {current_price_hkd}. "
            "Set fallback_market_price_hkd in wacc.yaml to override.",
            RuntimeWarning,
            stacklevel=2,
        )

    tencent_financials = pd.DataFrame(
        [
            {
                "asof": asof,
                "revenue_hkd_bn": ttm_revenue_rmb_bn * fx_cny_hkd,
                "ebit_margin": ttm_non_ifrs_rmb_bn / ttm_revenue_rmb_bn,
                "capex_pct_revenue": ttm_capex_rmb_bn / ttm_revenue_rmb_bn,
                "nwc_pct_revenue": float(wacc_config.get("default_nwc_pct_revenue", 0.02)),
                "dep_pct_revenue": float(wacc_config.get("default_dep_pct_revenue", 0.03)),
                "net_cash_hkd_bn": latest_net_cash_rmb_bn * fx_cny_hkd,
                "shares_out_bn": latest_shares_out_bn,
                "current_price_hkd": current_price_hkd,
                "fundamentals_method": "ttm_4q_from_quarterly",
                "source_period": f"{latest4.iloc[0]['period_end']}..{latest4.iloc[-1]['period_end']}",
                "fx_cny_hkd": fx_cny_hkd,
                "fx_source": fx_source,
                "fundamentals_source": "override_csv",
            }
        ]
    )
    tencent_financials_path = paths.data_raw / asof / "tencent_financials.csv"
    tencent_financials.to_csv(tencent_financials_path, index=False)

    latest_spec = _RELEASE_SPECS[-1]
    latest_release = release_files[latest_spec["title"]]
    segment_rmb, seg_hint = _extract_latest_segment_values(latest_release)
    total_rmb = sum(segment_rmb.values())
    segment_rows = []
    for segment, value_rmb in segment_rmb.items():
        segment_rows.append(
            {
                "period": quarterly.iloc[-1]["period_end"],
                "segment": segment,
                "revenue_hkd_bn": value_rmb * fx_cny_hkd,
                "total_revenue_hkd_bn": total_rmb * fx_cny_hkd,
                "source_doc": latest_spec["title"],
                "source_page_hint": seg_hint,
                "segment_source": "override_csv",
            }
        )
    segment_revenue = pd.DataFrame(segment_rows)
    segment_revenue_path = paths.data_raw / asof / "segment_revenue.csv"
    segment_revenue.to_csv(segment_revenue_path, index=False)

    peer_fundamentals_path = _create_peer_fundamentals_if_missing(
        asof=asof,
        paths=paths,
        peers=peers,
        target_ticker=str(wacc_config.get("target_ticker", "0700.HK")),
    )

    return OverrideArtifacts(
        quarterly_financials=quarterly_path,
        tencent_financials=tencent_financials_path,
        segment_revenue=segment_revenue_path,
        peer_fundamentals=peer_fundamentals_path,
    )
