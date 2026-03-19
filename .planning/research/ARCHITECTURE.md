# Architecture Research

**Domain:** Local Python web tool wrapping yt-dlp and ffmpeg (Drill Clip Extractor)
**Researched:** 2026-03-19
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Frontend)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │  index.html + vanilla JS                             │   │
│  │  - URL input / active instructional display          │   │
│  │  - Timestamp form (start, end, filename, desc)       │   │
│  │  - Session clip list with play buttons               │   │
│  └──────────────────────────────────────────────────────┘   │
│                  fetch() / EventSource (SSE)                 │
├─────────────────────────────────────────────────────────────┤
│                   FastAPI HTTP Server                        │
├──────────────────┬──────────────────┬───────────────────────┤
│  ┌─────────────┐ │  ┌─────────────┐ │  ┌──────────────────┐ │
│  │  /api/clips │ │  │  /api/status│ │  │  /api/config     │ │
│  │  (POST/GET) │ │  │  (SSE GET)  │ │  │  (GET/POST)      │ │
│  └──────┬──────┘ │  └──────┬──────┘ │  └──────────────────┘ │
│         │        │         │        │                        │
│  ┌──────▼────────────────────────────────────────────────┐  │
│  │                   Service Layer                        │  │
│  │  DownloadService  |  ClipService  |  ConfigService     │  │
│  └──────┬────────────────────┬───────────────────────────┘  │
│         │                    │                               │
│  ┌──────▼──────┐    ┌────────▼──────────┐                   │
│  │  yt-dlp     │    │  ffmpeg subprocess│                   │
│  │  (Python    │    │  (-c copy trim)   │                   │
│  │   API)      │    └───────────────────┘                   │
│  └─────────────┘                                            │
├─────────────────────────────────────────────────────────────┤
│                    File System Layer                         │
│  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │  Cache Dir       │  │  Output Dir                     │  │
│  │  ~/.drillclips/  │  │  (user-configured)              │  │
│  │  cache/          │  │  <filename>.mp4                 │  │
│  │  <url_hash>.mp4  │  │  <filename>.json (hidden meta)  │  │
│  └──────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Frontend (HTML/JS) | User input, session clip list display, progress feedback | Single `index.html` with `<script>` blocks; no build step |
| FastAPI app | HTTP routing, static file serving, request validation | `main.py` mounting StaticFiles + routers |
| DownloadService | Check cache, invoke yt-dlp Python API, return cached path | Class or module using `yt_dlp.YoutubeDL` |
| ClipService | Invoke ffmpeg to trim cached video, write .mp4 + .json | Module calling `asyncio.create_subprocess_exec` for ffmpeg |
| ConfigService | Read/write user config (output dir, cache dir) | JSON file at `~/.drillclips/config.json` |
| File System | Persistent cache and output storage | OS directories, addressed by hash of source URL |

## Recommended Project Structure

```
drillclip/
├── main.py                 # FastAPI app, mounts routers and static files
├── config.py               # Settings model (output_dir, cache_dir), load/save
├── services/
│   ├── __init__.py
│   ├── download.py         # yt-dlp wrapper: check cache, download at 720p
│   └── clip.py             # ffmpeg wrapper: trim, write .mp4 + .json sidecar
├── routers/
│   ├── __init__.py
│   ├── clips.py            # POST /api/clips, GET /api/clips
│   ├── status.py           # GET /api/status/{job_id} (SSE for progress)
│   └── config.py           # GET/POST /api/config
├── models.py               # Pydantic request/response schemas
├── static/
│   ├── index.html          # Single-page UI
│   └── app.js              # Fetch calls, SSE listener, DOM manipulation
└── tests/
    ├── test_download.py
    └── test_clip.py
```

### Structure Rationale

- **services/:** Contains all side-effecting logic (subprocess calls, file I/O). Keeps routers thin and testable.
- **routers/:** One file per resource group. FastAPI `APIRouter` instances are included in `main.py`. Thin — delegate to services.
- **static/:** FastAPI serves this directory with `StaticFiles(directory="static", html=True)`. Keeps frontend colocated.
- **models.py:** Single file for Pydantic models is sufficient at this scale. Split only if it grows large.
- **config.py:** Separate from models — handles persistence of user settings, not HTTP schemas.

## Architectural Patterns

### Pattern 1: yt-dlp Python API (not subprocess)

**What:** Import `yt_dlp` and use `YoutubeDL` class directly instead of `subprocess("yt-dlp ...")`.
**When to use:** Always, for this project — gives access to progress hooks and avoids shell quoting issues.
**Trade-offs:** Slightly more complex setup than subprocess; progress hooks have known issues with certain yt-dlp options (e.g., `writesubtitles`), but those don't apply here.

**Example:**
```python
import yt_dlp

def download_video(url: str, output_path: str, progress_cb=None):
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]",
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "progress_hooks": [progress_cb] if progress_cb else [],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
```

### Pattern 2: asyncio.create_subprocess_exec for ffmpeg

