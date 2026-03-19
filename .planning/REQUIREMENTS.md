# Requirements: Drill Clip Extractor

**Defined:** 2026-03-19
**Core Value:** Fast, keyboard-friendly clip extraction from a watched instructional — paste URL once, stamp out clips without friction.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Download

- [ ] **DL-01**: User can set a YouTube or Bilibili URL as the current instructional source
- [ ] **DL-02**: Tool downloads video via yt-dlp at 720p (mp4+m4a format) to a local cache directory
- [ ] **DL-03**: Tool skips re-download if URL is already cached (cache hit validated by file size check)

### Extraction

- [ ] **EXT-01**: User can input start and end timestamps for a clip
- [ ] **EXT-02**: User provides a filename manually for the output clip
- [ ] **EXT-03**: Tool cuts clip using ffmpeg -c copy with -avoid_negative_ts make_zero, outputs <filename>.mp4
- [ ] **EXT-04**: Clips are saved to ./clips/ directory (created automatically if missing)

### Description & Metadata

- [ ] **DESC-01**: User can fill a multiline description field with auto-suggest template (source, tags, url, range, notes)
- [ ] **DESC-02**: Tool stores a hidden JSON sidecar file (<filename>.json) next to each clip (not visible in UI)

### Progress

- [ ] **PROG-01**: Download progress is streamed live to the UI via Server-Sent Events (SSE)

### Session

- [ ] **SESS-01**: Session clip list shows all clips extracted from the current instructional (in-memory, resets on restart)
- [ ] **SESS-02**: Each clip in the session list has a play button that opens the clip file

### UX

- [ ] **UX-01**: Form supports full keyboard navigation (tab between fields, enter to submit)
- [ ] **UX-02**: UI is minimal — single page, no frameworks, no complex components

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Configuration

- **CONF-01**: User can configure output directory via settings
- **CONF-02**: User can configure cache directory via settings

### Session Persistence

- **SESS-03**: Session clip list persists across server restarts

### UX Enhancements

- **UX-03**: Auto-open clip file after extraction completes
- **UX-04**: Timestamp validation with user-friendly error before submission

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
| DL-01 | Phase 2 | Pending |
| DL-02 | Phase 2 | Pending |
| DL-03 | Phase 2 | Pending |
| EXT-01 | Phase 3 | Pending |
| EXT-02 | Phase 3 | Pending |
| EXT-03 | Phase 3 | Pending |
| EXT-04 | Phase 3 | Pending |
| DESC-01 | Phase 4 | Pending |
| DESC-02 | Phase 4 | Pending |
| PROG-01 | Phase 3 | Pending |
| SESS-01 | Phase 3 | Pending |
| SESS-02 | Phase 3 | Pending |
| UX-01 | Phase 3 | Pending |
| UX-02 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
