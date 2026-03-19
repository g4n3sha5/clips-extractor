# Drill Clip Extractor

## What This Is

A minimal local web tool for extracting timestamped clips from YouTube and Bilibili instructional videos. The user sets a current instructional URL, adds timestamp ranges with filenames, and the tool downloads (once, cached) and cuts clips using yt-dlp and ffmpeg. Extracted clips are shown in a session list with a play button.

## Core Value

Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can set a "current instructional" URL (YouTube or Bilibili)
- [ ] User inputs start/end timestamps and a filename to extract a clip
- [ ] Tool downloads video via yt-dlp at 720p, cached by URL (skip re-download if cached)
- [ ] Tool cuts clip using ffmpeg -c copy, outputs <filename>.mp4 to user-chosen folder
- [ ] Description field with auto-suggest template (source, tags, url, range, notes) — multiline, freeform
- [ ] Session clip list shows all clips extracted from the current instructional, with filename, range, and play button
- [ ] Hidden JSON metadata stored next to each clip file (not visible in UI)
- [ ] User-chosen output directory (configured once)
- [ ] Form is keyboard-friendly and fast

### Out of Scope

- JSON metadata exposed in UI — metadata is internal only
- Re-download when cache exists — cache hit always skips download
- Complex UI, thumbnails, or video preview in browser — keep it minimal
- Mobile / non-local access — local use only
- Qualities above 720p — 720p is the cap

## Context

- yt-dlp handles both YouTube and Bilibili; needs to be installed on the system
- ffmpeg required for cutting; -c copy avoids re-encoding (fast, lossless cut)
- Cache lives in a configurable cache dir (default: ~/.drillclips/cache/)
- Hidden metadata: <filename>.json next to <filename>.mp4
- Python backend (FastAPI) serves a simple browser UI
- "Drill clips" = technique clips from instructional videos (martial arts / grappling context)

## Constraints

- **Tech stack**: Python + FastAPI backend, minimal HTML/JS frontend (no heavy frameworks)
- **Dependencies**: yt-dlp and ffmpeg must be installed on the host system
- **Download quality**: 720p max, no higher
- **Cut method**: ffmpeg -c copy only (no re-encoding)
- **Scope**: Local tool, single user, no auth

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + FastAPI | yt-dlp is Python-native; minimal server overhead | — Pending |
| Cache by URL | Avoid redundant downloads of same instructional | — Pending |
| ffmpeg -c copy | Speed and quality — no re-encoding needed for clip extraction | — Pending |
| JSON metadata hidden | User wants human-readable descriptions, not structured UI | — Pending |
| 720p cap | Sufficient quality for instructionals, keeps files manageable | — Pending |

---
*Last updated: 2026-03-19 after initialization*