**What:** Use `asyncio.create_subprocess_exec` to call ffmpeg non-blocking, rather than `subprocess.run` (which blocks the event loop).
**When to use:** ffmpeg invocation for clip trimming — keeps FastAPI responsive during cuts.
**Trade-offs:** Slightly more verbose than `subprocess.run`; correctly non-blocking.

**Example:**
```python
import asyncio

async def cut_clip(input_path: str, start: str, end: str, output_path: str):
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", start, "-to", end,
        "-c", "copy",
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
```

### Pattern 3: Background task + SSE for download progress

**What:** FastAPI `BackgroundTasks` starts the yt-dlp download; an `asyncio.Queue` per job carries progress events; a SSE endpoint streams the queue to the browser.
**When to use:** For the download phase — yt-dlp can take 10-60 seconds; a blocking endpoint is wrong.
**Trade-offs:** Adds a job-tracking dict in app state; acceptable for single-user local tool. (Celery/Redis would be overkill here.)

**Example:**
```python
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio, json

jobs: dict[str, asyncio.Queue] = {}

async def event_stream(job_id: str):
    q = jobs[job_id]
    while True:
        event = await q.get()
        yield f"data: {json.dumps(event)}\n\n"
        if event.get("status") in ("finished", "error"):
            break

@app.get("/api/status/{job_id}")
async def status(job_id: str):
    return StreamingResponse(event_stream(job_id), media_type="text/event-stream")
```

### Pattern 4: URL-keyed cache check

**What:** Hash the source URL (md5 or sha256) to derive a stable cache filename. On each extract request, check if `cache_dir/<url_hash>.mp4` exists before invoking yt-dlp.
**When to use:** Always — core requirement is "download once, cache forever."
**Trade-offs:** No expiry logic; cache grows indefinitely. Acceptable for a personal local tool.

**Example:**
```python
import hashlib
from pathlib import Path

def cache_path(url: str, cache_dir: Path) -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    return cache_dir / f"{key}.mp4"

def is_cached(url: str, cache_dir: Path) -> bool:
    return cache_path(url, cache_dir).exists()
```

## Data Flow

### Clip Extraction Request Flow

```
[User fills form: URL, start, end, filename, description]
    ↓  POST /api/clips
[Router: validate request with Pydantic model]
    ↓
[DownloadService.ensure_cached(url)]
    ├── cache hit → return cached path immediately
    └── cache miss → start BackgroundTask(download)
            ↓
        [yt-dlp YoutubeDL.download()]  → progress_hook → asyncio.Queue
            ↓  (job done)
        [cached .mp4 written to cache_dir]
    ↓
[ClipService.cut(cached_path, start, end, output_path)]
    ↓  asyncio.create_subprocess_exec ffmpeg -c copy
[<filename>.mp4 written to output_dir]
    ↓
[Write <filename>.json sidecar (url, range, description, tags)]
    ↓
[Return clip metadata to frontend]
    ↓
[Frontend appends to session clip list, shows play button]
```

### Progress Feedback Flow (SSE)

```
[Frontend: EventSource("/api/status/<job_id>")]
    ↑  text/event-stream
[FastAPI SSE endpoint reads asyncio.Queue]
    ↑  queue.put(event)
[yt-dlp progress_hook callback]
    (fires per download fragment: percent, speed, eta)
```

### Config Flow

```
[Frontend: GET /api/config on load]
    → ConfigService.load() → reads ~/.drillclips/config.json
    → returns {output_dir, cache_dir}

[Frontend: POST /api/config with new dirs]
    → ConfigService.save() → writes ~/.drillclips/config.json
```

### Key Data Flows

1. **Cache check:** Every clip request first resolves `cache_dir/<url_hash>.mp4` — no network hit if present.
2. **ffmpeg input:** ffmpeg always reads from the cached full video file, never from a network stream.
3. **Sidecar metadata:** `.json` is written by ClipService immediately after `.mp4` succeeds — not a separate step exposed in the API.
4. **Session state:** The frontend holds the session clip list in memory (JS array). The server does not persist session state; on reload, the clip list is reconstructed from `.mp4` + `.json` files in `output_dir` (or simply lost — acceptable per the project scope).

## Scaling Considerations

This is a local single-user tool. Scaling is not a concern. The table below documents what would break first if this ever needed multi-user access.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (current) | In-process `asyncio.Queue` + BackgroundTasks is correct |
| 2-5 users | Add job locking to prevent duplicate downloads of same URL |
| 10+ users | Replace in-process queue with Celery + Redis; add proper job persistence |

### Scaling Priorities

1. **First bottleneck:** Duplicate downloads — two requests for the same URL could trigger two yt-dlp processes simultaneously. Fix with a per-URL download lock (`asyncio.Lock` keyed by URL hash).
2. **Second bottleneck:** In-process `jobs` dict — lost on server restart. Fix with a lightweight DB (SQLite) for job state if persistence matters.

