# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.
**Current focus:** v1.1 shipped — Phases 5–7 complete

## Current Position

Phase: 7 of 7 (Timeline Scrubber) — v1.1 milestone complete
Plan: integrated delivery
Status: Complete
Last activity: 2026-03-20 — Phases 5–7 implemented (dark UI, cache panel + delete, timeline scrubber + preview API)

Progress: [##########] 100% (v1 + v1.1)

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (Phase 1 formal plans) + Phases 2–4 implemented as single delivery
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 2 | - | - |
| 2–4 | impl | - | - |

**Recent Trend:**
- Last 5 plans: 01-01, 01-02, full-stack v1
- Trend: Feature-complete for v1 requirements

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pre-roadmap: yt-dlp format string must be locked before cache is built (Opus/MP4 mux failure risk)
- Pre-roadmap: Use asyncio.to_thread() for yt-dlp to avoid blocking the FastAPI event loop
- Pre-roadmap: Always use asyncio.create_subprocess_exec with arg list (never shell=True) for ffmpeg

### Roadmap Evolution

- Phase 8 added: Queue clips while downloading, choose videos from local files, optional descriptions toggle

### Pending Todos

- Optional: move `pytest` to dev dependency group (requires `uv lock` or lockfile refresh); split formal plan docs for Phases 2–4 if desired

### Blockers/Concerns

- Bilibili may require verification/captcha in some regions — yt-dlp errors surface in the SSE status line
- Host must have `ffmpeg` installed for extraction (see README)
- ~~Timeline scrubber needs video duration~~ — addressed via `GET /api/cache/preview/{cache_key}` + browser `loadedmetadata`

## Session Continuity

Last session: 2026-03-20
Stopped at: v1.1 complete — see `.planning/phases/02-v1.1-ux/SUMMARY.md`
Resume file: .planning/ROADMAP.md
