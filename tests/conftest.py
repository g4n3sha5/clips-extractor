"""Isolate config + session store per test (tmp_path under pytest)."""

import pytest

import config
from services.session import reset_session


@pytest.fixture(autouse=True)
def isolate_config_and_session(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    reset_session()