## Anti-Patterns

### Anti-Pattern 1: subprocess.run for yt-dlp

**What people do:** Call `subprocess.run(["yt-dlp", ...])` instead of using the Python API.
**Why it's wrong:** Blocks the event loop; loses access to progress hooks; requires shell-escaping URLs; harder to test.
**Do this instead:** Import `yt_dlp` and use `YoutubeDL` class with `progress_hooks`.

### Anti-Pattern 2: Blocking the FastAPI event loop during download

**What people do:** Call `yt_dlp.YoutubeDL().download()` directly inside an `async def` endpoint.
**Why it's wrong:** yt-dlp's download is synchronous and CPU/IO bound; it will block the entire server for the duration of the download (potentially minutes).
**Do this instead:** Run yt-dlp in a `BackgroundTask` or via `asyncio.to_thread()` so the endpoint returns immediately with a job ID.

### Anti-Pattern 3: Re-encoding with ffmpeg

**What people do:** Use `ffmpeg -vcodec libx264` or similar re-encoding options.
**Why it's wrong:** Slow (minutes for long clips), lossy, unnecessary — clips are already MP4 H.264 from yt-dlp at 720p.
**Do this instead:** Always use `-c copy` for trimming. Fast, lossless, seconds to complete.

### Anti-Pattern 4: Storing the full video in output_dir

**What people do:** Write the full downloaded video alongside the clips.
**Why it's wrong:** Confuses the output directory with cache; user sees unwanted files.
**Do this instead:** Separate cache_dir (full videos) from output_dir (clips only). Cache is an implementation detail.

### Anti-Pattern 5: Heavy frontend framework for a single-page local tool

**What people do:** Reach for React/Vue/Svelte for the browser UI.
**Why it's wrong:** Adds a build step, node_modules, and maintenance overhead for a tool with ~5 UI interactions.
**Do this instead:** Vanilla HTML + `fetch()` + `EventSource`. FastAPI serves a single `index.html`. No build step.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| yt-dlp | Python API (`yt_dlp.YoutubeDL`) — in-process | Must be installed: `pip install yt-dlp`. Supports Bilibili and YouTube natively. |
| ffmpeg | `asyncio.create_subprocess_exec` — child process | Must be installed on host OS. Binary path should be configurable or discovered via `shutil.which("ffmpeg")`. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Router ↔ DownloadService | Direct function/method call + `await` | Router passes validated Pydantic model fields |
| Router ↔ ClipService | Direct function/method call + `await` | Router passes `output_dir` from ConfigService |
| DownloadService ↔ progress queue | `asyncio.Queue.put_nowait()` in yt-dlp progress hook | Hook runs in yt-dlp's thread; queue is thread-safe |
| Frontend ↔ SSE endpoint | `EventSource` HTTP long-connection | Browser reconnects automatically on disconnect |
| Frontend ↔ REST endpoints | `fetch()` JSON | Standard JSON request/response |
| ClipService ↔ file system | Direct `pathlib.Path` operations | Write .mp4, then .json. If .mp4 write fails, .json is not written. |

## Build Order (Phase Dependencies)

The components have clear dependencies that dictate build order:

```
1. Config layer (config.py, /api/config)
        ↓ required by
2. DownloadService (needs cache_dir from config)
        ↓ required by
3. ClipService (needs cached video path from DownloadService)
        ↓ required by
4. Clips API (/api/clips router)
        ↓ required by
5. Frontend UI (calls /api/clips, /api/config)
        ↓ enhanced by
6. SSE progress (/api/status) — additive, doesn't block usability
```

Build the config and service layers first (testable in isolation), then wire routers, then add the frontend, then layer on SSE progress as a UX enhancement.

## Sources

- [FastAPI Background Tasks documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) — HIGH confidence
- [FastAPI Static Files documentation](https://fastapi.tiangolo.com/tutorial/static-files/) — HIGH confidence
- [yt-dlp Python embedding patterns](https://github.com/yt-dlp/yt-dlp) — HIGH confidence (official repo)
- [yt-dlp asyncio multiprocessing issue discussion](https://github.com/yt-dlp/yt-dlp/issues/9487) — MEDIUM confidence (community)
- [Building a yt-dlp web frontend (2026)](https://www.earezki.com/ai-news/2026-02-21-i-built-a-free-yt-dlp-web-frontend-that-supports-1000-sites-heres-how/) — MEDIUM confidence (practitioner writeup)
- [FastAPI long-running background tasks discussion](https://github.com/fastapi/fastapi/discussions/7930) — MEDIUM confidence (community)
- [FastAPI SSE + asyncio.Queue pattern](https://dev.to/zachary62/build-an-llm-web-app-in-python-from-scratch-part-4-fastapi-background-tasks-sse-21g4) — MEDIUM confidence (practitioner)

---
*Architecture research for: Local Python web tool wrapping yt-dlp + ffmpeg (Drill Clip Extractor)*
*Researched: 2026-03-19*
