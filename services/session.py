from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import config


def session_store_path() -> Path:
    return config.CONFIG_PATH.parent / "session_clips.json"


_current_url: Optional[str] = None
_clips: list[dict[str, Any]] = []

_CLIP_KEYS = frozenset({"filename", "start", "end", "source_url", "play_url"})


def get_instructional_url() -> Optional[str]:
    return _current_url


def set_instructional_url(url: str) -> None:
    global _current_url
    normalized = url.strip()
    _current_url = normalized
    _persist()


def get_session_clips() -> list[dict[str, Any]]:
    return list(_clips)


def add_session_clip(item: dict[str, Any]) -> None:
    _clips.append(item)
    _persist()


def clear_session_clips() -> None:
    """Clear the clip list only (keeps current instructional URL)."""
    global _clips
    _clips = []
    _persist()


def reset_session() -> None:
    """Test helper: clear instructional URL, session clips, and persisted file."""
    global _current_url, _clips
    _current_url = None
    _clips = []
    p = session_store_path()
    try:
        if p.exists():
            p.unlink()
    except OSError:
        pass


def clear_session_memory_only() -> None:
    """Clear in-memory session without touching disk (for tests simulating restart)."""
    global _current_url, _clips
    _current_url = None
    _clips = []


def _persist() -> None:
    try:
        p = session_store_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "instructional_url": _current_url,
            "clips": _clips,
        }
        p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def load_session_from_disk() -> None:
    """Restore session from disk; call on app startup."""
    global _current_url, _clips
    _current_url = None
    _clips = []
    p = session_store_path()
    if not p.is_file():
        return
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(raw, dict):
        return
    url = raw.get("instructional_url")
    if isinstance(url, str) and url.strip():
        _current_url = url.strip()
    clips = raw.get("clips")
    if not isinstance(clips, list):
        return
    out: list[dict[str, Any]] = []
    for c in clips:
        if not isinstance(c, dict):
            continue
        if not _CLIP_KEYS.issubset(c.keys()):
            continue
        out.append({k: c[k] for k in _CLIP_KEYS})
    _clips = out
