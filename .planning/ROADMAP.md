# Roadmap: Drill Clip Extractor

## Overview

Four phases that build sequentially on each other. Phase 1 creates the running app shell. Phase 2 adds the download and cache layer — the slow operation that only happens once per instructional. Phase 3 wires in clip extraction, live progress feedback, and the session clip list, completing the end-to-end workflow. Phase 4 adds the description field and JSON sidecar metadata that lets clips self-document. Each phase delivers something independently verifiable before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Running FastAPI app with minimal UI shell and config layer
- [ ] **Phase 2: Download** - URL-keyed download and cache via yt-dlp
- [ ] **Phase 3: Extraction** - Clip cutting, live progress, and session list
- [ ] **Phase 4: Metadata** - Description field and JSON sidecar

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
- [ ] 01-01-PLAN.md — Config layer: uv project init, Settings model, GET/POST /api/config, GET /api/health
- [ ] 01-02-PLAN.md — App wiring: main.py with lifespan + StaticFiles, minimal single-page UI shell

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

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Not started | - |
| 2. Download | 0/? | Not started | - |
| 3. Extraction | 0/? | Not started | - |
| 4. Metadata | 0/? | Not started | - |
