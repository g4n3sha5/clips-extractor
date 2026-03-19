# Phase 1: Foundation - Research

**Researched:** 2026-03-19
**Domain:** FastAPI project scaffold, pydantic-settings config management, StaticFiles serving, filesystem initialization
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-02 | UI is minimal — single page, no frameworks, no complex components | FastAPI StaticFiles mounts a static/ directory and serves index.html directly; vanilla JS + fetch() is the prescribed pattern; no build step, no node_modules |
</phase_requirements>

---

## Summary

Phase 1 establishes the skeleton that every subsequent phase builds on. The deliverables are narrow: a `uvicorn main:app` invocation that opens at `localhost:8000`, serves a single-page HTML UI, and automatically creates the `~/.drillclips/cache/` and `clips/` directories on first run. No download logic, no clip extraction — just the project scaffold, config layer, and static file serving.

The entire stack for this phase is vanilla FastAPI with pydantic-settings. FastAPI mounts a `static/` directory using `StaticFiles(directory="static", html=True)` and serves it at the root. The `html=True` flag makes FastAPI return `index.html` for bare `/` requests, which is exactly the single-page pattern required. The config layer (pydantic-settings reading/writing `~/.drillclips/config.json`) ensures both service classes in Phase 2 and Phase 3 have a typed, validated interface to the cache directory and output directory.

The project ecosystem research (SUMMARY.md, STACK.md, ARCHITECTURE.md) is thorough and directly applicable here. All stack versions are confirmed on PyPI as of 2026-03-19. No new tool research is needed for this phase — the patterns are standard FastAPI and pydantic-settings.

**Primary recommendation:** Scaffold the project with `uv`, create `main.py` + `config.py` + `static/index.html`, mount StaticFiles, initialize `~/.drillclips/cache/` and `./clips/` in a startup event handler, and expose `GET/POST /api/config`. This phase is complete when `uvicorn main:app` works end-to-end.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Longest active support window; fastest CPython; FastAPI 0.135+ requires 3.10+; 3.12 is the safe current target |
| FastAPI | 0.135.1 | HTTP framework, static file serving, request validation | Async-first; StaticFiles built into Starlette base; pydantic v2 built in; single import path for all Phase 1 needs |
| Uvicorn | 0.42.0 | ASGI server | Default for FastAPI; `uvicorn main:app --reload` is the standard dev invocation; single-process is correct for local single-user tool |
| pydantic | 2.12.5 | Data models and validation | Ships with FastAPI; define Settings and config response models here |
| pydantic-settings | 2.13.1 | Typed config management from JSON/env | Reads `~/.drillclips/config.json` into a validated Settings model; handles default values; avoids manual JSON parsing |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiofiles | 25.1.0 | Async file I/O | Required by FastAPI StaticFiles under the hood; also used for async writes to config.json if needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-settings | python-dotenv + manual parsing | pydantic-settings gives type validation and IDE autocomplete at the same install cost; no reason to use dotenv directly |
| StaticFiles mount | Separate file server (nginx, http.server) | Adds ops complexity for zero benefit; StaticFiles handles the single-page pattern cleanly |
| uv | pip + venv | pip works; uv produces a lockfile automatically and is significantly faster; no functional difference for this scope |

**Installation:**
```bash
uv venv && source .venv/bin/activate
uv add "fastapi[standard]"   # pulls uvicorn[standard] + pydantic
uv add pydantic-settings
uv add aiofiles
```

---

## Architecture Patterns

### Recommended Project Structure

```
drillclip/
├── main.py                 # FastAPI app instance, startup handler, router includes, StaticFiles mount
├── config.py               # Settings model (output_dir, cache_dir), load() and save() functions
├── routers/
│   ├── __init__.py
│   └── config.py           # GET /api/config, POST /api/config
├── models.py               # Pydantic request/response schemas (ConfigResponse, ConfigUpdate)
└── static/
    └── index.html          # Minimal single-page UI — no framework, no build step
```

Note: `services/` directory is not needed in Phase 1 — DownloadService and ClipService are Phase 2/3 work. Create the directory as a stub only if it avoids import errors in later plans.

### Pattern 1: StaticFiles with html=True for Single-Page UI

**What:** Mount the `static/` directory at the root path with `html=True`. FastAPI will serve `index.html` for bare `/` requests and any path that doesn't match an API route.
**When to use:** Always — this is the correct FastAPI pattern for a single-page app served from the same process as the API.

```python
# Source: https://fastapi.tiangolo.com/tutorial/static-files/
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# API routers must be included BEFORE StaticFiles mount
# StaticFiles is a catch-all — it must come last
app.include_router(config_router, prefix="/api")

app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

**Critical ordering:** Include all API routers before the StaticFiles mount. StaticFiles acts as a catch-all fallback — if mounted first, it intercepts API routes.

### Pattern 2: pydantic-settings for Config Management

**What:** Use pydantic-settings `BaseSettings` to define the application config as a typed model. Load from a JSON file at `~/.drillclips/config.json`. Save by serializing the model back to JSON.
**When to use:** Always — typed config with defaults is strictly better than manual JSON dict parsing.

```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
import json

