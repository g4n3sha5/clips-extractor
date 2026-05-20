# Drill Clip Extractor

A local FastAPI app for downloading instructional videos once (cached), extracting timestamped clips with **ffmpeg** (clips are **re-encoded** to **H.264 + AAC** for a much smaller footprint than stream-copy), and keeping a per-session clip list. Metadata (including encode settings) is stored in a **JSON sidecar** next to each `.mp4` (not shown in the UI).

## System requirements

- **Python** 3.9+
- **`uv`** (recommended) or another way to install Python deps
- **`ffmpeg`** on your `PATH` — **required** for (1) cutting clips and (2) **merging** separate video+audio streams when downloading (common on Bilibili / YouTube DASH). Example (macOS): `brew install ffmpeg`. The app shows a warning on load if `ffmpeg` is missing.
- **YouTube / most URLs:** no account required (default).
- **Bilibili:** public videos download without login. Multi-part links need **`?p=N`** (e.g. `?p=10`). Optional in **Settings**: proxy URL (VPN local port) and “Bilibili login” for members-only / region-locked videos. Space out downloads to avoid **412** rate limits.
- **`yt-dlp`** is bundled as a Python dependency; the CLI is not required

Install `uv` if needed:

```bash
python3 -m pip install --user uv
```

Add `uv` to your `PATH` (zsh), e.g. in `~/.zshrc`:

```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

## Setup

From the project root:

```bash
uv sync
```

## Run the app

```bash
uv run uvicorn main:app --reload --port 3003
```

Or (same default port):

```bash
uv run python main.py
```

Open [http://localhost:3003](http://localhost:3003).

### Workflow

1. Paste a **YouTube or Bilibili** URL and click **Prepare video** (or use **Extract clip** — it will download on first use). Downloads happen **once** per URL at **up to 720p** into `./cache/` (with live progress).
2. Change **Start** / **End** (`0:30`, `1:05`, or `1:01:05`) — or use the **timeline scrubber** when the video is cached — set **filename**, and click **Extract clip** again — **no re-download** for the same URL. The JSON sidecar next to each clip stores the **video title** (from the download) and the **start–end range** only. After a successful extract, the **filename** field clears and the scrubber resets for the next clip.
3. The **library** dropdown lists videos already cached on disk (URLs are stored in `url_registry.json` next to the `.mp4` files).
4. Clips go to the **output directory** (default `./clips/`). Each clip is saved as **MP4 (libx264 CRF + AAC)**. Tune encoding in **`config.json`** at the project root (`clip_crf`, `clip_preset`, `clip_audio_kbps`) or via **Settings** in the UI.
5. **Clips this session** accumulates extractions until you **Clear list** or restart the server; switching URLs does not wipe the list.

## API (for debugging)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/config` | Cache/output dirs + clip encoding defaults (`clip_crf`, `clip_preset`, `clip_audio_kbps`) |
| `POST /api/config` | Update dirs and/or clip settings |
| `GET /api/health` | `status` + `ffmpeg` (whether `ffmpeg` is on `PATH`) |
| `POST /api/instructional` | Set current instructional URL (`{"url":"..."}`) |
| `POST /api/download` | Start download job; returns `job_id` |
| `GET /api/download/stream/{job_id}` | **SSE** download progress |
| `POST /api/clips` | Extract clip (`start`, `end`, `filename`, optional `url`); sidecar description is auto: title + range |
| `GET /api/clips` | Session clip list |
| `GET /api/clip-file/{filename}` | Serve an extracted `.mp4` |
| `GET /api/cache/status?url=` | Whether the URL is cached locally (+ size) |
| `GET /api/cache/videos` | List cached `.mp4` entries (with URL when known) |
| `GET /api/cache/preview/{cache_key}` | Serve cached source `.mp4` for the timeline scrubber (browser) |
| `DELETE /api/cache/videos/{cache_key}` | Remove one cached `.mp4` and its registry entry |
| `DELETE /api/clips` | Clear the session clip list |

## Run tests

```bash
uv run pytest tests/ -v
```

## Files & config

- **Cache:** `./cache/<url-hash>.mp4`, `url_registry.json`, `video_titles.json`
- **Config:** `./config.json` (paths, encoding, optional proxy / Bilibili login) — copy from `config.example.json` to start fresh
- **Session:** `./session_clips.json` (clip list until you clear it)
- Run `uvicorn` from the **project root** so relative paths resolve correctly
