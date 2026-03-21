from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

CONFIG_PATH = Path.home() / ".drillclips" / "config.json"


class Settings(BaseSettings):
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".drillclips" / "cache")
    output_dir: Path = Field(default_factory=lambda: Path("clips").resolve())
    # Clips: re-encode for smaller files (vs stream-copy). Tune via ~/.drillclips/config.json
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


def load_settings() -> Settings:
    if CONFIG_PATH.exists():
        return Settings.model_validate_json(CONFIG_PATH.read_text())
    return Settings()


def save_settings(settings: Settings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(settings.model_dump_json(indent=2))
