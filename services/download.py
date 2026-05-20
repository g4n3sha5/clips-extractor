from __future__ import annotations

import asyncio
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import yt_dlp

from config import load_settings

from services.cache import (
    cached_video_path,
    is_valid_cache_file,
    save_url_registry_entry,
    save_video_title,
)
from services.bilibili_cookies import resolve_bilibili_cookie_file
from services.url_parse import canonical_instructional_url, is_bilibili_url

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


def is_download_in_progress(url: str) -> bool:
    """True while a download task holds the per-URL lock."""
    from services.cache import url_cache_key

    lock = _download_locks.get(url_cache_key(url))
    return lock is not None and lock.locked()


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


def _proxy_for_ydl() -> Optional[str]:
    settings = load_settings()
    if settings.proxy_url:
        p = str(settings.proxy_url).strip()
        if p:
            return p
    import os

    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("ALL_PROXY")


def _bilibili_download_attempts() -> List[tuple[Optional[str], Optional[str]]]:
    """Try without login first; add cookie attempts only when opted in."""
    settings = load_settings()
    attempts: List[tuple[Optional[str], Optional[str]]] = [(None, None)]

    manual = settings.bilibili_cookies_file
    if manual and manual.is_file():
        attempts.append((str(manual), None))

    if not settings.bilibili_use_login:
        return attempts

    cookie_path = resolve_bilibili_cookie_file(allow_auto_export=True)
    if cookie_path and (str(cookie_path), None) not in attempts:
        attempts.append((str(cookie_path), None))

    # Only the browser you picked — never fall back to Safari (macOS blocks cookie access).
    browser = (settings.bilibili_cookies_browser or "firefox").strip().lower()
    if browser:
        attempts.append((None, browser))
    return attempts


def _is_cookie_access_error(msg: str) -> bool:
    lower = msg.lower()
    return any(
        token in lower
        for token in (
            "cookie",
            "permission",
            "permitted",
            "binarycookies",
            "could not find",
            "no such file",
        )
    )


def _is_retriable_bilibili_error(msg: str) -> bool:
    lower = msg.lower()
    return any(
        token in lower
        for token in (
            "geo-restricted",
            "deleted",
            "login",
            "412",
            "precondition failed",
            "rate limit",
            "exceeded the rate",
            "anti",
            "blocked",
            "啥都木有",
        )
    )


def _apply_bilibili_opts(url: str, opts: dict[str, Any]) -> None:
    """Download only the ?p=N part, not the full series."""
    if not is_bilibili_url(url):
        return
    opts["noplaylist"] = True
    headers = dict(opts.get("http_headers") or {})
    headers.setdefault("Referer", url.split("?")[0] if "?" in url else url)
    opts["http_headers"] = headers


def _apply_cookie_opts(
    opts: dict[str, Any],
    cookiefile: Optional[str],
    browser: Optional[str],
) -> None:
    opts.pop("cookiefile", None)
    opts.pop("cookiesfrombrowser", None)
    if cookiefile:
        opts["cookiefile"] = cookiefile
    elif browser:
        opts["cookiesfrombrowser"] = (browser,)


def _friendly_bilibili_error(msg: str) -> str:
    lower = msg.lower()
    settings = load_settings()
    proxy_hint = ""
    if not _proxy_for_ydl():
        proxy_hint = (
            ' Optional: set a proxy under Settings (e.g. "http://127.0.0.1:7890") '
            "if you use a VPN — browser extensions do not apply to downloads."
        )
    if "412" in lower or "precondition" in lower or "rate limit" in lower:
        return (
            "Bilibili rate-limited this IP (412 / anti-scraping). "
            "Wait several minutes before retrying, avoid rapid repeated downloads, "
            "and use an optional proxy if needed."
            + proxy_hint
            + f" Details: {msg}"
        )
    if _is_retriable_bilibili_error(msg):
        login_hint = (
            " Enable “Bilibili login” in Settings if the video needs your account."
            if not settings.bilibili_use_login
            else " Check that you are logged in to bilibili.com in your browser."
        )
        return (
            "Bilibili blocked this download (region, login, or unavailable video)."
            + login_hint
            + proxy_hint
            + f" Details: {msg}"
        )
    return msg


