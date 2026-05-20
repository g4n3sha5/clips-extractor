from __future__ import annotations

import urllib.parse
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from config import load_settings
from models import (
    ClipExtractRequest,
    ClipItem,
    ClipListResponse,
    ClipQueuedResponse,
    SessionClearResponse,
)
from services.cache import cached_video_path, is_valid_cache_file
from services.clip_queue import enqueue, pending_count
from services.download import is_download_in_progress
from services.extract_clip import extract_clip_request
from services.session import clear_session_clips, get_instructional_url, get_session_clips

router = APIRouter()


@router.get("/clips", response_model=ClipListResponse)
def list_clips() -> ClipListResponse:
    return ClipListResponse(clips=[ClipItem(**c) for c in get_session_clips()])


@router.delete("/clips", response_model=SessionClearResponse)
def delete_session_clips() -> SessionClearResponse:
    clear_session_clips()
    return SessionClearResponse()


@router.post("/clips", response_model=ClipItem)
async def extract_clip(body: ClipExtractRequest):
    url = (body.url or "").strip() or get_instructional_url()
    if not url:
        raise HTTPException(status_code=400, detail="No instructional URL. Load a URL first.")

    settings = load_settings()
    cached = cached_video_path(settings.cache_dir, url)
    if not is_valid_cache_file(cached):
        position = enqueue(url, body.model_dump())
        downloading = is_download_in_progress(url)
        msg = (
            "Clip queued — will extract when the download finishes."
            if downloading
            else "Clip queued — start or wait for the video download, then it will extract automatically."
        )
        payload = ClipQueuedResponse(position=position, message=msg)
        return JSONResponse(status_code=202, content=payload.model_dump())

    try:
        return await extract_clip_request(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/clips/queue")
def clip_queue_status(url: str) -> dict:
    """How many clips are waiting for this URL's cache file."""
    if not url.strip():
        raise HTTPException(status_code=400, detail="url query parameter required")
    return {"pending": pending_count(url), "downloading": is_download_in_progress(url)}


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
