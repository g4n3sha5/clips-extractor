from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import config
from config import Settings
from fastapi.testclient import TestClient
from services.cache import cache_status_for_url, is_valid_cache_file
from services.session import get_instructional_url, reset_session


def _make_tiny_mp4(path: Path, *, audio: bool = True) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not on PATH")
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=160x90:rate=5",
    ]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.4"]
    cmd += [
        "-t",
        "0.4",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
    ]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "64k"]
    else:
        cmd += ["-an"]
    cmd.append(str(path))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip(f"could not create test mp4: {proc.stderr}")


def _make_tiny_audio(path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not on PATH")
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.4",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip(f"could not create test audio: {proc.stderr}")


@pytest.fixture
def browser_cache_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    out = tmp_path / "out"
    desc = out / "descriptions"
    cache = tmp_path / "cache"

    def fake_load() -> Settings:
        return Settings(cache_dir=cache, output_dir=out, descriptions_dir=desc)

    monkeypatch.setattr(config, "load_settings", fake_load)
    monkeypatch.setattr("services.browser_cache.load_settings", fake_load)
    reset_session()
    from main import app

    return TestClient(app), cache


def test_from_browser_caches_single_file(browser_cache_client, tmp_path):
    client, cache_dir = browser_cache_client
    video = tmp_path / "sample.mp4"
    _make_tiny_mp4(video)
    source = "https://www.bilibili.com/video/BV1VF421F7R3?p=5"

    with video.open("rb") as f:
        response = client.post(
            "/api/cache/from-browser",
            data={"source_url": source, "title": "Test instructional"},
            files={"video": ("sample.mp4", f, "video/mp4")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cached"] is True
    assert body["url"] == "https://www.bilibili.com/video/BV1VF421F7R3?p=5"
    assert body["title"] == "Test instructional"
    assert get_instructional_url() == body["url"]
    status = cache_status_for_url(cache_dir, source)
    assert status["cached"] is True
    assert is_valid_cache_file(cache_dir / f"{status['cache_key']}.mp4")


def test_from_browser_muxes_video_and_audio(browser_cache_client, tmp_path):
    client, cache_dir = browser_cache_client
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.m4a"
    _make_tiny_mp4(video, audio=False)
    _make_tiny_audio(audio)
    source = "https://www.bilibili.com/video/BV1TESTCACHE1?p=1"

    with video.open("rb") as vf, audio.open("rb") as af:
        response = client.post(
            "/api/cache/from-browser",
            data={"source_url": source, "title": "Muxed"},
            files={
                "video": ("video.mp4", vf, "video/mp4"),
                "audio": ("audio.m4a", af, "audio/mp4"),
            },
        )

    assert response.status_code == 200, response.text
    status = cache_status_for_url(cache_dir, source)
    assert status["cached"] is True


def test_from_browser_rejects_empty_video(browser_cache_client):
    client, _ = browser_cache_client
    response = client.post(
        "/api/cache/from-browser",
        data={"source_url": "https://www.bilibili.com/video/BVempty?p=1"},
        files={"video": ("empty.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400


def test_from_browser_is_idempotent_when_cached(browser_cache_client, tmp_path):
    client, cache_dir = browser_cache_client
    video = tmp_path / "sample.mp4"
    _make_tiny_mp4(video)
    source = "https://www.bilibili.com/video/BV1IDEMPOTENT1?p=1"

    with video.open("rb") as f:
        first = client.post(
            "/api/cache/from-browser",
            data={"source_url": source, "title": "Once"},
            files={"video": ("sample.mp4", f, "video/mp4")},
        )
    assert first.status_code == 200, first.text
    key = first.json()["cache_key"]
    first_size = (cache_dir / f"{key}.mp4").stat().st_size

    with video.open("rb") as f:
        second = client.post(
            "/api/cache/from-browser",
            data={"source_url": source, "title": "Twice"},
            files={"video": ("sample.mp4", f, "video/mp4")},
        )
    assert second.status_code == 200, second.text
    assert second.json()["cache_key"] == key
    assert (cache_dir / f"{key}.mp4").stat().st_size == first_size
