from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    pass



def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigError(f"Config must be a mapping: {path}")
    return payload
