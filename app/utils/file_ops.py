from __future__ import annotations

import json
import secrets
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from ..config import settings

_RANDOM_ALPHABET = string.ascii_lowercase + string.digits


def _generate_token(length: int = 8) -> str:
    return "".join(secrets.choice(_RANDOM_ALPHABET) for _ in range(length))


def make_storage_filename(original_name: str, suffix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    token = _generate_token()
    safe_suffix = suffix.lstrip(".")
    return f"{timestamp}_{token}_{original_name}.{safe_suffix}" if safe_suffix else f"{timestamp}_{token}_{original_name}"


def persist_bytes(directory: Path, filename: str, data: bytes) -> Path:
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # Directory should already exist in production environments
        if not directory.exists():
            raise
    destination = directory / filename
    destination.write_bytes(data)
    return destination


def cleanup_storage(directories: Iterable[Path], retention_hours: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    for directory in directories:
        if not directory.exists():
            continue
        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue
            modified = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                try:
                    file_path.unlink()
                except OSError:
                    continue


def build_metadata_header(metadata: dict) -> str:
    return json.dumps(metadata, ensure_ascii=False)
