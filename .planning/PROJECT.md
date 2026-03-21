# Drill Clip Extractor

## What This Is

A minimal local web tool for extracting timestamped clips from YouTube and Bilibili instructional videos. The user sets a current instructional URL, adds timestamp ranges with filenames, and the tool downloads (once, cached) and cuts clips using yt-dlp and ffmpeg. Extracted clips are shown in a session list with a play button.

## Core Value

Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [x] User can set a "current instructional" URL (YouTube or Bilibili)
- [x] User inputs start/end timestamps and a filename to extract a clip (timeline scrubber optional)
- [x] Tool downloads video via yt-dlp at 720p, cached by URL (skip re-download if cached)
- [x] Tool cuts clip using ffmpeg (re-encode to H.264 + AAC per config), outputs `<filename>.mp4` to output dir
- [x] Description field with auto-suggest template (source, tags, url, range, notes) — multiline, freeform
- [x] Session clip list shows clips with filename, range, and play button
- [x] Hidden JSON metadata stored next to each clip file (not visible in UI)
- [x] User-chosen output directory (via config API / `~/.drillclips/config.json`)
- [x] Form is keyboard-friendly and fast

### Out of Scope

- JSON metadata exposed in UI — metadata is internal only
- Re-download when cache exists — cache hit always skips download
- Heavy video editing UI — timeline scrubber for range only; no in-player preview requirement beyond duration
- Mobile / non-local access — local use only
- Qualities above 720p — 720p is the cap

## Context

- yt-dlp handles both YouTube and Bilibili (Python dependency)
- ffmpeg required for merge (download) and clip extraction (re-encode for smaller files — see README defaults)
- Cache lives in a configurable cache dir (default: ~/.drillclips/cache/)
- Hidden metadata: <filename>.json next to <filename>.mp4
- Python backend (FastAPI) serves a simple browser UI
- "Drill clips" = technique clips from instructional videos (martial arts / grappling context)

## Constraints

- **Tech stack**: Python + FastAPI backend, minimal HTML/JS frontend (no heavy frameworks)
- **Dependencies**: yt-dlp (Python dep) and ffmpeg on `PATH`
- **Download quality**: 720p max, no higher
- **Cut method**: ffmpeg re-encode (H.264 + AAC) with configurable CRF/preset — smaller files than stream-copy
- **Scope**: Local tool, single user, no auth

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + FastAPI | yt-dlp is Python-native; minimal server overhead | Shipped |
| Cache by URL | Avoid redundant downloads of same instructional | Shipped |
| ffmpeg re-encode for clips | Much smaller clip files than `-c copy` for typical instructionals | Shipped (defaults in config) |
| JSON metadata hidden | Human-readable descriptions in sidecar, not structured UI | Shipped |
| 720p cap | Sufficient quality; keeps downloads manageable | Shipped |

## Milestone: v1.1 UX Overhaul — **complete**

**Shipped (2026-03-20):**
- Dark minimal UI; post-extract reset (filename + description template + scrubber range)
- Cache pill: Cached / Downloading / Not cached; cache library panel with delete
- Timeline scrubber + `GET /api/cache/preview/{cache_key}` for duration

**Next (v2, deferred):** See `.planning/REQUIREMENTS.md` — e.g. configurable cache dir in UI, session persistence, optional UX polish.

---
*Last updated: 2026-03-20 — v1.1 complete*
