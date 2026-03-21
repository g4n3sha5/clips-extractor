from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import yt_dlp

from services.cache import (
    cached_video_path,
    is_valid_cache_file,
    save_url_registry_entry,
    save_video_title,
)

logger = logging.getLogger(__name__)

# 720p max. If ffmpeg is on PATH: mux video+audio (works for Bilibili/YouTube DASH).
# If not: prefer a single muxed MP4 (no merge) — many YouTube progressive streams work;
# some sites still need ffmpeg; user gets a clear error.
FFMPEG_MERGE_FORMAT = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
NO_MERGE_FORMAT = "best[height<=720][ext=mp4]/best[height<=720]/best"


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _format_and_merge_for_environment() -> Tuple[str, bool]:
    if shutil.which("ffmpeg"):
        return FFMPEG_MERGE_FORMAT, True
    return NO_MERGE_FORMAT, False

_download_locks: dict[str, asyncio.Lock] = {}


def _lock_for_url(url: str) -> asyncio.Lock:
    from services.cache import url_cache_key

    key = url_cache_key(url)
    if key not in _download_locks:
        _download_locks[key] = asyncio.Lock()
    return _download_locks[key]


def _progress_hook(
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> Callable[[dict[str, Any]], None]:
    def hook(d: dict[str, Any]) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes") or 0
            pct: Optional[float] = None
            if total:
                pct = round(downloaded / total * 100, 1)
            payload = {
                "type": "progress",
                "percent": pct,
                "downloaded": downloaded,
                "total": total,
            }
            try:
                loop.call_soon_threadsafe(queue.put_nowait, payload)
            except Exception:
                logger.exception("progress queue put failed")
        elif status == "finished":
            payload = {"type": "hook_finished", "info": str(d.get("filename", ""))}
            try:
                loop.call_soon_threadsafe(queue.put_nowait, payload)
            except Exception:
                logger.exception("progress queue put failed")

    return hook


def _sync_download_to_path(
    url: str,
    output_mp4: Path,
    progress_hook: Optional[Callable[[dict[str, Any]], None]],
) -> str:
    """Download to output_mp4; return video title from yt-dlp metadata (may be empty)."""
    outtmpl = str(output_mp4.with_suffix("")) + ".%(ext)s"
    fmt, merge_mp4 = _format_and_merge_for_environment()
    opts: dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
    }
    if merge_mp4:
        opts["merge_output_format"] = "mp4"
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    title = ""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if isinstance(info, dict):
                title = (info.get("title") or "").strip()
    except Exception as e:
        msg = _strip_ansi(str(e))
        if not shutil.which("ffmpeg") and "ffmpeg" in msg.lower():
            raise RuntimeError(
                "ffmpeg is required to merge video+audio for this URL (common on Bilibili/YouTube). "
                "Install ffmpeg and ensure it is on PATH, then try again. "
                "macOS: brew install ffmpeg. Linux: apt install ffmpeg. "
                f"Details: {msg}"
            ) from e
        raise

    if output_mp4.is_file():
        return title
    parent = output_mp4.parent
    stem = output_mp4.stem
    candidates = sorted(parent.glob(f"{stem}*.mp4"))
    if candidates:
        candidates[0].rename(output_mp4)
        return title
    raise RuntimeError("Download finished but expected mp4 not found in cache directory")


async def ensure_cached_with_progress(
    url: str,
    cache_dir: Path,
    queue: asyncio.Queue,
) -> Path:
    """Download if missing; stream progress events to queue. Returns path to cached mp4."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = cached_video_path(cache_dir, url)
    title_out: list[str] = []

    if is_valid_cache_file(out_path):
        save_url_registry_entry(cache_dir, url)
        await queue.put({"type": "done", "cached": True, "path": str(out_path)})
        return out_path

    lock = _lock_for_url(url)
    async with lock:
        if is_valid_cache_file(out_path):
            save_url_registry_entry(cache_dir, url)
            await queue.put({"type": "done", "cached": True, "path": str(out_path)})
            return out_path

        loop = asyncio.get_running_loop()

        def run_download() -> None:
            hook = _progress_hook(loop, queue)
            try:
                t = _sync_download_to_path(url, out_path, hook)
                title_out.append(t)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "done", "cached": False, "path": str(out_path)},
                )
            except Exception as e:
                logger.exception("yt-dlp download failed")
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "error", "message": _strip_ansi(str(e))},
                )

        await asyncio.to_thread(run_download)

    if not is_valid_cache_file(out_path):
        await queue.put(
            {
                "type": "error",
                "message": "Download finished but cache file is missing or empty.",
            }
        )
    else:
        save_url_registry_entry(cache_dir, url)
        if title_out:
            save_video_title(cache_dir, url, title_out[0])
    return out_path
