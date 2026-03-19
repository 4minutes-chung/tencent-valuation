from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from .paths import ProjectPaths
from .provenance import file_sha256, write_source_manifest


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
        "sha256": file_sha256(out_path),
        "usage_status": "fetched",
    }


def run_fetch(asof: str, paths: ProjectPaths, sources_config: dict | None = None) -> FetchArtifacts:
    paths.ensure()
    raw_dir = paths.data_raw / asof
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_map = (sources_config or {}).get("sources", {})
    year = str(asof)[:4]
    targets = [
        (
            "tencent_ir_financial_news",
            str(source_map.get("tencent_ir_news", "https://www.tencent.com/en-us/investors/financial-news.html")),
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
            str(
                source_map.get(
                    "ken_french_apac_3f",
                    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Asia_Pacific_ex_Japan_3_Factors_CSV.zip",
                )
            ),
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
            entry["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            entry = {
                "url": url,
                "file": str(out_path),
                "status": "error",
                "usage_status": "failed",
                "error": str(exc),
            }
        entry["name"] = name
        entry["parser_version"] = str((sources_config or {}).get("parser_version", "v3.0"))
        entries.append(entry)

    manifest = raw_dir / "source_manifest.json"
    write_source_manifest(
        out_path=manifest,
        asof=asof,
        parser_version=str((sources_config or {}).get("parser_version", "v3.0")),
        entries=entries,
    )

    # Keep V2-compatible file name for easier traceability.
    legacy_manifest = raw_dir / "fetch_manifest.json"
    if not legacy_manifest.exists():
        legacy_manifest.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")

    return FetchArtifacts(raw_dir=raw_dir, manifest=manifest)
