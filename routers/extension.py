from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from models import ClipItem
from services.browser_recording import save_upload_and_import

router = APIRouter()


@router.post("/clips/from-recording", response_model=ClipItem)
async def clip_from_recording(
    file: UploadFile = File(...),
    filename: str = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    source_url: str = Form(...),
) -> ClipItem:
    if not file.filename and not filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    data = await file.read()
    try:
        item = await save_upload_and_import(
            file_bytes=data,
            original_name=file.filename or "recording.webm",
            filename=filename,
            start=start,
            end=end,
            source_url=source_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ClipItem(**item)
