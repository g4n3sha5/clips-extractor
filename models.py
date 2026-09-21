from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    cache_dir: Path
    output_dir: Path
    descriptions_dir: Path
    ingest_dir: Path = Path("ingest")
    clip_crf: int
    clip_preset: str
    clip_audio_kbps: int
    proxy_url: Optional[str] = None
    bilibili_use_login: bool = False
    bilibili_cookies_browser: Optional[str] = None
    bilibili_cookies_file: Optional[Path] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    has_openai_api_key: bool = False


class ConfigUpdate(BaseModel):
    cache_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    descriptions_dir: Optional[Path] = None
    ingest_dir: Optional[Path] = None
    clip_crf: Optional[int] = Field(None, ge=18, le=51)
    clip_preset: Optional[str] = None
    clip_audio_kbps: Optional[int] = Field(None, ge=32, le=320)
    proxy_url: Optional[str] = None
    bilibili_use_login: Optional[bool] = None
    bilibili_cookies_browser: Optional[str] = None
    bilibili_cookies_file: Optional[Path] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None


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


class ClipQueuedResponse(BaseModel):
    status: str = "queued"
    position: int
    message: str


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
    title: Optional[str] = None


class CachedVideosResponse(BaseModel):
    videos: List[CachedVideoItem]


class CacheDeleteResponse(BaseModel):
    ok: bool = True


class BrowserCacheResponse(BaseModel):
    cached: bool
    cache_key: str
    size_bytes: Optional[int] = None
    url: str
    title: Optional[str] = None


class SessionClearResponse(BaseModel):
    ok: bool = True


class IngestRequest(BaseModel):
    title: str = Field(..., min_length=1)
    transcript: str = Field(..., min_length=1)
    source_url: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    save: bool = True


class IngestListItem(BaseModel):
    id: str
    title: Optional[str] = None
    mode: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[str] = None
    path: Optional[str] = None


class IngestListResponse(BaseModel):
    items: List[IngestListItem]


class IngestResult(BaseModel):
    id: str
    title: str
    source_url: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    mode: str
    model: Optional[str] = None
    title_techniques: List[str] = Field(default_factory=list)
    corrections: List[Dict[str, Any]] = Field(default_factory=list)
    removed_fillers: List[Any] = Field(default_factory=list)
    cleaned_transcript: str = ""
    concepts: List[Dict[str, Any]] = Field(default_factory=list)
    techniques: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    created_at: str
    saved_path: Optional[str] = None
