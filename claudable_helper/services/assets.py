import os
from pathlib import Path
from typing import Optional


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def write_bytes(path: str, data: bytes) -> None:
    ensure_dir(str(Path(path).parent))
    with open(path, "wb") as f:
        f.write(data)


def write_text(path: str, data: str) -> None:
    ensure_dir(str(Path(path).parent))
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
