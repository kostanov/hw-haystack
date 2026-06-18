"""Сохранение медиафайлов на диск."""

from pathlib import Path
from uuid import uuid4


def save_media_file(
    data: bytes,
    directory: Path,
    extension: str,
    *,
    prefix: str = "cat",
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    ext = extension.lstrip(".")
    path = directory / f"{prefix}_{uuid4().hex[:10]}.{ext}"
    path.write_bytes(data)
    return path
