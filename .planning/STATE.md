# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 4 (Foundation)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-19 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pre-roadmap: yt-dlp format string must be locked before cache is built (Opus/MP4 mux failure risk)
- Pre-roadmap: Use asyncio.to_thread() for yt-dlp to avoid blocking the FastAPI event loop
- Pre-roadmap: Always use asyncio.create_subprocess_exec with arg list (never shell=True) for ffmpeg

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: Bilibili anonymous 720p availability is unverified — test format string against real Bilibili URL during Phase 2 and handle "format not available" with user-facing error
- Phase 3: yt-dlp progress hook runs in yt-dlp's internal thread; asyncio.Queue.put_nowait() is thread-safe but validate before frontend SSE depends on it

## Session Continuity

Last session: 2026-03-19
Stopped at: Roadmap created — ready to plan Phase 1
Resume file: None
