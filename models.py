from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    cache_dir: Path
    output_dir: Path
    clip_crf: int
    clip_preset: str
    clip_audio_kbps: int


class ConfigUpdate(BaseModel):
    cache_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    clip_crf: Optional[int] = Field(None, ge=18, le=51)
    clip_preset: Optional[str] = None
    clip_audio_kbps: Optional[int] = Field(None, ge=32, le=320)


class InstructionalBody(BaseModel):
    url: str = Field(..., min_length=1)


class InstructionalResponse(BaseModel):
    url: Optional[str] = None


class DownloadJobResponse(BaseModel):
    job_id: str


class ClipExtractRequest(BaseModel):
    start: str = Field(..., min_length=1)
    end: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    url: Optional[str] = None


class ClipItem(BaseModel):
    filename: str
    start: str
    end: str
    source_url: str
    play_url: str


class ClipListResponse(BaseModel):
    clips: List[ClipItem]


class CacheStatusResponse(BaseModel):
    cached: bool
    size_bytes: Optional[int] = None
    cache_key: Optional[str] = None


class CachedVideoItem(BaseModel):
    cache_key: str
    size_bytes: int
    modified: int
    url: Optional[str] = None


class CachedVideosResponse(BaseModel):
    videos: List[CachedVideoItem]


class CacheDeleteResponse(BaseModel):
    ok: bool = True


class SessionClearResponse(BaseModel):
    ok: bool = True
