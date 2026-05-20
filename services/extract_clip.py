from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any

from config import load_settings
from models import ClipExtractRequest, ClipItem
from services.cache import cached_video_path, get_video_title, is_valid_cache_file
from services import clip as clip_service
from services.session import add_session_clip, get_instructional_url


def _safe_output_basename(name: str) -> str:
    base = Path(name.strip()).name
    if base.lower().endswith(".mp4"):
        stem = base[:-4]
    else:
        stem = base
    stem = clip_service.sanitize_filename_stem(stem)
    return f"{stem}.mp4"


async def extract_clip_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract one clip and append to the session list. Raises on validation/ffmpeg errors."""
    body = ClipExtractRequest(**payload)
    url = (body.url or "").strip() or get_instructional_url()
    if not url:
        raise ValueError("No instructional URL")

    settings = load_settings()
    cached = cached_video_path(settings.cache_dir, url)
    if not is_valid_cache_file(cached):
        raise ValueError("Video is not cached yet")

    start_sec = clip_service.parse_timestamp(body.start)
    end_sec = clip_service.parse_timestamp(body.end)

    out_name = _safe_output_basename(body.filename)
    output_mp4 = settings.output_dir / out_name

    await clip_service.extract_clip_encoded(
        cached,
        output_mp4,
        start_sec,
        end_sec,
        crf=settings.clip_crf,
        preset=settings.clip_preset,
        audio_kbps=settings.clip_audio_kbps,
    )

    encode_meta = clip_service.encode_options_for_sidecar(
        crf=settings.clip_crf,
        preset=settings.clip_preset,
        audio_kbps=settings.clip_audio_kbps,
    )
    description = clip_service.format_clip_description(
        video_title=get_video_title(settings.cache_dir, url),
        start=body.start.strip(),
        end=body.end.strip(),
        fallback_url=url,
    )
    meta = clip_service.build_metadata_sidecar(
        source_url=url,
        start=body.start.strip(),
        end=body.end.strip(),
        filename_stem=Path(out_name).stem,
        description=description,
        output_filename=out_name,
        encode=encode_meta,
    )
    settings.descriptions_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.descriptions_dir / f"{Path(out_name).stem}.json"
    clip_service.write_sidecar_json(json_path, meta)

    play_path = f"/api/clip-file/{urllib.parse.quote(out_name)}"
    item = {
        "filename": out_name,
        "start": body.start.strip(),
        "end": body.end.strip(),
        "source_url": url,
        "play_url": play_path,
    }
    add_session_clip(item)
    return item


async def extract_clip_request(body: ClipExtractRequest) -> ClipItem:
    item = await extract_clip_from_payload(body.model_dump())
    return ClipItem(**item)
