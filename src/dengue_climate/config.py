"""Load the project configuration from config.yaml.

Paths are resolved to absolute paths anchored at the project root so callers
do not depend on the current working directory.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# project root = two levels up from this file (src/dengue_climate/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Read config.yaml; resolve every entry under ``paths`` to an absolute path."""
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        config: dict[str, Any] = yaml.safe_load(fh)
    config["paths"] = {k: PROJECT_ROOT / v for k, v in config.get("paths", {}).items()}
    return config


def get_path(key: str) -> Path:
    """Return an absolute path from the ``paths`` section of the config."""
    paths = load_config()["paths"]
    if key not in paths:
        raise KeyError(f"Unknown path key {key!r}. Available: {sorted(paths)}")
    return paths[key]
