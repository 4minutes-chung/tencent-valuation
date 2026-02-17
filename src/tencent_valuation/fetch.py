from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .paths import ProjectPaths


@dataclass(frozen=True)
class FetchArtifacts:
    raw_dir: Path
    manifest: Path



def _download(url: str, out_path: Path, timeout: int = 30) -> dict[str, object]:
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
        content = response.read()

    out_path.write_bytes(content)
    return {
        "url": url,
        "file": str(out_path),
        "bytes": len(content),
        "status": "ok",
    }



def run_fetch(asof: str, paths: ProjectPaths) -> FetchArtifacts:
    paths.ensure()
    raw_dir = paths.data_raw / asof
    raw_dir.mkdir(parents=True, exist_ok=True)

    year = str(asof)[:4]
    targets = [
        (
            "tencent_ir_financial_news",
            "https://www.tencent.com/en-us/investors/financial-news.html",
            raw_dir / "tencent_ir_financial_news.html",
        ),
        (
            "hkex_title_search",
            "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=en",
            raw_dir / "hkex_title_search.html",
        ),
        (
            "hkex_ccass",
            "https://www.hkexnews.hk/sdw/search/mutualmarket.aspx?t=hk",
            raw_dir / "hkex_ccass.html",
        ),
        (
            "sfc_short_positions",
            "https://www.sfc.hk/en/Regulatory-functions/Market/Short-position-reporting",
            raw_dir / "sfc_short_positions.html",
        ),
        (
            "ken_french_apac_3f",
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Asia_Pacific_ex_Japan_3_Factors_CSV.zip",
            raw_dir / "Asia_Pacific_ex_Japan_3_Factors_CSV.zip",
        ),
        (
            "ust_daily_yield",
            (
                "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
                f"&field_tdr_date_value={year}&page&_format=csv"
            ),
            raw_dir / f"ust_daily_yield_{year}.csv",
        ),
    ]

    entries: list[dict[str, object]] = []
    for name, url, out_path in targets:
        try:
            entry = _download(url, out_path)
        except Exception as exc:  # noqa: BLE001 - snapshot should continue on partial failures
            entry = {
                "url": url,
                "file": str(out_path),
                "status": "error",
                "error": str(exc),
            }
        entry["name"] = name
        entries.append(entry)

    manifest_payload = {
        "asof": asof,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }

    manifest = raw_dir / "fetch_manifest.json"
    with manifest.open("w", encoding="utf-8") as handle:
        json.dump(manifest_payload, handle, indent=2)

    return FetchArtifacts(raw_dir=raw_dir, manifest=manifest)
