from __future__ import annotations

import re
from pathlib import Path


WINDOWS_FORBIDDEN = r'\\/:*?"<>|'
FORBIDDEN_RE = re.compile(r'[\\/:*?"<>|]')
SPACE_RE = re.compile(r"\s+")


def sanitize_filename(text: str, max_length: int = 120) -> str:
    """把商品英文标题清洗成 Windows 可用文件名。"""
    if not text:
        text = "untitled"

    text = text.replace("\u00a0", " ")
    text = text.replace("\r", " ").replace("\n", " ")
    text = FORBIDDEN_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip(" .")

    if not text:
        text = "untitled"

    if len(text) > max_length:
        text = text[:max_length].rstrip(" .")

    return text or "untitled"


def unique_path(folder: Path, filename_stem: str, suffix: str = ".png") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    candidate = folder / f"{filename_stem}{suffix}"
    if not candidate.exists():
        return candidate

    for i in range(1, 1000):
        candidate = folder / f"{filename_stem}_{i:03d}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError("同名文件太多，无法生成唯一文件名。")
