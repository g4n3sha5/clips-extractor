# Stack Research

**Domain:** Local Python web app — video clip extraction tool (yt-dlp + ffmpeg)
**Researched:** 2026-03-19
**Confidence:** HIGH (all versions verified against PyPI; architecture patterns verified against official docs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime | 3.12 is the current LTS sweet spot — longest active support window, fastest CPython yet, and FastAPI 0.135+ requires 3.10+ minimum. 3.12 avoids deprecation churn without chasing 3.13 beta quirks. |
| FastAPI | 0.135.1 | HTTP API + static file serving | The only Python async framework where yt-dlp's Python API + asyncio.to_thread integrates cleanly. Pydantic v2 is built-in. Starlette's StaticFiles mounts the frontend without a separate server. SSE support is native as of 0.135. |
| Uvicorn | 0.42.0 | ASGI server | Default ASGI server for FastAPI; single-process is correct for a local single-user tool. `uvicorn main:app --reload` is the standard dev invocation. No Gunicorn needed at local scale. |
| yt-dlp | 2026.03.17 (date-versioned) | Video download | Python-native import (`yt_dlp.YoutubeDL`) is preferred over subprocess — gives direct access to the options dict, progress hooks, and error handling without shell escaping. Run in `asyncio.to_thread` to avoid blocking the event loop. |
| ffmpeg (system binary) | Latest system install | Video cutting | `-c copy` cuts are essentially I/O-bound — no re-encoding, near-instant. Called via `asyncio.create_subprocess_exec` for non-blocking execution without a wrapper library overhead. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.5 | Request/response model validation | Always — FastAPI's validation layer. Define `ClipRequest`, `Config`, and session models here. V2 is ~10–50x faster than V1 and ships with FastAPI. |
| pydantic-settings | 2.13.1 | Config management (output dir, cache dir) | Load `~/.drillclips/config.json` or env vars into a typed `Settings` model. Handles the user-configured output directory and cache directory cleanly. |
| aiofiles | 25.1.0 | Async file I/O | Required by FastAPI's `StaticFiles`. Also useful for async JSON metadata writes (`<filename>.json` side-files). |
| sse-starlette | 3.3.3 | Server-Sent Events for download progress | Stream yt-dlp progress hooks back to the browser without polling. The browser's `EventSource` API requires no extra JS dependency — pure vanilla JS handles it. Only needed if implementing live progress feedback. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Dependency management and venv | Replaces pip + virtualenv for 2025 projects. `uv sync` is the install command; lockfile is `uv.lock`. Dramatically faster than pip for repeated installs. |
| Ruff | Linting + formatting | Single tool replaces flake8 + black + isort. Run as pre-commit or in CI. Default config is sane for a small project. |
| pytest + pytest-anyio | Testing | `pytest-anyio` handles async route testing without asyncio boilerplate. Only add if writing tests; small local tools often skip formal tests. |

---

## Installation

```bash
# Create and activate environment with uv
uv venv && source .venv/bin/activate

# Core runtime dependencies
uv add "fastapi[standard]"   # pulls uvicorn[standard] + pydantic
uv add pydantic-settings
uv add aiofiles
uv add sse-starlette          # only if streaming progress is in scope

# System dependencies (not pip-managed)
# brew install yt-dlp ffmpeg   # macOS
# or: pip install yt-dlp       # installs yt-dlp as a Python package + CLI

# Dev dependencies
uv add --dev ruff pytest pytest-anyio
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Flask | Flask is fine for pure REST without async; loses ergonomics when you add SSE progress streaming and Pydantic models. For this project, yt-dlp blocking calls need `asyncio.to_thread` — FastAPI's async-first design makes that natural. |
| FastAPI | Django | Django is overkill: ORM, migrations, admin panel — none of it applies to a single-user local tool. |
| asyncio.create_subprocess_exec (raw) | python-ffmpeg library | python-ffmpeg is a useful wrapper for complex filter graphs. For this project, the ffmpeg call is a single `-c copy` cut — raw subprocess is shorter, has no additional dependency, and is easier to debug. |
| yt_dlp Python import | subprocess yt-dlp CLI | The Python import gives direct access to progress hooks (`postprocessor_hooks`, `progress_hooks`) needed for SSE streaming. Subprocess yt-dlp requires parsing stderr, which is fragile. |
| pydantic-settings | python-dotenv | pydantic-settings wraps dotenv but adds type validation and IDE autocomplete. Same install cost; better ergonomics. |
| uv | pip + venv | pip works; uv is strictly faster and produces a lockfile automatically. No functional difference for this scope — just developer quality of life. |
| Vanilla HTML/JS (no framework) | React / Vue / HTMX | This is a local tool with one screen and ~5 interactive elements. A JS framework adds a build step, node_modules, and cognitive overhead for zero user benefit. Vanilla JS with `fetch()` + `EventSource` is sufficient. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| ffmpeg-python (kkroening) | Last meaningful release was 2020; the pip package `ffmpeg-python` is unmaintained and has known issues with complex filter graphs. Do not confuse with `python-ffmpeg` (jonghwanhyeon). | `asyncio.create_subprocess_exec` directly, or `python-ffmpeg` if a wrapper is desired |
| Celery + Redis | Adds two infrastructure dependencies (broker + worker) for a problem that `asyncio.to_thread` solves in 5 lines. Appropriate for multi-user production systems, not local single-user tools. | FastAPI `BackgroundTasks` + `asyncio.to_thread` |
| SQLite / any database | There is no relational data model here — clips are files, metadata is JSON side-files. Introducing a DB adds migration complexity for no benefit. | JSON files on disk, as specified in PROJECT.md |
| Starlette directly | FastAPI is a thin wrapper over Starlette with Pydantic validation and auto-docs added. No reason to drop to raw Starlette for a new project. | FastAPI |
| WebSockets for progress | WebSockets require bidirectional framing — overkill for server-to-client progress updates. SSE is unidirectional, HTTP-compatible, and trivial with `sse-starlette` + browser `EventSource`. | `sse-starlette` |

---

## Stack Patterns by Variant

**If download progress feedback is out of scope (MVP):**
- Skip `sse-starlette`
- Return a synchronous JSON response after the download+cut completes
- Use FastAPI `BackgroundTasks` to kick off download, poll a `/status/{job_id}` endpoint from JS

**If download progress feedback is in scope:**
- Add `sse-starlette`
- yt-dlp progress hook writes to an `asyncio.Queue`; SSE endpoint drains the queue
- Browser `EventSource('/progress/{job_id}')` renders a live progress bar in vanilla JS

**If Bilibili requires cookies or login (future):**
- yt-dlp supports `cookiesfrombrowser` option — pass the browser name in `YoutubeDL` opts
- No additional library needed; document this as a config option in `pydantic-settings`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| fastapi 0.135.1 | pydantic 2.12.5 | FastAPI 0.100+ requires Pydantic v2. V1 compatibility shim exists but is deprecated. |
| fastapi 0.135.1 | uvicorn 0.42.0 | No known conflicts; `fastapi[standard]` pins a compatible uvicorn range. |
| sse-starlette 3.3.3 | Python 3.10+ | Requires Python 3.10+, same floor as FastAPI 0.135. |
| pydantic-settings 2.13.1 | pydantic 2.x | pydantic-settings 2.x requires pydantic 2.x. Versions are independent packages since pydantic v2 split settings out. |
| yt-dlp (date-versioned) | Python 3.9+ | yt-dlp supports Python 3.9+; no conflicts with the Python 3.12 requirement. |

---

## Sources

- [fastapi PyPI](https://pypi.org/project/fastapi/) — version 0.135.1, released 2026-03-01 (HIGH confidence)
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — version 0.42.0, released 2026-03-16 (HIGH confidence)
- [yt-dlp GitHub releases](https://github.com/yt-dlp/yt-dlp/releases) — date-versioned, latest 2026.03.17 (HIGH confidence)
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) — version 3.3.3, released 2026-03-17 (HIGH confidence)
- [pydantic PyPI](https://pypi.org/project/pydantic/) — version 2.12.5 (HIGH confidence)
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) — version 2.13.1 (HIGH confidence)
- [aiofiles PyPI](https://pypi.org/project/aiofiles/) — version 25.1.0 (HIGH confidence)
- [FastAPI static files docs](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mounting pattern (HIGH confidence)
- [FastAPI SSE docs](https://fastapi.tiangolo.com/tutorial/server-sent-events/) — native SSE support in 0.135+ (HIGH confidence)
- [yt-dlp asyncio issue #9487](https://github.com/yt-dlp/yt-dlp/issues/9487) — ThreadPoolExecutor recommended over ProcessPoolExecutor for yt-dlp (MEDIUM confidence)
- [python-ffmpeg docs](https://python-ffmpeg.readthedocs.io/) — async API via asyncio.create_subprocess_exec (MEDIUM confidence)

---

*Stack research for: Drill Clip Extractor — local Python web tool for yt-dlp + ffmpeg clip extraction*
*Researched: 2026-03-19*
