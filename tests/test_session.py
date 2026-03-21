"""Session persistence (SESS-03)."""

import json

from services.session import (
    add_session_clip,
    clear_session_memory_only,
    get_session_clips,
    load_session_from_disk,
    reset_session,
    session_store_path,
)


def test_add_session_clip_persists():
    reset_session()
    item = {
        "filename": "a.mp4",
        "start": "0",
        "end": "1",
        "source_url": "https://x",
        "play_url": "/api/clip-file/a.mp4",
    }
    add_session_clip(item)
    p = session_store_path()
    assert p.is_file()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["clips"] == [item]


def test_load_session_from_disk_restores_after_memory_clear():
    reset_session()
    item = {
        "filename": "a.mp4",
        "start": "0",
        "end": "1",
        "source_url": "https://x",
        "play_url": "/api/clip-file/a.mp4",
    }
    add_session_clip(item)
    clear_session_memory_only()
    assert get_session_clips() == []
    load_session_from_disk()
    assert get_session_clips() == [item]
