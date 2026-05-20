from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from config import load_settings
from models import CacheDeleteResponse, CacheStatusResponse, CachedVideoItem, CachedVideosResponse
from services.cache import cache_status_for_url, delete_cached_video, is_valid_cache_key, list_cached_videos

router = APIRouter()


@router.get("/cache/status", response_model=CacheStatusResponse)
def get_cache_status(url: Optional[str] = Query(None, description="Instructional URL; defaults to session URL")) -> CacheStatusResponse:
    from services.session import get_instructional_url

    settings = load_settings()
    resolved = (url or "").strip() or (get_instructional_url() or "").strip()
    if not resolved:
        raise HTTPException(status_code=400, detail="Pass url= or set instructional URL first.")
    data = cache_status_for_url(settings.cache_dir, resolved)
    return CacheStatusResponse(**data)


@router.get("/cache/videos", response_model=CachedVideosResponse)
def get_cached_videos() -> CachedVideosResponse:
    settings = load_settings()
    raw = list_cached_videos(settings.cache_dir)
    videos = [
        CachedVideoItem(
            cache_key=x["cache_key"],
            size_bytes=x["size_bytes"],
            modified=x["modified"],
            url=x.get("url"),
            title=x.get("title"),
        )
        for x in raw
    ]
    return CachedVideosResponse(videos=videos)


@router.get("/cache/preview/{cache_key}")
def get_cache_preview(cache_key: str) -> FileResponse:
    """Serve a cached source .mp4 for in-browser duration / timeline scrubbing (TL-01)."""
    if not is_valid_cache_key(cache_key):
        raise HTTPException(status_code=400, detail="Invalid cache key.")
    settings = load_settings()
    path = settings.cache_dir / f"{cache_key}.mp4"
    try:
        path.resolve().relative_to(settings.cache_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not cached")
    return FileResponse(path, media_type="video/mp4")


@router.delete("/cache/videos/{cache_key}", response_model=CacheDeleteResponse)
def remove_cached_video(cache_key: str) -> CacheDeleteResponse:
    settings = load_settings()
    if not is_valid_cache_key(cache_key):
        raise HTTPException(status_code=400, detail="Invalid cache key.")
    ok = delete_cached_video(settings.cache_dir, cache_key)
    if not ok:
        raise HTTPException(status_code=404, detail="No cached file for this key.")
    return CacheDeleteResponse(ok=True)
