from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config import load_settings
from models import DownloadJobResponse
from services.download import ensure_cached_with_progress
from services.session import get_instructional_url

router = APIRouter()

# Single-user local tool: job_id -> queue of SSE payloads
_download_jobs: dict[str, asyncio.Queue] = {}


async def _run_download_job(job_id: str) -> None:
    queue = _download_jobs.get(job_id)
    if queue is None:
        return
    url = get_instructional_url()
    if not url:
        await queue.put({"type": "error", "message": "No instructional URL set. Paste a URL first."})
        return
    settings = load_settings()
    try:
        await ensure_cached_with_progress(url, settings.cache_dir, queue)
    except Exception as e:
        await queue.put({"type": "error", "message": str(e)})


@router.post("/download", response_model=DownloadJobResponse)
async def start_download() -> DownloadJobResponse:
    if not get_instructional_url():
        raise HTTPException(status_code=400, detail="Set instructional URL first (Load).")
    job_id = str(uuid.uuid4())
    _download_jobs[job_id] = asyncio.Queue()
    asyncio.create_task(_run_download_job(job_id))
    return DownloadJobResponse(job_id=job_id)


@router.get("/download/stream/{job_id}")
async def download_stream(job_id: str) -> StreamingResponse:
    if job_id not in _download_jobs:
        raise HTTPException(status_code=404, detail="Unknown job_id")

    async def event_gen():
        queue = _download_jobs[job_id]
        try:
            while True:
                item: dict[str, Any] = await queue.get()
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
        finally:
            _download_jobs.pop(job_id, None)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
