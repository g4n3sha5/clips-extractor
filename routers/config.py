from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException

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
    if body.descriptions_dir is not None:
        updates["descriptions_dir"] = body.descriptions_dir
    if body.clip_crf is not None:
        updates["clip_crf"] = body.clip_crf
    if body.clip_preset is not None:
        updates["clip_preset"] = body.clip_preset.strip() or settings.clip_preset
    if body.clip_audio_kbps is not None:
        updates["clip_audio_kbps"] = body.clip_audio_kbps
    if body.proxy_url is not None:
        p = body.proxy_url.strip() if isinstance(body.proxy_url, str) else ""
        updates["proxy_url"] = p or None
    if body.bilibili_use_login is not None:
        updates["bilibili_use_login"] = body.bilibili_use_login
    if body.bilibili_cookies_browser is not None:
        b = body.bilibili_cookies_browser.strip() if body.bilibili_cookies_browser else None
        updates["bilibili_cookies_browser"] = b or None
    if body.bilibili_cookies_file is not None:
        updates["bilibili_cookies_file"] = body.bilibili_cookies_file
    if updates:
        settings = settings.model_copy(update=updates)
        save_settings(settings)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.descriptions_dir.mkdir(parents=True, exist_ok=True)
    return settings


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "ffmpeg": bool(shutil.which("ffmpeg"))}


@router.post("/config/open-output-dir")
def open_output_dir() -> dict[str, Any]:
    """Open the configured output folder in the user's file browser."""
    settings = load_settings()
    path = settings.output_dir
    path.mkdir(parents=True, exist_ok=True)

    system = platform.system()
    if system == "Darwin":
        cmd = ["open", str(path)]
    elif system == "Windows":
        cmd = ["explorer", str(path)]
    else:
        cmd = ["xdg-open", str(path)]

    try:
        subprocess.Popen(cmd)  # noqa: S603 — fixed command list, path from validated settings
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"File browser command not found: {cmd[0]}",
        ) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"ok": True, "path": str(path)}