def _ensure_single_bilibili_part(url: str, ydl: yt_dlp.YoutubeDL) -> None:
    """Refuse whole-series downloads; user must pick ?p=N for multi-part Bilibili URLs."""
    if not is_bilibili_url(url) or "p=" in url:
        return
    info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict) or info.get("_type") != "playlist":
        return
    count = info.get("playlist_count") or len(info.get("entries") or [])
    raise RuntimeError(
        f"This Bilibili link is a multi-part series ({count} videos). "
        "Open the part you want on Bilibili, copy that page’s URL (it should include ?p=N, e.g. ?p=10), "
        "and paste it here."
    )


def _sync_download_to_path(
    url: str,
    output_mp4: Path,
    progress_hook: Optional[Callable[[dict[str, Any]], None]],
) -> str:
    """Download to output_mp4; return video title from yt-dlp metadata (may be empty)."""
    url = canonical_instructional_url(url)
    if not url:
        raise RuntimeError("No valid video URL to download.")

    outtmpl = str(output_mp4.with_suffix("")) + ".%(ext)s"
    fmt, merge_mp4 = _format_and_merge_for_environment()
    opts: dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        # YouTube often returns CDN URLs that respond 403 for default TV/web clients
        # when using merged DASH; Android innertube first avoids that (other sites unchanged).
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "tv", "web_safari", "web"],
            },
        },
    }
    if merge_mp4:
        opts["merge_output_format"] = "mp4"
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    _apply_bilibili_opts(url, opts)
    proxy = _proxy_for_ydl()
    if proxy:
        opts["proxy"] = proxy
    if is_bilibili_url(url) and load_settings().bilibili_use_login:
        from services.bilibili_cookies import DEFAULT_COOKIE_PATH, export_firefox_bilibili_cookies

        export_firefox_bilibili_cookies(DEFAULT_COOKIE_PATH)

    attempts: List[tuple[Optional[str], Optional[str]]] = (
        _bilibili_download_attempts() if is_bilibili_url(url) else [(None, None)]
    )

    title = ""
    last_err: Optional[Exception] = None
    for cookiefile, browser in attempts:
        attempt_opts = dict(opts)
        _apply_cookie_opts(attempt_opts, cookiefile, browser)
        try:
            with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                _ensure_single_bilibili_part(url, ydl)
                info = ydl.extract_info(url, download=True)
                if isinstance(info, dict):
                    title = (info.get("title") or "").strip()
            last_err = None
            break
        except Exception as e:
            last_err = e
            msg = _strip_ansi(str(e))
            if browser and _is_cookie_access_error(msg):
                logger.warning("Bilibili cookie source %s failed: %s", browser, msg)
                continue
            if not shutil.which("ffmpeg") and "ffmpeg" in msg.lower():
                raise RuntimeError(
                    "ffmpeg is required to merge video+audio for this URL (common on Bilibili/YouTube). "
                    "Install ffmpeg and ensure it is on PATH, then try again. "
                    "macOS: brew install ffmpeg. Linux: apt install ffmpeg. "
                    f"Details: {msg}"
                ) from e
            if is_bilibili_url(url) and (cookiefile, browser) != attempts[-1]:
                if _is_retriable_bilibili_error(msg):
                    continue
            raise RuntimeError(_friendly_bilibili_error(msg)) from e

    if last_err is not None:
        msg = _strip_ansi(str(last_err))
        if not shutil.which("ffmpeg") and "ffmpeg" in msg.lower():
            raise RuntimeError(
                "ffmpeg is required to merge video+audio for this URL (common on Bilibili/YouTube). "
                "Install ffmpeg and ensure it is on PATH, then try again. "
                "macOS: brew install ffmpeg. Linux: apt install ffmpeg. "
                f"Details: {msg}"
            ) from last_err
        raise RuntimeError(_friendly_bilibili_error(msg)) from last_err

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
    url = canonical_instructional_url(url)
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
        from services.clip_queue import process_pending_for_url

        await process_pending_for_url(url)
    return out_path
