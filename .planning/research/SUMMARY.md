# Project Research Summary

**Project:** Drill Clip Extractor
**Domain:** Local Python web tool — video clip extraction for martial arts instructionals
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

Drill Clip Extractor is a single-user localhost tool that solves a specific workflow: paste a YouTube or Bilibili URL, specify a timestamp range and filename, and receive a lossless MP4 clip in under a second (after the initial download). The recommended approach is a minimal FastAPI + vanilla JS stack with yt-dlp for downloading and ffmpeg `-c copy` for trimming. This is not a complex product — the entire backend is three service classes and four API routes, and the frontend is a single HTML file with no build step. The architecture is dictated by one constraint: yt-dlp downloads are slow (30–120 seconds), and everything in the design — SSE progress feedback, background task execution, URL-keyed caching — exists to make that wait acceptable.

The key insight from competitive research is that no existing tool combines URL download, lossless stream-copy trimming, per-session tracking, and a keyboard-first form in a single local tool. LosslessCut does lossless cuts but requires local files. Parabolic downloads but doesn't cut. Online cutters re-encode. This tool fills the gap specifically for practitioners who watch long instructionals and need to extract clips rapidly across a work session. The metadata sidecar feature (hidden `.json` alongside each `.mp4`) is low-effort to implement and creates forward compatibility with future search/tagging tooling without any database overhead today.

The main risks are implementation-order risks, not architectural unknowns. Several pitfalls are well-documented and avoidable if addressed in the correct phase: the yt-dlp format string must be locked down before caching is built on top of it (Opus/MP4 mux failure); async execution of yt-dlp must be established before the download endpoint is wired up (event loop blocking); and the ffmpeg command shape must be correct from the start (keyframe snapping, `-avoid_negative_ts`). None of these are hard problems — they just require deliberate sequencing.

---

## Key Findings

### Recommended Stack

The entire runtime fits in five packages: FastAPI 0.135.1, Uvicorn 0.42.0, yt-dlp (date-versioned), pydantic 2.12.5, and pydantic-settings 2.13.1. Add aiofiles for async file writes and sse-starlette 3.3.3 if SSE progress is in scope. Dependency management via `uv`. No database, no frontend framework, no task queue. The stack is intentionally minimal because this is a local single-user tool — Celery/Redis, SQLite, and React are all explicitly out of scope.

**Core technologies:**
- Python 3.12 — runtime; longest active support, fastest CPython, required by FastAPI 0.135+
- FastAPI 0.135.1 — HTTP API, static file serving, SSE; async-first design integrates cleanly with yt-dlp's threading model
- Uvicorn 0.42.0 — ASGI server; single-process is correct for a local single-user tool
- yt-dlp (Python API, not subprocess) — direct access to progress hooks; run via `asyncio.to_thread` to avoid blocking the event loop
- ffmpeg (system binary) — called via `asyncio.create_subprocess_exec`; `-c copy` cuts are near-instant, no re-encoding
- Vanilla HTML/JS — no build step, no node_modules; a single `index.html` with `fetch()` and `EventSource` is sufficient

### Expected Features

**Must have (table stakes — v1):**
- URL input with download and URL-keyed caching — the single slow step; must only happen once per instructional
- Timestamp range + filename form — the core data of every clip
- ffmpeg `-c copy` extraction to configured output folder — the deliverable
- Download/extraction progress feedback (SSE) — without this, the UI appears frozen for 30–120 seconds
- Session clip list with filename, range, and play button — confirm clips without leaving the tool
- Output folder configuration (once on first use) — clips need a home
- Error messaging for yt-dlp and ffmpeg failures — silent failures are unusable
- Keyboard-first form flow (Tab, Enter) — the core value proposition is low friction

