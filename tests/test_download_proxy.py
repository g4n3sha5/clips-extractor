import os

import pytest

from config import CONFIG_PATH, Settings, save_settings
from services.download import _proxy_for_ydl


def test_proxy_from_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("config.CONFIG_PATH", tmp_path / "config.json")
    save_settings(Settings(proxy_url="http://127.0.0.1:7890"))
    assert _proxy_for_ydl() == "http://127.0.0.1:7890"


def test_proxy_from_env(monkeypatch) -> None:
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1080")
    monkeypatch.setattr(
        "services.download.load_settings",
        lambda: Settings(proxy_url=None),
    )
    assert _proxy_for_ydl() == "http://127.0.0.1:1080"