CONFIG_PATH = Path.home() / ".drillclips" / "config.json"

class Settings(BaseSettings):
    cache_dir: Path = Field(default=Path.home() / ".drillclips" / "cache")
    output_dir: Path = Field(default=Path("clips").resolve())

def load_settings() -> Settings:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        return Settings(**data)
    return Settings()

def save_settings(settings: Settings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(settings.model_dump_json(indent=2))
```

### Pattern 3: Startup Event Handler for Directory Initialization

**What:** Use FastAPI's `lifespan` context manager (preferred over deprecated `@app.on_event("startup")`) to create required directories on first run.
**When to use:** Always — directory creation must happen before any service can write files.

```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure required directories exist
    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: nothing needed

app = FastAPI(lifespan=lifespan)
```

Note: `@app.on_event("startup")` is deprecated in FastAPI 0.93+. Use `lifespan` context manager.

### Pattern 4: Config API Router

**What:** A thin router exposing `GET /api/config` (returns current settings) and `POST /api/config` (updates and persists settings). Delegates entirely to `config.py` functions.

```python
from fastapi import APIRouter
from models import ConfigResponse, ConfigUpdate

router = APIRouter()

@router.get("/config", response_model=ConfigResponse)
def get_config():
    return load_settings()

@router.post("/config", response_model=ConfigResponse)
def update_config(body: ConfigUpdate):
    settings = load_settings()
    if body.output_dir is not None:
        settings = settings.model_copy(update={"output_dir": body.output_dir})
    save_settings(settings)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings
```

### Anti-Patterns to Avoid

- **Mounting StaticFiles before API routers:** StaticFiles is a catch-all. Any router included after the mount will never be reached. Always include routers first.
- **Using `@app.on_event("startup")` (deprecated):** This was removed in FastAPI 0.93+ in favor of `lifespan`. Use the context manager pattern.
- **Storing config in app state instead of a file:** Config must survive server restarts. Write to `~/.drillclips/config.json`, not to `app.state`.
- **Hardcoding paths without `Path.home()`:** `~/` expansion via `os.path.expanduser` or `Path.home()` is required; string literals like `~/.drillclips` will not expand on all platforms.
- **Creating `static/` without an `index.html`:** If the directory exists but `index.html` is missing, FastAPI returns 404 for `/`. The placeholder must exist even in Phase 1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Typed config with defaults | Manual JSON dict access + try/except | pydantic-settings BaseSettings | Type coercion, validation, and default values are handled automatically; custom code has drift risk |
| Static file serving | Custom route returning `FileResponse` per file | FastAPI StaticFiles mount | StaticFiles handles etag, range requests, content-type headers, and directory listing automatically |
| Directory path expansion | String formatting with `os.environ["HOME"]` | `pathlib.Path.home()` | Platform-safe, no environment variable dependency, returns a Path object directly |
| Config file location | Arbitrary project-relative path | `~/.drillclips/config.json` via `Path.home()` | User-level config belongs in the home directory; survives working directory changes |

**Key insight:** This phase is infrastructure-only. Every problem has a five-line solution using the prescribed libraries. Custom implementations add surface area that must be maintained across phases.

---

## Common Pitfalls

### Pitfall 1: StaticFiles Intercepts API Routes

**What goes wrong:** `GET /api/config` returns 404 or the contents of `index.html` instead of JSON.
**Why it happens:** StaticFiles is mounted at `/` before the API router is registered. It becomes a catch-all that intercepts every request.
**How to avoid:** Always `app.include_router(...)` before `app.mount("/", StaticFiles(...))`. The router include must appear first in `main.py`.
**Warning signs:** API endpoints return HTML instead of JSON; `/api/config` returns 404 in browser but the server is running.

### Pitfall 2: Deprecated Startup Event Handler

**What goes wrong:** FastAPI logs a deprecation warning, or in future versions startup logic silently never runs.
**Why it happens:** `@app.on_event("startup")` was deprecated in FastAPI 0.93 and removed in later versions.
**How to avoid:** Use the `lifespan` context manager pattern from day one.
**Warning signs:** `DeprecationWarning: on_event is deprecated` in uvicorn logs.

### Pitfall 3: Path Serialization in pydantic-settings

**What goes wrong:** `config.json` stores `Path` objects that deserialize as strings on reload, causing type mismatch errors.
**Why it happens:** `pathlib.Path` is not natively JSON-serializable as a `Path` — it serializes as a string, and `Settings(**data)` re-coerces it, which works correctly. However, if `model_dump()` is used instead of `model_dump_json()`, Path objects become Python objects that `json.dumps` cannot serialize.
**How to avoid:** Use `settings.model_dump_json()` (pydantic's serializer) when writing config, not `json.dumps(settings.model_dump())`.
**Warning signs:** `TypeError: Object of type PosixPath is not JSON serializable` during config save.

### Pitfall 4: Missing index.html Causes 404 on First Load

**What goes wrong:** Browser opens `localhost:8000` and gets a 404.
**Why it happens:** StaticFiles with `html=True` serves `index.html` for `/`, but only if the file exists. An empty `static/` directory or missing `index.html` causes a 404.
**How to avoid:** Always create a minimal `static/index.html` as part of the scaffold task, even if it's just a `<h1>Drill Clip Extractor</h1>` placeholder.
**Warning signs:** `GET / 404` in uvicorn logs.

### Pitfall 5: clips/ Directory Created Relative to CWD

**What goes wrong:** `./clips/` is created wherever `uvicorn` is invoked from, not in the expected project directory.
**Why it happens:** The `output_dir` default is `Path("clips").resolve()` — this resolves relative to the current working directory at import time. If uvicorn is run from a different directory, clips end up in the wrong place.
**How to avoid:** Document clearly that `uvicorn main:app` must be run from the project root. Alternatively, anchor the default to a fixed location (`Path.home() / "drillclips-output"`) or make it configurable via the config API from day one.
**Warning signs:** Clips saved to unexpected directory; user can't find output.

---

## Code Examples

### main.py Scaffold

```python
# Source: https://fastapi.tiangolo.com/tutorial/static-files/ + https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import config as config_router
from config import load_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(lifespan=lifespan)

# Routers MUST come before StaticFiles mount
app.include_router(config_router.router, prefix="/api")

# StaticFiles as catch-all — must be last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### Minimal index.html (Phase 1 Placeholder)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Drill Clip Extractor</title>
</head>
<body>
  <h1>Drill Clip Extractor</h1>
  <p>Foundation phase — UI coming in Phase 3.</p>
</body>
</html>
```

### uv Project Initialization

```bash
# Initialize project
uv init drillclip
cd drillclip

# Add runtime dependencies
uv add "fastapi[standard]"
uv add pydantic-settings
uv add aiofiles

# Run dev server
uvicorn main:app --reload
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93 (deprecated); removed in 0.103+ | Startup/shutdown logic must use the context manager pattern |
| pydantic v1 BaseSettings in fastapi package | pydantic-settings as a separate package | pydantic v2 / FastAPI 0.100+ | `pydantic-settings` must be installed separately; it is not part of pydantic core |
| `pip + venv` | `uv` | 2024+ | uv produces a lockfile automatically; `uv sync` is the install command; `uv.lock` replaces `requirements.txt` in new projects |

**Deprecated/outdated:**
- `@app.on_event("startup")`: Use `lifespan` context manager. The old event decorator raises deprecation warnings on FastAPI 0.135.
- `from pydantic import BaseSettings`: Removed from pydantic core in v2. Import from `pydantic_settings` instead.

---

## Open Questions

1. **Should `clips/` default to `./clips/` (project-relative) or `~/drillclips-output/`?**
   - What we know: The requirements say "clips/ output directory" and "EXT-04: Clips are saved to ./clips/ directory." This implies project-relative.
   - What's unclear: If the user runs `uvicorn` from different directories, project-relative defaults can be surprising.
   - Recommendation: Use `Path("clips").resolve()` as the default (resolves at startup, anchored to CWD). Document in README that uvicorn must be run from the project root. The config API (Phase 1) lets users override it.

2. **Should Phase 1 include a `/api/health` endpoint?**
   - What we know: Not in requirements. Success criterion is "uvicorn main:app serves at localhost:8000."
   - What's unclear: Useful for Phase 2/3 integration testing — lets a test verify the server is up without loading the full HTML.
   - Recommendation: Include a trivial `GET /api/health` returning `{"status": "ok"}` — zero cost, useful for smoke testing in later phases.

---

## Sources

### Primary (HIGH confidence)

- [FastAPI Static Files docs](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mounting, html=True behavior
- [FastAPI Lifespan Events docs](https://fastapi.tiangolo.com/advanced/events/) — lifespan context manager, deprecation of on_event
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) — version 2.13.1, BaseSettings pattern
- [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — model_dump_json, Path field handling
- [fastapi PyPI](https://pypi.org/project/fastapi/) — version 0.135.1
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — version 0.42.0

### Secondary (MEDIUM confidence)

- project STACK.md (2026-03-19) — version matrix and alternatives confirmed against PyPI
- project ARCHITECTURE.md (2026-03-19) — build order and StaticFiles/router ordering pattern
- project SUMMARY.md (2026-03-19) — Phase 1 scope definition and rationale

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI as of 2026-03-19 in prior research
- Architecture: HIGH — StaticFiles + lifespan + pydantic-settings are documented FastAPI patterns with no ambiguity
- Pitfalls: HIGH — all pitfalls are derived from official FastAPI deprecation notes and pydantic v2 migration docs; no speculation

**Research date:** 2026-03-19
**Valid until:** 2026-09-19 (stable stack — FastAPI, pydantic-settings, and uvicorn change slowly; lifespan pattern is stable since FastAPI 0.93)
