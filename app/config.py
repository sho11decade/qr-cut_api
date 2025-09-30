from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    project_name: str = Field(default="QR Cut API", env="QR_CUT_PROJECT_NAME")
    version: str = Field(default="1.0.0", env="QR_CUT_VERSION")
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], env="QR_CUT_ALLOWED_ORIGINS")
    database_path: Path = Field(default=Path("data/app.db"), env="QR_CUT_DATABASE_PATH")
    storage_root: Path = Field(default=Path("storage"), env="QR_CUT_STORAGE_ROOT")
    temp_retention_hours: int = Field(default=24, env="QR_CUT_RETENTION_HOURS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

def ensure_directories():
    """Ensure required directories exist with proper error handling."""
    import os
    
    directories = [
        settings.storage_root,
        settings.storage_root / "uploads",
        settings.storage_root / "processed",
        settings.database_path.parent,
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # Check if directory already exists
            if not directory.exists():
                print(f"Warning: Could not create directory {directory}: {e}")
                # In production environments, directories should be created
                # by the deployment process or container setup
