from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

_pending: dict[str, list[dict[str, Any]]] = defaultdict(list)
_queue_lock = asyncio.Lock()


def enqueue(url: str, payload: dict[str, Any]) -> int:
    """Queue a clip for extraction after the source video is cached. Returns 1-based position."""
    key = url.strip()
    _pending[key].append(payload)
    return len(_pending[key])


def pending_count(url: str) -> int:
    return len(_pending.get(url.strip(), []))


def take_pending(url: str) -> list[dict[str, Any]]:
    key = url.strip()
    items = _pending.pop(key, [])
    return items


async def process_pending_for_url(url: str) -> list[dict[str, Any]]:
    """Run all queued extractions for this URL. Returns session clip dicts that succeeded."""
    from services.extract_clip import extract_clip_from_payload

    async with _queue_lock:
        items = take_pending(url)
    if not items:
        return []

    results: list[dict[str, Any]] = []
    for payload in items:
        try:
            item = await extract_clip_from_payload(payload)
            results.append(item)
        except Exception:
            logger.exception("Queued clip extract failed for %s", url)
    return results
