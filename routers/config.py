from __future__ import annotations

import shutil
from typing import Any

from fastapi import APIRouter

from config import load_settings, save_settings
from models import ConfigResponse, ConfigUpdate

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return load_settings()


@router.post("/config", response_model=ConfigResponse)
def update_config(body: ConfigUpdate) -> ConfigResponse:
    settings = load_settings()
    updates: dict = {}
    if body.cache_dir is not None:
        updates["cache_dir"] = body.cache_dir
    if body.output_dir is not None:
        updates["output_dir"] = body.output_dir
    if body.clip_crf is not None:
        updates["clip_crf"] = body.clip_crf
    if body.clip_preset is not None:
        updates["clip_preset"] = body.clip_preset.strip() or settings.clip_preset
    if body.clip_audio_kbps is not None:
        updates["clip_audio_kbps"] = body.clip_audio_kbps
    if updates:
        settings = settings.model_copy(update=updates)
        save_settings(settings)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "ffmpeg": bool(shutil.which("ffmpeg"))}
