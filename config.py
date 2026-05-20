import sys
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

# All app config lives next to this file (project root), not under ~/.drillclips/.
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"


def _default_cache_dir() -> Path:
    return PROJECT_ROOT / "cache"


def _default_output_dir() -> Path:
    return PROJECT_ROOT / "clips"


def _default_descriptions_dir() -> Path:
    return _default_output_dir() / "descriptions"


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _path_for_storage(path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return resolved


class Settings(BaseSettings):
    cache_dir: Path = Field(default_factory=_default_cache_dir)
    output_dir: Path = Field(default_factory=_default_output_dir)
    descriptions_dir: Path = Field(default_factory=_default_descriptions_dir)
    clip_crf: int = Field(
        default=26,
        ge=18,
        le=51,
        description="libx264 CRF (higher = smaller file, lower = better quality)",
    )
    clip_preset: str = Field(
        default="medium",
        description="libx264 preset (slower presets squeeze more at same CRF)",
    )
    clip_audio_kbps: int = Field(
        default=96,
        ge=32,
        le=320,
        description="AAC audio bitrate (kb/s); 96 is fine for speech",
    )
    proxy_url: Optional[str] = Field(
        default=None,
        description="HTTP/SOCKS proxy, e.g. http://127.0.0.1:7890",
    )
    bilibili_use_login: bool = Field(
        default=False,
        description="Use browser cookies for Bilibili (logged-in / region-locked videos)",
    )
    bilibili_cookies_browser: Optional[str] = Field(
        default=None,
        description="Browser for cookiesfrombrowser when bilibili_use_login is true",
    )
    bilibili_cookies_file: Optional[Path] = Field(
        default=None,
        description="Optional Netscape cookies.txt (used when login enabled or path set)",
    )


def _normalize_settings(settings: Settings) -> Settings:
    cookies_file = settings.bilibili_cookies_file
    return settings.model_copy(
        update={
            "cache_dir": _resolve_path(settings.cache_dir),
            "output_dir": _resolve_path(settings.output_dir),
            "descriptions_dir": _resolve_path(settings.descriptions_dir),
            "bilibili_cookies_file": _resolve_path(cookies_file) if cookies_file else None,
        }
    )


def load_settings() -> Settings:
    if CONFIG_PATH.is_file():
        settings = Settings.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        settings = Settings()
    return _normalize_settings(settings)


def save_settings(settings: Settings) -> None:
    normalized = _normalize_settings(settings)
    payload = normalized.model_copy(
        update={
            "cache_dir": _path_for_storage(normalized.cache_dir),
            "output_dir": _path_for_storage(normalized.output_dir),
            "descriptions_dir": _path_for_storage(normalized.descriptions_dir),
            "bilibili_cookies_file": (
                _path_for_storage(normalized.bilibili_cookies_file)
                if normalized.bilibili_cookies_file
                else None
            ),
        }
    )
    CONFIG_PATH.write_text(payload.model_dump_json(indent=2) + "\n", encoding="utf-8")
