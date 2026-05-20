from __future__ import annotations

import asyncio
import shutil
import tempfile
import urllib.parse
from pathlib import Path

from config import load_settings
from services import clip as clip_service
from services.session import add_session_clip, get_instructional_url, set_instructional_url


def _safe_output_basename(name: str) -> str:
    base = Path(name.strip()).name
    if base.lower().endswith(".mp4"):
        stem = base[:-4]
    else:
        stem = base
    stem = clip_service.sanitize_filename_stem(stem)
    return f"{stem}.mp4"


async def transcode_recording_to_mp4(
    input_path: Path,
    output_mp4: Path,
    *,
    crf: int,
    preset: str,
    audio_kbps: int,
) -> None:
    """Re-encode a browser recording (webm/mp4) to H.264 + AAC."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH; install ffmpeg to extract clips.")

    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    audio_kbps = max(32, min(320, int(audio_kbps)))
    ab = f"{audio_kbps}k"

    proc = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
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
        ab,
        "-movflags",
        "+faststart",
        str(output_mp4),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        msg = stderr.decode(errors="replace").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"ffmpeg failed: {msg}")


async def import_browser_recording(
    *,
    upload_path: Path,
    filename: str,
    start: str,
    end: str,
    source_url: str,
) -> dict:
    """Transcode uploaded recording, write sidecar, append session clip."""
    start = start.strip()
    end = end.strip()
    source_url = source_url.strip()
    if not filename.strip():
        raise ValueError("filename is required")
    if not source_url:
        raise ValueError("source_url is required")
    if not start or not end:
        raise ValueError("start and end are required")

    clip_service.parse_timestamp(start)
    clip_service.parse_timestamp(end)

    settings = load_settings()
    out_name = _safe_output_basename(filename)
    output_mp4 = settings.output_dir / out_name

    await transcode_recording_to_mp4(
        upload_path,
        output_mp4,
        crf=settings.clip_crf,
        preset=settings.clip_preset,
        audio_kbps=settings.clip_audio_kbps,
    )

    if not get_instructional_url():
        set_instructional_url(source_url)

    encode_meta = clip_service.encode_options_for_sidecar(
        crf=settings.clip_crf,
        preset=settings.clip_preset,
        audio_kbps=settings.clip_audio_kbps,
    )
    description = clip_service.format_clip_description(
        video_title="",
        start=start,
        end=end,
        fallback_url=source_url,
    )
    meta = clip_service.build_metadata_sidecar(
        source_url=source_url,
        start=start,
        end=end,
        filename_stem=Path(out_name).stem,
        description=description,
        output_filename=out_name,
        encode={**encode_meta, "source": "browser_recording"},
    )
    settings.descriptions_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.descriptions_dir / f"{Path(out_name).stem}.json"
    clip_service.write_sidecar_json(json_path, meta)

    play_path = f"/api/clip-file/{urllib.parse.quote(out_name)}"
    item = {
        "filename": out_name,
        "start": start,
        "end": end,
        "source_url": source_url,
        "play_url": play_path,
    }
    add_session_clip(item)
    return item


async def save_upload_and_import(
    *,
    file_bytes: bytes,
    original_name: str,
    filename: str,
    start: str,
    end: str,
    source_url: str,
) -> dict:
    if not file_bytes:
        raise ValueError("Empty upload")

    suffix = Path(original_name or "recording.webm").suffix.lower()
    if suffix not in {".webm", ".mp4", ".mkv", ".mov"}:
        suffix = ".webm"

    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        dir=settings.cache_dir,
        prefix="browser_rec_",
    ) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        return await import_browser_recording(
            upload_path=tmp_path,
            filename=filename,
            start=start,
            end=end,
            source_url=source_url,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
