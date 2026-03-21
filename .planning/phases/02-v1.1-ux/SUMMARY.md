# v1.1 UX Overhaul — Summary

**Completed:** 2026-03-20  
**Phases covered:** 5 (Dark UI + post-extract reset), 6 (Cache visibility), 7 (Timeline scrubber)

## Delivered

- **Phase 5:** Dark minimal UI (already in place); after successful extract: filename cleared, description template reset, scrubber range reset to full video when duration is known.
- **Phase 6:** Status pill text: Cached / Downloading / Not cached; **Cache library** panel (size, date, per-row delete); `DELETE /api/cache/videos/{cache_key}` + registry cleanup in `services/cache.py`.
- **Phase 7:** Hidden `<video preload="metadata">` via `GET /api/cache/preview/{cache_key}`; draggable in/out handles; two-way sync with Start/End fields.

## Verification

- `uv run pytest tests/ -v` (or `.venv/bin/python -m pytest tests/ -v`)

## Follow-ups (optional)

- Move `pytest` to a dev dependency group / extra when `uv lock` can be run locally.
- Formal plan markdowns for Phases 2–4 (v1) if documentation parity with Phase 1 is desired.
