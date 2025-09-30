from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULES_TO_RELOAD = [
    "app.config",
    "app.database",
    "app.models",
    "app.utils.file_ops",
    "app.services.qr_processor",
    "app.routers.health",
    "app.routers.processing",
    "app.routers.logs",
    "app.main",
]


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    storage_root = tmp_path / "storage"
    db_path = tmp_path / "data" / "test.db"
    monkeypatch.setenv("QR_CUT_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("QR_CUT_DATABASE_PATH", str(db_path))

    for module_name in MODULES_TO_RELOAD:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
