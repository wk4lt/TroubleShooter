from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    root: Path
    knowledge_dir: Path
    config_path: Path
    values: dict[str, Any]

    @property
    def retrieval(self) -> dict[str, Any]:
        return self.values["retrieval"]


def load_settings(config_path: Path | None = None) -> Settings:
    path = config_path or ROOT / "config.yaml"
    values = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Settings(
        root=ROOT,
        knowledge_dir=ROOT / "knowledge",
        config_path=path,
        values=values,
    )
