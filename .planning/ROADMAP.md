# Roadmap: Drill Clip Extractor

## Overview

Four phases that build sequentially on each other. Phase 1 creates the running app shell. Phase 2 adds the download and cache layer — the slow operation that only happens once per instructional. Phase 3 wires in clip extraction, live progress feedback, and the session clip list, completing the end-to-end workflow. Phase 4 adds the description field and JSON sidecar metadata that lets clips self-document. Each phase delivers something independently verifiable before the next begins.

Milestone v1.1 (Phases 5–7) replaces the v1 form UI with a dark, minimal interface. Phase 5 lands the dark theme and post-extraction reset. Phase 6 adds cache visibility and management. Phase 7 delivers the timeline scrubber — the centerpiece of the overhaul.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Running FastAPI app with minimal UI shell and config layer
- [x] **Phase 2: Download** - URL-keyed download and cache via yt-dlp
- [x] **Phase 3: Extraction** - Clip cutting, live progress, and session list
- [x] **Phase 4: Metadata** - Description field and JSON sidecar
- [x] **Phase 5: Dark UI Overhaul** - Complete visual redesign to dark minimal theme plus post-extraction form reset
- [x] **Phase 6: Cache Visibility** - Cache status badge on URL field and cache management panel with delete
- [x] **Phase 7: Timeline Scrubber** - Visual timeline scrubber with draggable in/out handles synced to timestamp fields

## Phase Details

### Phase 1: Foundation
**Goal**: A running local app that serves the UI and persists config
**Depends on**: Nothing (first phase)
**Requirements**: UX-02
**Success Criteria** (what must be TRUE):
  1. Running `uvicorn main:app` serves the app at localhost:8000
  2. Opening localhost:8000 in a browser shows the single-page UI (no frameworks, no build step)
  3. Cache directory (~/.drillclips/cache/) and clips/ output directory are created automatically on first run
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Config layer: uv project init, Settings model, GET/POST /api/config, GET /api/health
- [x] 01-02-PLAN.md — App wiring: main.py with lifespan + StaticFiles, minimal single-page UI shell

### Phase 2: Download
**Goal**: Users can paste a YouTube or Bilibili URL and have the video downloaded and cached once
**Depends on**: Phase 1
**Requirements**: DL-01, DL-02, DL-03
**Success Criteria** (what must be TRUE):
  1. User pastes a YouTube URL and the video downloads to ~/.drillclips/cache/ at 720p mp4
  2. Submitting the same URL a second time completes immediately (cache hit, no re-download)
  3. Pasting a Bilibili URL downloads at the best available quality up to 720p (or shows a clear error if format unavailable)
**Plans**: TBD

### Phase 3: Extraction
**Goal**: Users can extract a named clip from the cached video and see it in the session list
**Depends on**: Phase 2
**Requirements**: EXT-01, EXT-02, EXT-03, EXT-04, PROG-01, SESS-01, SESS-02, UX-01
**Success Criteria** (what must be TRUE):
  1. User enters start/end timestamps and a filename, submits with keyboard, and receives a .mp4 clip in clips/
  2. Download progress streams live to the UI — the page does not appear frozen during a 30–120 second download
  3. After extraction, the clip appears in the session list with filename, timestamp range, and a play button
  4. Clicking the play button opens the clip file (native player or browser)
  5. All form fields are reachable and submittable via keyboard only (Tab to navigate, Enter to submit)
**Plans**: TBD

### Phase 4: Metadata
**Goal**: Each extracted clip is self-documenting via a freeform description and a hidden JSON sidecar
**Depends on**: Phase 3
**Requirements**: DESC-01, DESC-02
**Success Criteria** (what must be TRUE):
  1. The clip form includes a multiline description textarea pre-filled with a source/tags/url/range/notes template
  2. After extraction, a <filename>.json file exists next to the .mp4 with the metadata contents (not visible in UI)
**Plans**: TBD

### Phase 5: Dark UI Overhaul
**Goal**: The entire UI runs on a dark minimal theme and resets to a clean state after each clip extraction
**Depends on**: Phase 4
**Requirements**: UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. Opening the app shows a dark background with light text — no white or light-grey backgrounds visible anywhere in the layout
  2. All interactive elements (inputs, buttons, session list) render consistently within the dark theme
  3. After a clip extraction completes, the filename field is cleared and the form is ready for the next clip without a page reload
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — Dark theme CSS tokens + post-extraction form reset (UI-03, UI-04)

### Phase 6: Cache Visibility
**Goal**: Users can see cache status at a glance and delete cached videos they no longer need
**Depends on**: Phase 5
**Requirements**: CACHE-01, CACHE-02, CACHE-03
**Success Criteria** (what must be TRUE):
  1. The URL field shows a status badge that reads "Cached", "Downloading", or "Not cached" based on actual cache state
  2. The badge updates in real time — switching from "Not cached" to "Downloading" to "Cached" as a download progresses
  3. User can open a cache panel that lists each cached video with its file size and cache date
  4. User can delete a cached video from the panel, and it disappears from the list and from disk
**Plans**: TBD

### Phase 7: Timeline Scrubber
**Goal**: Users can drag handles on a visual timeline to set clip in/out points instead of typing timestamps
**Depends on**: Phase 6
**Requirements**: TL-01, TL-02, TL-03
**Success Criteria** (what must be TRUE):
  1. When a cached video is loaded, a horizontal timeline scrubber is visible representing the full video duration
  2. User can drag the left handle to set the clip start time and the right handle to set the clip end time
  3. Dragging a handle updates the corresponding timestamp field in real time
  4. Typing a timestamp directly into a start/end field moves the corresponding scrubber handle to the matching position
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-03-19 |
| 2. Download | integrated | Complete | 2026-03-19 |
| 3. Extraction | integrated | Complete | 2026-03-19 |
| 4. Metadata | integrated | Complete | 2026-03-19 |
| 5. Dark UI Overhaul | 1/1 | Complete | 2026-03-20 |
| 6. Cache Visibility | integrated | Complete | 2026-03-20 |
| 7. Timeline Scrubber | integrated | Complete | 2026-03-20 |
