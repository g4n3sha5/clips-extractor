from __future__ import annotations

from fastapi import APIRouter

from config import load_settings
from models import InstructionalBody, InstructionalResponse
from services.cache import cached_video_path, is_valid_cache_file, save_url_registry_entry
from services.session import get_instructional_url, set_instructional_url

router = APIRouter()


@router.get("/instructional", response_model=InstructionalResponse)
def get_instructional() -> InstructionalResponse:
    return InstructionalResponse(url=get_instructional_url())


@router.post("/instructional", response_model=InstructionalResponse)
def post_instructional(body: InstructionalBody) -> InstructionalResponse:
    set_instructional_url(body.url)
    settings = load_settings()
    path = cached_video_path(settings.cache_dir, body.url)
    if is_valid_cache_file(path):
        save_url_registry_entry(settings.cache_dir, body.url)
    return InstructionalResponse(url=get_instructional_url())
