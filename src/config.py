from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.json"


@dataclass
class AppConfig:
    adspower_api: str = "http://local.adspower.com:50325"
    profile_id: str = ""
    output_root: str = "D:/Temu截图/截图结果"
    registry_path: str = "D:/Temu截图/登记/截图进度.xlsx"
    max_filename_length: int = 120
    min_image_width: int = 250
    min_image_height: int = 250
    prefer_left_side_image: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        base = cls()
        for key, value in data.items():
            if hasattr(base, key):
                setattr(base, key, value)
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "adspower_api": self.adspower_api,
            "profile_id": self.profile_id,
            "output_root": self.output_root,
            "registry_path": self.registry_path,
            "max_filename_length": self.max_filename_length,
            "min_image_width": self.min_image_width,
            "min_image_height": self.min_image_height,
            "prefer_left_side_image": self.prefer_left_side_image,
        }


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return AppConfig.from_dict(data)
    except Exception:
        return AppConfig()


def save_config(config: AppConfig) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
