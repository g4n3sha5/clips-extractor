from pathlib import Path

import config
from config import Settings
from fastapi.testclient import TestClient
from services.session import reset_session


def test_main_routes_and_static(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    from main import app

    client = TestClient(app)

    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    assert config_response.headers["content-type"].startswith("application/json")

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    health_json = health_response.json()
    assert health_json["status"] == "ok"
    assert "ffmpeg" in health_json

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert index_response.headers["content-type"].startswith("text/html")


def test_lifespan_creates_directories(tmp_path, monkeypatch):
    output_dir = tmp_path / "clips_out"
    desc_dir = tmp_path / "clips_out" / "descriptions"
    cache_dir = tmp_path / "cache_out"
    from main import app
    monkeypatch.setattr(
        "main.load_settings",
        lambda: config.Settings(cache_dir=cache_dir, output_dir=output_dir, descriptions_dir=desc_dir),
    )

    with TestClient(app):
        pass

    assert Path(cache_dir).exists()
    assert Path(output_dir).exists()
    assert Path(desc_dir).exists()


def test_clips_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    reset_session()
    from main import app

    client = TestClient(app)
    response = client.get("/api/clips")
    assert response.status_code == 200
    assert response.json() == {"clips": []}


def test_extract_without_cache_queues_clip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")

    def fake_load() -> Settings:
        return Settings(
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "out",
            descriptions_dir=tmp_path / "out" / "descriptions",
        )

    monkeypatch.setattr(config, "load_settings", fake_load)
    reset_session()
    from main import app

    client = TestClient(app)
    url = "https://example.com/watch?v=1"
    assert client.post("/api/instructional", json={"url": url}).status_code == 200
    response = client.post(
        "/api/clips",
        json={"start": "0", "end": "1", "filename": "x"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["position"] == 1
    assert client.get("/api/clips/queue", params={"url": url}).json()["pending"] == 1


def test_cache_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")

    def fake_load() -> Settings:
        return Settings(
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "out",
            descriptions_dir=tmp_path / "out" / "descriptions",
        )

    monkeypatch.setattr(config, "load_settings", fake_load)
    monkeypatch.setattr("routers.cache.load_settings", fake_load)
    reset_session()
    from main import app

    client = TestClient(app)
    assert client.get("/api/cache/videos").status_code == 200
    assert client.get("/api/cache/videos").json() == {"videos": []}
    assert client.get("/api/cache/status").status_code == 400
    assert (
        client.get("/api/cache/status", params={"url": "https://example.com/v"}).json()["cached"] is False
    )


def test_cached_videos_list_includes_title(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)

    def fake_load() -> Settings:
        return Settings(
            cache_dir=cache_dir,
            output_dir=tmp_path / "out",
            descriptions_dir=tmp_path / "out" / "descriptions",
        )

    monkeypatch.setattr(config, "load_settings", fake_load)
    monkeypatch.setattr("routers.cache.load_settings", fake_load)
    from services.cache import save_url_registry_entry, save_video_title, url_cache_key

    url = "https://www.youtube.com/watch?v=abc"
    key = url_cache_key(url)
    (cache_dir / f"{key}.mp4").write_bytes(b"fakevid")
    save_url_registry_entry(cache_dir, url)
    save_video_title(cache_dir, url, "Knee Cut Defense")

    from main import app

    client = TestClient(app)
    videos = client.get("/api/cache/videos").json()["videos"]
    assert len(videos) == 1
    assert videos[0]["title"] == "Knee Cut Defense"
    assert videos[0]["url"] == url


def test_cache_preview_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)

    def fake_load() -> Settings:
        return Settings(
            cache_dir=cache_dir,
            output_dir=tmp_path / "out",
            descriptions_dir=tmp_path / "out" / "descriptions",
        )

    monkeypatch.setattr(config, "load_settings", fake_load)
    monkeypatch.setattr("routers.cache.load_settings", fake_load)
    from services.cache import save_url_registry_entry, url_cache_key

    url = "https://example.com/watch?v=preview"
    key = url_cache_key(url)
    (cache_dir / f"{key}.mp4").write_bytes(b"fakevid")
    save_url_registry_entry(cache_dir, url)

    from main import app

    client = TestClient(app)
    prev = client.get(f"/api/cache/preview/{key}")
    assert prev.status_code == 200
    assert prev.headers["content-type"].startswith("video/mp4")

    assert client.delete(f"/api/cache/videos/{key}").status_code == 200
    assert not (cache_dir / f"{key}.mp4").exists()
    assert client.get(f"/api/cache/preview/{key}").status_code == 404


def test_delete_session_clips(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    reset_session()
    from main import app
    from services.session import add_session_clip

    add_session_clip(
        {
            "filename": "a.mp4",
            "start": "0",
            "end": "1",
            "source_url": "https://x",
            "play_url": "/api/clip-file/a.mp4",
        }
    )
    client = TestClient(app)
    assert client.get("/api/clips").json()["clips"]
    assert client.delete("/api/clips").status_code == 200
    assert client.get("/api/clips").json() == {"clips": []}
