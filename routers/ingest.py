"""Transcript ingest: title-aware ASR fix, cleanup, concept extract, save."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from config import load_settings, resolve_openai_api_key
from models import IngestListItem, IngestListResponse, IngestRequest, IngestResult
from services.ingest import list_ingests, load_ingest, process_ingest, save_ingest

router = APIRouter()


@router.post("/ingest", response_model=IngestResult)
async def create_ingest(body: IngestRequest) -> IngestResult:
    settings = load_settings()
    settings.ingest_dir.mkdir(parents=True, exist_ok=True)
    api_key = resolve_openai_api_key(settings)
    try:
        result = await process_ingest(
            title=body.title,
            transcript=body.transcript,
            api_key=api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            source_url=body.source_url,
            start=body.start,
            end=body.end,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    saved_path = None
    if body.save:
        path = save_ingest(result, settings.ingest_dir)
        saved_path = str(path)
    elif not result.get("id"):
        import uuid
        from services.ingest import _slug

        result["id"] = f"{_slug(result.get('title', ''))}-{uuid.uuid4().hex[:8]}"

    return IngestResult(**{**result, "saved_path": saved_path})


@router.get("/ingest", response_model=IngestListResponse)
def get_ingests() -> IngestListResponse:
    settings = load_settings()
    items = [IngestListItem(**row) for row in list_ingests(settings.ingest_dir)]
    return IngestListResponse(items=items)


@router.get("/ingest/{ingest_id}")
def get_ingest(ingest_id: str) -> dict[str, Any]:
    settings = load_settings()
    data = load_ingest(settings.ingest_dir, ingest_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Ingest not found")
    return data
