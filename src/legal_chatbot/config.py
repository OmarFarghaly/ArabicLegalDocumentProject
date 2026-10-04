from __future__ import annotations

from pathlib import Path
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARAMS_FILE = PROJECT_ROOT / "params.toml"


def load_params(path: Path = PARAMS_FILE) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)
    