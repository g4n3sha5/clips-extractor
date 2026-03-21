from __future__ import annotations

import asyncio
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def parse_timestamp(s: str) -> float:
    """Parse M:SS, MM:SS, or H:MM:SS into seconds."""
    text = s.strip()
    if not text:
        raise ValueError("Empty timestamp")
    parts = text.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Invalid timestamp: {s!r}")


def sanitize_filename_stem(name: str) -> str:
    stem = Path(name.strip()).name
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    stem = stem.strip("._") or "clip"
    return stem


def format_clip_description(
    *,
    video_title: str,
    start: str,
    end: str,
    fallback_url: str,
) -> str:
    """Sidecar description: video title (or URL if title unknown), then start–end range."""
    name = (video_title or "").strip() or (fallback_url or "").strip() or "Video"
    return f"{name}\n{start.strip()} – {end.strip()}"


def build_metadata_sidecar(
    *,
    source_url: str,
    start: str,
    end: str,
    filename_stem: str,
    description: str,
    output_filename: str,
    encode: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "source_url": source_url,
        "start": start,
        "end": end,
        "filename_stem": filename_stem,
        "description": description,
        "output_file": output_filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if encode:
        meta["encode"] = encode
    return meta


def encode_options_for_sidecar(*, crf: int, preset: str, audio_kbps: int) -> dict[str, Any]:
    """Stored in JSON sidecar so you know how the clip was compressed."""
    return {
        "video": "libx264",
        "crf": crf,
        "preset": preset,
        "audio": "aac",
        "audio_kbps": audio_kbps,
    }


async def extract_clip_encoded(
    input_video: Path,
    output_mp4: Path,
    start_sec: float,
    end_sec: float,
    *,
    crf: int,
    preset: str,
    audio_kbps: int,
) -> None:
    """Cut a segment and re-encode to H.264 + AAC for much smaller files than stream-copy."""
    if end_sec <= start_sec:
        raise ValueError("End time must be after start time")

    duration = end_sec - start_sec
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
        "-ss",
        str(start_sec),
        "-i",
        str(input_video),
        "-t",
        str(duration),
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


def write_sidecar_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