**Should have (competitive differentiators — v1.x after validation):**
- Description field with auto-suggest template — clips self-document with source, tags, and notes
- JSON metadata sidecar written alongside each MP4 — machine-readable, portable, no database required
- Timestamp validation (client + server) — prevents "end before start" and out-of-range errors
- Bilibili support — yt-dlp handles it transparently; needs testing and documentation

**Defer to v2+:**
- Persistent clip library across sessions — requires storage design; session-based model is sufficient initially
- Tag-based sidecar search — only valuable after many clips accumulate
- Bulk re-extraction — edge case; not needed until output folder changes become common

### Architecture Approach

The architecture is a thin FastAPI app with three service classes (DownloadService, ClipService, ConfigService), three router modules, a single-page frontend, and two filesystem directories (cache and output). The build order is dictated by dependencies: config layer first (both services need it), then DownloadService, then ClipService, then routers, then frontend, then SSE progress as a final UX layer. The entire system is stateless on the server side — session clip history lives in the browser's JS memory and is reconstructed from the output directory on reload (or simply lost, which is acceptable).

**Major components:**
1. DownloadService — checks URL-keyed cache (`sha256(url)[:16].mp4`), invokes yt-dlp Python API via `asyncio.to_thread`, writes to `~/.drillclips/cache/`
2. ClipService — calls `ffmpeg -c copy` via `asyncio.create_subprocess_exec`, writes `.mp4` + `.json` sidecar to user-configured output directory
3. ConfigService — reads/writes `~/.drillclips/config.json`; exposes `GET/POST /api/config`
4. SSE progress layer — yt-dlp progress hook writes to `asyncio.Queue` per job; `/api/status/{job_id}` endpoint drains the queue as a Server-Sent Event stream
5. Frontend (vanilla HTML/JS) — served by FastAPI `StaticFiles`; uses `fetch()` for API calls and `EventSource` for progress

### Critical Pitfalls

1. **ffmpeg `-c copy` keyframe snapping** — place `-ss` before `-i` (input seek) and add `-avoid_negative_ts make_zero`; accept that cuts snap to the nearest preceding I-frame and document this behavior in the UI. Address during core clip extraction implementation.

2. **Opus/WebM audio fails to mux into MP4** — lock the yt-dlp format string to `bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]` with `--merge-output-format mp4`. Must be decided before caching is built, because cached files with wrong format cannot be recovered without deletion and re-download.

3. **yt-dlp blocks the FastAPI event loop** — never call `YoutubeDL().download()` inside an `async def` endpoint. Use `asyncio.to_thread()` or `asyncio.create_subprocess_exec("yt-dlp", ...)`. Address at the download endpoint phase before any other backend work depends on it.

4. **Stale/corrupt cache from interrupted downloads** — after download, verify the file exists AND has size above a minimum threshold; optionally run `ffprobe` to confirm non-zero duration. Store expected URL in a `.meta` sidecar so corruption is detectable. Address at cache layer design.

5. **Shell injection via user-supplied inputs** — always use `asyncio.create_subprocess_exec(...)` with arguments as a Python list, never with `shell=True` or f-string interpolation. Validate filenames to strip path separators and assert the final output path is inside the configured output directory (directory traversal prevention).

---

## Implications for Roadmap

Based on the build-order dependencies in ARCHITECTURE.md and the phase-to-pitfall mapping in PITFALLS.md, a four-phase structure is recommended:

### Phase 1: Foundation — Config, Project Scaffold, and File System Layout

**Rationale:** Both service classes depend on knowing the cache directory and output directory. Nothing else can be built without this. Sets up the `uv` project, FastAPI app shell, and ConfigService in a single focused phase.
**Delivers:** Running FastAPI app at localhost:8000 serving `index.html`; config read/write via `/api/config`; `~/.drillclips/` directory structure created on first run.
**Addresses features:** Output folder configuration.
**Avoids pitfalls:** None of the critical pitfalls arise here, but this is where filename/path validation patterns should be established (directory traversal prevention from the start).
**Research flag:** Standard patterns — skip phase research.

