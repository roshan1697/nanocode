import importlib
import os

import pytest

os.environ.setdefault("OLLAMA_API_KEY", "test-key")
os.environ.setdefault("FIRECRAWL_API_KEY", "test-key")


nc = importlib.import_module("nanocode.main")


@pytest.fixture
def workspace(tmp_path, monkeypatch):

    monkeypatch.setattr(nc, "WORKSPACE_ROOT", str(tmp_path))
    return tmp_path