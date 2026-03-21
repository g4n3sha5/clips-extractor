from __future__ import annotations

import urllib.parse
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import load_settings
from models import ClipExtractRequest, ClipItem, ClipListResponse, SessionClearResponse
from services.cache import cached_video_path, get_video_title, is_valid_cache_file
from services import clip as clip_service
from services.session import add_session_clip, clear_session_clips, get_instructional_url, get_session_clips

router = APIRouter()


def _safe_output_basename(name: str) -> str:
    base = Path(name.strip()).name
    if base.lower().endswith(".mp4"):
        stem = base[:-4]
    else:
        stem = base
    stem = clip_service.sanitize_filename_stem(stem)
    return f"{stem}.mp4"


@router.get("/clips", response_model=ClipListResponse)
def list_clips() -> ClipListResponse:
    return ClipListResponse(clips=[ClipItem(**c) for c in get_session_clips()])


@router.delete("/clips", response_model=SessionClearResponse)
def delete_session_clips() -> SessionClearResponse:
    clear_session_clips()
    return SessionClearResponse()


@router.post("/clips", response_model=ClipItem)
async def extract_clip(body: ClipExtractRequest) -> ClipItem:
    url = (body.url or "").strip() or get_instructional_url()
    if not url:
        raise HTTPException(status_code=400, detail="No instructional URL. Load a URL first.")

    settings = load_settings()
    cached = cached_video_path(settings.cache_dir, url)
    if not is_valid_cache_file(cached):
        raise HTTPException(
            status_code=409,
            detail="Video is not cached yet. Click Load and wait for download to finish.",
        )

    try:
        start_sec = clip_service.parse_timestamp(body.start)
        end_sec = clip_service.parse_timestamp(body.end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    out_name = _safe_output_basename(body.filename)
    output_mp4 = settings.output_dir / out_name

    try:
        await clip_service.extract_clip_encoded(
            cached,
            output_mp4,
            start_sec,
            end_sec,
            crf=settings.clip_crf,
            preset=settings.clip_preset,
            audio_kbps=settings.clip_audio_kbps,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

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
    json_path = output_mp4.with_suffix(".json")
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
    return ClipItem(**item)


@router.get("/clip-file/{filename}")
def serve_clip_file(filename: str) -> FileResponse:
    """Serve extracted clips so the browser can open/play them (SESS-02)."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    name = Path(filename).name
    settings = load_settings()
    path = settings.output_dir / name
    try:
        path.resolve().relative_to(settings.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="video/mp4", filename=name)
