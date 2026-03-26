from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SchemaCheckResult:
    path: Path
    required_columns: list[str]
    missing_columns: list[str]

    @property
    def ok(self) -> bool:
        return len(self.missing_columns) == 0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_source_manifest(
    out_path: Path,
    asof: str,
    parser_version: str,
    entries: list[dict[str, Any]],
) -> Path:
    payload = {
        "asof": asof,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "parser_version": parser_version,
        "entries": entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return out_path


def validate_required_columns(path: Path, required_columns: list[str]) -> SchemaCheckResult:
    if not path.exists():
        return SchemaCheckResult(path=path, required_columns=required_columns, missing_columns=required_columns)

    with path.open("r", encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")

    required = [str(x) for x in required_columns]
    missing = [col for col in required if col not in header]
    return SchemaCheckResult(path=path, required_columns=required, missing_columns=missing)
