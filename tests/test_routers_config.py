from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import config
from config import Settings, save_settings
from routers.config import router


def build_client(tmp_path, monkeypatch):
    save_settings(Settings(output_dir=tmp_path / "clips"))
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_get_config_returns_expected_keys(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert "cache_dir" in payload
    assert "output_dir" in payload
    assert payload["clip_crf"] == 26
    assert payload["clip_preset"] == "medium"
    assert payload["clip_audio_kbps"] == 96


def test_post_config_updates_output_dir(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.post("/api/config", json={"output_dir": "/tmp/test_clips"})

    assert response.status_code == 200
    assert response.json()["output_dir"] == "/tmp/test_clips"


def test_post_config_updates_cache_dir(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.post("/api/config", json={"cache_dir": "/tmp/test_cache"})

    assert response.status_code == 200
    assert response.json()["cache_dir"] == "/tmp/test_cache"


def test_post_config_without_output_dir_keeps_value(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    before = client.get("/api/config").json()["output_dir"]

    response = client.post("/api/config", json={})

    assert response.status_code == 200
    assert response.json()["output_dir"] == before


def test_health_returns_ok(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "ffmpeg" in payload