### Phase 2: Download Service and URL-Keyed Cache

**Rationale:** The cache is the foundation of the tool's value — without it, every clip extraction triggers a full re-download. This phase locks in the yt-dlp format string (preventing Opus/MP4 mux failure), the async execution pattern (preventing event loop blocking), and the cache integrity check (preventing stale cache). These three decisions cannot be safely revisited after ClipService is built on top of them.
**Delivers:** `POST /api/download` or equivalent; URL-keyed cache at `~/.drillclips/cache/<url_hash>.mp4`; async download with no event loop blocking; cache hit returning immediately.
**Addresses features:** Download with caching by URL; Bilibili support (verify format string works for both).
**Avoids pitfalls:** Opus/WebM mux failure (format string locked here), event loop blocking (async pattern established here), stale cache (integrity check implemented here).
**Research flag:** Needs verification — Bilibili 720p format availability without login should be tested in this phase.

### Phase 3: Clip Extraction, SSE Progress, and Core UI

**Rationale:** With the cache layer stable, ClipService can be built knowing its inputs are reliable. SSE progress is included in this phase — not deferred — because the FEATURES.md research explicitly flags that a frozen UI during 30–120 second downloads makes the tool feel broken. This is the phase that produces the end-to-end working workflow.
**Delivers:** Full clip extraction flow: URL → cache → ffmpeg `-c copy` → `.mp4` in output dir; live download progress via SSE; session clip list with play button in browser; error messaging surfaced to UI.
**Addresses features:** All P1 features: clip extraction, progress feedback, session clip list, in-browser playback, error messaging, keyboard-first form flow.
**Avoids pitfalls:** ffmpeg keyframe snapping (correct `-ss` placement and `-avoid_negative_ts`), browser video seek (use `FileResponse` not `StreamingResponse` for clip playback endpoint).
**Uses stack:** sse-starlette, asyncio.Queue per job, `asyncio.create_subprocess_exec` for ffmpeg.
**Research flag:** Standard patterns for SSE and ffmpeg — skip phase research. FileResponse range request behavior is well-documented.

### Phase 4: Metadata, Validation, and Polish (v1.x)

**Rationale:** Once the core workflow is validated through use, add the features that improve durability of the clips over time and reduce form errors. Description field and JSON sidecar are coupled and low-effort; timestamp validation prevents a class of frustrating errors.
**Delivers:** Description field with template pre-fill; `.json` sidecar written alongside every `.mp4`; client + server timestamp validation; yt-dlp version check and warning on startup.
**Addresses features:** Description field (P2), JSON metadata sidecar (P2), timestamp validation (P2), yt-dlp version warning (integration gotcha from PITFALLS.md).
**Avoids pitfalls:** UX pitfall — free-form timestamp input without validation causes inconsistent behavior.
**Research flag:** Standard patterns — skip phase research.

### Phase Ordering Rationale

- Config before services: Both DownloadService and ClipService need the config (cache_dir, output_dir) to know where to write. This is a hard dependency, not a preference.
- Download before clip extraction: ClipService reads from the cache. The cache must exist and be reliable before ClipService is written.
- SSE in Phase 3 (not deferred to Phase 4): The FEATURES.md research classifies progress feedback as P1, not P2. The PITFALLS.md research independently documents that the absence of progress feedback causes users to assume the tool is broken and click again (triggering duplicate downloads). Deferring SSE creates a worse problem.
- Metadata and validation last: These improve experience but do not affect the core workflow. Adding them after the core loop is validated ensures they are not over-engineered.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2:** Bilibili 720p format availability and cookie requirements. The format string research is solid for YouTube, but PITFALLS.md flags that Bilibili gates 720p+ on login. This needs a test download against a real Bilibili URL to confirm what format string works for anonymous access.

