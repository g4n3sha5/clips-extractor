# Requirements: Drill Clip Extractor

**Defined:** 2026-03-19
**Core Value:** Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Download

- [x] **DL-01**: User can set a YouTube or Bilibili URL as the current instructional source
- [x] **DL-02**: Tool downloads video via yt-dlp at 720p (mp4+m4a format) to a local cache directory
- [x] **DL-03**: Tool skips re-download if URL is already cached (cache hit validated by file size check)

### Extraction

- [x] **EXT-01**: User can input start and end timestamps for a clip
- [x] **EXT-02**: User provides a filename manually for the output clip
- [x] **EXT-03**: Tool cuts clip using ffmpeg -c copy with -avoid_negative_ts make_zero, outputs <filename>.mp4
- [x] **EXT-04**: Clips are saved to ./clips/ directory (created automatically if missing)

### Description & Metadata

- [x] **DESC-01**: User can fill a multiline description field with auto-suggest template (source, tags, url, range, notes)
- [x] **DESC-02**: Tool stores a hidden JSON sidecar file (<filename>.json) next to each clip (not visible in UI)

### Progress

- [x] **PROG-01**: Download progress is streamed live to the UI via Server-Sent Events (SSE)

### Session

- [x] **SESS-01**: Session clip list shows all clips extracted from the current instructional (in-memory, resets on restart)
- [x] **SESS-02**: Each clip in the session list has a play button that opens the clip file

### UX

- [x] **UX-01**: Form supports full keyboard navigation (tab between fields, enter to submit)
- [x] **UX-02**: UI is minimal — single page, no frameworks, no complex components

## v1.1 Requirements

Requirements for UX Overhaul milestone.

### Timeline

- [x] **TL-01**: User can see a visual timeline scrubber for the currently cached video
- [x] **TL-02**: User can drag in-point and out-point handles on the scrubber to set clip start and end times
- [x] **TL-03**: Scrubber handle positions are reflected in the start/end timestamp fields (and vice versa)

### Cache

- [x] **CACHE-01**: URL field shows a status badge indicating whether the video is cached, downloading, or not cached
- [x] **CACHE-02**: User can open a cache management panel listing all cached videos with size and date
- [x] **CACHE-03**: User can delete a cached video from the cache management panel

### UI

- [x] **UI-03**: UI uses a dark minimal theme (complete visual overhaul replacing current light form layout)
- [x] **UI-04**: After clip extraction completes, the form resets to scrub-ready state (filename cleared, scrubber reset)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Configuration

- **CONF-01**: User can configure output directory via settings
- **CONF-02**: User can configure cache directory via settings

### Session Persistence

- **SESS-03**: Session clip list persists across server restarts

### UX Enhancements

- **UX-05**: Auto-open clip file after extraction completes
- **UX-06**: Timestamp validation with user-friendly error before submission

## Out of Scope

| Feature | Reason |
|---------|--------|
| JSON metadata visible in UI | User wants clean UI; metadata is internal only |
| In-browser video preview/scrubbing | Complexity spike, wrong problem for this tool |
| Quality selection UI | 720p is the fixed cap — no choice needed |
| Batch CSV/timestamp import | Scope explosion, not the workflow |
| Re-encoding / transcoding | ffmpeg -c copy only — speed and quality |
| Mobile or remote access | Local-only tool, single user |
| OAuth / authentication | Local tool, no auth needed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DL-01 | Phase 2 | Done |
| DL-02 | Phase 2 | Done |
| DL-03 | Phase 2 | Done |
| EXT-01 | Phase 3 | Done |
| EXT-02 | Phase 3 | Done |
| EXT-03 | Phase 3 | Done |
| EXT-04 | Phase 3 | Done |
| DESC-01 | Phase 4 | Done |
| DESC-02 | Phase 4 | Done |
| PROG-01 | Phase 3 | Done |
| SESS-01 | Phase 3 | Done |
| SESS-02 | Phase 3 | Done |
| UX-01 | Phase 3 | Done |
| UX-02 | Phase 1 | Done |
| UI-03 | Phase 5 | Done |
| UI-04 | Phase 5 | Done |
| CACHE-01 | Phase 6 | Done |
| CACHE-02 | Phase 6 | Done |
| CACHE-03 | Phase 6 | Done |
| TL-01 | Phase 7 | Done |
| TL-02 | Phase 7 | Done |
| TL-03 | Phase 7 | Done |

**Coverage:**
- v1 requirements: 14 total — all Done ✓
- v1.1 requirements: 8 total — all Done ✓
- Mapped to phases: 8/8
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-20 — v1.1 requirements completed (Phases 5–7)*
