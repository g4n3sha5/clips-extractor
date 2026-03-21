from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def url_cache_key(url: str) -> str:
    """Stable short key for cache filename (full URL hashed)."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]


def cached_video_path(cache_dir: Path, url: str) -> Path:
    return cache_dir / f"{url_cache_key(url)}.mp4"


def is_valid_cache_file(path: Path) -> bool:
    """DL-03: treat existing non-empty file as cache hit."""
    return path.is_file() and path.stat().st_size > 0


REGISTRY_FILENAME = "url_registry.json"
VIDEO_TITLES_FILENAME = "video_titles.json"


def _registry_path(cache_dir: Path) -> Path:
    return cache_dir / REGISTRY_FILENAME


def _video_titles_path(cache_dir: Path) -> Path:
    return cache_dir / VIDEO_TITLES_FILENAME


def load_video_titles(cache_dir: Path) -> dict[str, str]:
    """Map cache key (16-char hex stem) -> video title from yt-dlp."""
    path = _video_titles_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, str) and v.strip():
            out[k] = v.strip()
    return out


def save_video_title(cache_dir: Path, url: str, title: str) -> None:
    """Persist display title for a cached instructional (keyed by URL hash)."""
    normalized = url.strip()
    text = (title or "").strip()
    if not normalized or not text:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = url_cache_key(normalized)
    titles = load_video_titles(cache_dir)
    titles[key] = text
    _video_titles_path(cache_dir).write_text(
        json.dumps(dict(sorted(titles.items())), indent=2) + "\n",
        encoding="utf-8",
    )


def get_video_title(cache_dir: Path, url: str) -> str:
    """Return stored title for this URL, or empty string if unknown."""
    normalized = url.strip()
    if not normalized:
        return ""
    key = url_cache_key(normalized)
    return load_video_titles(cache_dir).get(key, "")


def load_url_registry(cache_dir: Path) -> dict[str, str]:
    """Map cache key (16-char hex stem) -> canonical URL."""
    path = _registry_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, str) and v.strip():
            out[k] = v.strip()
    return out


def save_url_registry_entry(cache_dir: Path, url: str) -> None:
    """Record which URL owns a cache file (idempotent merge)."""
    normalized = url.strip()
    if not normalized:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = url_cache_key(normalized)
    reg = load_url_registry(cache_dir)
    reg[key] = normalized
    _registry_path(cache_dir).write_text(
        json.dumps(dict(sorted(reg.items())), indent=2) + "\n",
        encoding="utf-8",
    )


def list_cached_videos(cache_dir: Path) -> list[dict[str, Any]]:
    """All non-empty .mp4 in cache_dir with optional URL from registry."""
    if not cache_dir.is_dir():
        return []
    reg = load_url_registry(cache_dir)
    items: list[dict[str, Any]] = []
    for mp4 in sorted(cache_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not is_valid_cache_file(mp4):
            continue
        key = mp4.stem
        st = mp4.stat()
        items.append(
            {
                "cache_key": key,
                "url": reg.get(key),
                "size_bytes": st.st_size,
                "modified": int(st.st_mtime),
            }
        )
    return items


_CACHE_KEY_RE = re.compile(r"^[a-f0-9]{16}$")


def is_valid_cache_key(cache_key: str) -> bool:
    return bool(cache_key and _CACHE_KEY_RE.match(cache_key))


def delete_cached_video(cache_dir: Path, cache_key: str) -> bool:
    """Remove a cached .mp4 and its registry entry. Returns True if a file was deleted."""
    if not is_valid_cache_key(cache_key):
        return False
    path = cache_dir / f"{cache_key}.mp4"
    if not path.is_file():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    reg = load_url_registry(cache_dir)
    if cache_key in reg:
        del reg[cache_key]
        p = _registry_path(cache_dir)
        if reg:
            p.write_text(json.dumps(dict(sorted(reg.items())), indent=2) + "\n", encoding="utf-8")
        elif p.is_file():
            p.unlink()
    titles = load_video_titles(cache_dir)
    if cache_key in titles:
        del titles[cache_key]
        tp = _video_titles_path(cache_dir)
        if titles:
            tp.write_text(json.dumps(dict(sorted(titles.items())), indent=2) + "\n", encoding="utf-8")
        elif tp.is_file():
            tp.unlink()
    return True


def cache_status_for_url(cache_dir: Path, url: str) -> dict[str, Any]:
    """Whether the URL has a local cache file and its size."""
    normalized = url.strip()
    if not normalized:
        return {"cached": False, "size_bytes": None, "cache_key": None}
    path = cached_video_path(cache_dir, normalized)
    key = url_cache_key(normalized)
    if not is_valid_cache_file(path):
        return {"cached": False, "size_bytes": None, "cache_key": key}
    return {"cached": True, "size_bytes": path.stat().st_size, "cache_key": key}
