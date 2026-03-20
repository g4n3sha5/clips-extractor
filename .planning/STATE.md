# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.
**Current focus:** v1.1 — Phase 5: Dark UI Overhaul

## Current Position

Phase: 5 of 7 (Dark UI Overhaul)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-20 — v1.1 roadmap created (Phases 5–7)

Progress: [####------] 40% (v1 complete, v1.1 not started)

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

### Pending Todos

- Optional: move `pytest` to dev dependency group; split formal plan docs for Phases 2–4 if desired

### Blockers/Concerns

- Bilibili may require verification/captcha in some regions — yt-dlp errors surface in the SSE status line
- Host must have `ffmpeg` installed for extraction (see README)
- Timeline scrubber (Phase 7) requires the browser to have access to video duration metadata — ensure cached video path is served or duration is returned from the API

## Session Continuity

Last session: 2026-03-20
Stopped at: v1.1 roadmap created — Phases 5, 6, 7 defined
Resume file: .planning/ROADMAP.md
