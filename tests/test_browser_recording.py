from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import config
from config import Settings
from fastapi.testclient import TestClient
from services.session import get_session_clips, reset_session


def _make_tiny_webm(path: Path) -> None:
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
            "testsrc=size=160x90:rate=5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.4",
            "-t",
            "0.4",
            "-c:v",
            "libvpx-vp9",
            "-c:a",
            "libopus",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip(f"could not create test webm: {proc.stderr}")


@pytest.fixture
def recording_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    out = tmp_path / "out"
    desc = out / "descriptions"
    cache = tmp_path / "cache"

    def fake_load() -> Settings:
        return Settings(cache_dir=cache, output_dir=out, descriptions_dir=desc)

    monkeypatch.setattr(config, "load_settings", fake_load)
    monkeypatch.setattr("services.browser_recording.load_settings", fake_load)
    reset_session()
    from main import app

    return TestClient(app), out


def test_from_recording_imports_clip(recording_client, tmp_path):
    client, out_dir = recording_client
    webm = tmp_path / "sample.webm"
    _make_tiny_webm(webm)

    with webm.open("rb") as f:
        response = client.post(
            "/api/clips/from-recording",
            data={
                "filename": "drill-test",
                "start": "0:00",
                "end": "0:01",
                "source_url": "https://www.bilibili.com/video/BVtest?p=1",
            },
            files={"file": ("sample.webm", f, "video/webm")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["filename"] == "drill-test.mp4"
    assert body["source_url"] == "https://www.bilibili.com/video/BVtest?p=1"
    assert (out_dir / "drill-test.mp4").is_file()
    clips = get_session_clips()
    assert len(clips) == 1
    assert clips[0]["filename"] == "drill-test.mp4"


def test_from_recording_rejects_empty_file(recording_client):
    client, _ = recording_client
    response = client.post(
        "/api/clips/from-recording",
        data={
            "filename": "x",
            "start": "0",
            "end": "1",
            "source_url": "https://example.com/v",
        },
        files={"file": ("empty.webm", b"", "video/webm")},
    )
    assert response.status_code == 400


def test_from_recording_rejects_empty_filename(recording_client, tmp_path):
    client, _ = recording_client
    webm = tmp_path / "sample.webm"
    _make_tiny_webm(webm)
    with webm.open("rb") as f:
        response = client.post(
            "/api/clips/from-recording",
            data={
                "filename": "   ",
                "start": "0",
                "end": "1",
                "source_url": "https://example.com/v",
            },
            files={"file": ("sample.webm", f, "video/webm")},
        )
    assert response.status_code == 400