Phases with standard patterns (skip research-phase):
- **Phase 1:** FastAPI project setup and pydantic-settings config management are thoroughly documented.
- **Phase 3:** SSE with sse-starlette, asyncio.Queue, and ffmpeg subprocess are well-documented patterns with multiple verified sources.
- **Phase 4:** Description textarea, JSON file writes, and timestamp regex validation are trivial implementation tasks.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI as of 2026-03-19; official docs confirm compatibility matrix |
| Features | HIGH (core), MEDIUM (differentiators) | P1 features confirmed against competitive analysis; differentiator value is reasoned, not user-validated |
| Architecture | HIGH | Build order and component boundaries derived from FastAPI official docs and yt-dlp issue tracker; SSE pattern has multiple practitioner confirmations |
| Pitfalls | HIGH | Critical pitfalls verified against official issue trackers (yt-dlp, ffmpeg wiki, FastAPI discussions); warning signs and recovery strategies documented |

**Overall confidence:** HIGH

### Gaps to Address

- **Bilibili anonymous download quality cap:** PITFALLS.md documents that Bilibili gates 720p+ on login. The recommended approach is to test the format string against a real Bilibili URL during Phase 2 and gracefully handle "format not available" with a user-facing message. No architectural change needed — just test coverage and error handling.
- **yt-dlp progress hook with async queue threading:** STACK.md and PITFALLS.md both note (MEDIUM confidence) that yt-dlp's progress hooks run in yt-dlp's internal thread, not the asyncio event loop. The `asyncio.Queue.put_nowait()` call from the hook is thread-safe, but this pattern should be validated with a test run in Phase 3 before the frontend SSE wiring depends on it.
- **Output filename `.mp4` double-extension:** PITFALLS.md flags a UX issue where users type `clip.mp4` and receive `clip.mp4.mp4`. This is a trivial server-side strip, but it must be implemented explicitly — it will not happen automatically.

---

## Sources

### Primary (HIGH confidence)
- [fastapi PyPI](https://pypi.org/project/fastapi/) — version 0.135.1
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — version 0.42.0
- [yt-dlp GitHub releases](https://github.com/yt-dlp/yt-dlp/releases) — date-versioned, 2026.03.17
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) — version 3.3.3
- [pydantic PyPI](https://pypi.org/project/pydantic/) — version 2.12.5
- [FastAPI static files docs](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mounting pattern
- [FastAPI Background Tasks documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) — async task execution pattern
- [FFmpeg Wiki — Seeking](https://fftrac-bg.ffmpeg.org/wiki/Seeking) — `-ss` placement and `-avoid_negative_ts`
- [LosslessCut Issue #1216](https://github.com/mifi/lossless-cut/issues/1216) — ffmpeg keyframe cutting behavior

### Secondary (MEDIUM confidence)
- [yt-dlp asyncio issue #9487](https://github.com/yt-dlp/yt-dlp/issues/9487) — ThreadPoolExecutor recommended for yt-dlp async
- [yt-dlp stale cache issue #10808](https://github.com/yt-dlp/yt-dlp/issues/10808) — partial download detection
- [FastAPI long-running background tasks discussion #7930](https://github.com/fastapi/fastapi/discussions/7930) — async download patterns
- [FastAPI streaming video with range requests #7718](https://github.com/fastapi/fastapi/discussions/7718) — FileResponse range support
- [Building a yt-dlp web frontend (2026)](https://www.earezki.com/ai-news/2026-02-21-i-built-a-free-yt-dlp-web-frontend-that-supports-1000-sites-heres-how/) — practitioner confirmation of architecture patterns
- [Bilibili "No video formats found" Issue #14805](https://github.com/yt-dlp/yt-dlp/issues/14805) — Bilibili login requirements

### Tertiary (LOW confidence)
- [AlternativeTo: LosslessCut alternatives](https://alternativeto.net/software/lossless-cut/) — competitive landscape survey
- [BJJ study tools landscape](https://grapplingaiapp.com/) — user workflow context

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
