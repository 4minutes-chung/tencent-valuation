from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    config: Path
    data_raw: Path
    data_processed: Path
    data_model: Path
    reports: Path

    def ensure(self) -> None:
        self.config.mkdir(parents=True, exist_ok=True)
        self.data_raw.mkdir(parents=True, exist_ok=True)
        self.data_processed.mkdir(parents=True, exist_ok=True)
        self.data_model.mkdir(parents=True, exist_ok=True)
        self.reports.mkdir(parents=True, exist_ok=True)



def build_paths(project_root: str | Path | None = None) -> ProjectPaths:
    root = Path(project_root or Path.cwd()).resolve()
    return ProjectPaths(
        root=root,
        config=root / "config",
        data_raw=root / "data" / "raw",
        data_processed=root / "data" / "processed",
        data_model=root / "data" / "model",
        reports=root / "reports",
    )
