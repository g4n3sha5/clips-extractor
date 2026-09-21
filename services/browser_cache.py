from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from config import load_settings
from services.cache import (
    cache_status_for_url,
    cached_video_path,
    is_valid_cache_file,
    save_url_registry_entry,
    save_video_title,
)
from services.download import _lock_for_url
from services.session import set_instructional_url
from services.url_parse import canonical_instructional_url


def _suffix_for_name(name: str, fallback: str) -> str:
    suffix = Path(name or "").suffix.lower()
    if suffix in {".mp4", ".m4s", ".m4a", ".webm", ".mkv", ".mov", ".flv"}:
        return suffix
    return fallback


def _temp_path(cache_dir: Path, prefix: str, suffix: str) -> Path:
    fd, raw = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=cache_dir)
    os.close(fd)
    return Path(raw)


async def _run_ffmpeg(args: list[str]) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH; install ffmpeg to import browser downloads.")
    proc = await asyncio.create_subprocess_exec(
        ffmpeg,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        msg = stderr.decode(errors="replace").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"ffmpeg failed: {msg}")


async def mux_browser_streams(
    video_path: Path,
    audio_path: Optional[Path],
    output_mp4: Path,
    *,
    crf: int,
    preset: str,
    audio_kbps: int,
) -> None:
    """Mux browser-captured DASH/progressive streams into a cached H.264 MP4."""
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    partial = output_mp4.with_suffix(".partial.mp4")
    if partial.exists():
        partial.unlink()

    copy_args = [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
    ]
    if audio_path:
        copy_args += ["-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0"]
    copy_args += ["-c", "copy", "-movflags", "+faststart", str(partial)]

    try:
        await _run_ffmpeg(copy_args)
    except RuntimeError:
        audio_kbps = max(32, min(320, int(audio_kbps)))
        encode_args = [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
        ]
        if audio_path:
            encode_args += ["-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0"]
        encode_args += [
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_kbps}k",
            "-movflags",
            "+faststart",
            str(partial),
        ]
        await _run_ffmpeg(encode_args)

    if not is_valid_cache_file(partial):
        raise RuntimeError("ffmpeg produced an empty cache file")
    partial.replace(output_mp4)


async def save_upload_to_path(upload_file, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with dest.open("wb") as out:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            written += len(chunk)
    return written


async def import_browser_streams(
    *,
    video_path: Path,
    audio_path: Optional[Path],
    source_url: str,
    title: str = "",
) -> dict:
    url = canonical_instructional_url(source_url)
    if not url:
        raise ValueError("source_url is required")
    if not video_path.is_file() or video_path.stat().st_size <= 0:
        raise ValueError("Empty video upload")

    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = cached_video_path(settings.cache_dir, url)

    lock = _lock_for_url(url)
    async with lock:
        if not is_valid_cache_file(out_path):
            await mux_browser_streams(
                video_path,
                audio_path,
                out_path,
                crf=settings.clip_crf,
                preset=settings.clip_preset,
                audio_kbps=settings.clip_audio_kbps,
            )
            save_url_registry_entry(settings.cache_dir, url)
            if title.strip():
                save_video_title(settings.cache_dir, url, title.strip())
            from services.clip_queue import process_pending_for_url

            await process_pending_for_url(url)

    set_instructional_url(url)
    status = cache_status_for_url(settings.cache_dir, url)
    if not status.get("cached"):
        raise RuntimeError("Import finished but cache file is missing or empty.")
    return {
        "cached": True,
        "cache_key": status["cache_key"],
        "size_bytes": status["size_bytes"],
        "url": url,
        "title": title.strip() or None,
    }


async def save_uploads_and_import(
    *,
    video_file,
    audio_file,
    source_url: str,
    title: str = "",
) -> dict:
    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    video_tmp = _temp_path(
        settings.cache_dir,
        "browser_vid_",
        _suffix_for_name(video_file.filename or "", ".mp4"),
    )
    audio_tmp: Optional[Path] = None
    try:
        if await save_upload_to_path(video_file, video_tmp) <= 0:
            raise ValueError("Empty video upload")
        if audio_file is not None and audio_file.filename:
            audio_tmp = _temp_path(
                settings.cache_dir,
                "browser_aud_",
                _suffix_for_name(audio_file.filename or "", ".m4a"),
            )
            if await save_upload_to_path(audio_file, audio_tmp) <= 0:
                audio_tmp.unlink(missing_ok=True)
                audio_tmp = None
        return await import_browser_streams(
            video_path=video_tmp,
            audio_path=audio_tmp,
            source_url=source_url,
            title=title,
        )
    finally:
        video_tmp.unlink(missing_ok=True)
        if audio_tmp is not None:
            audio_tmp.unlink(missing_ok=True)
