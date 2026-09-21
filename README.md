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

## Browser extension (Bilibili bypass)

When server-side download fails (geo / 412 / login), use the **browser extension** in [`extension/`](extension/README.md):

1. Run the app on port **3003** (above).
2. Load the unpacked extension from `extension/` (Chrome: **Load unpacked**; Firefox: temporary add-on).
3. On Bilibili or YouTube, wait until the video is playing, then **Cache this video** — the extension downloads the player streams from that tab (VPN/cookies apply) into the app cache. Or mark **in/out** and **Export** to record one segment to `POST /api/clips/from-recording`.

See [extension/README.md](extension/README.md) for install steps and audio troubleshooting.

### Workflow

1. Paste a **YouTube or Bilibili** URL and click **Prepare video** (or use **Extract clip** — it will download on first use). Downloads happen **once** per URL at **up to 720p** into `./cache/` (with live progress).
2. Change **Start** / **End** (`0:30`, `1:05`, or `1:01:05`) — or use the **timeline scrubber** when the video is cached — set **filename**, and click **Extract clip** again — **no re-download** for the same URL. The JSON sidecar next to each clip stores the **video title** (from the download) and the **start–end range** only. After a successful extract, the **filename** field clears and the scrubber resets for the next clip.
3. The **library** dropdown lists videos already cached on disk (URLs are stored in `url_registry.json` next to the `.mp4` files).
4. Clips go to the **output directory** (default `./clips/`). Each clip is saved as **MP4 (libx264 CRF + AAC)**. Tune encoding in **`config.json`** at the project root (`clip_crf`, `clip_preset`, `clip_audio_kbps`) or via **Settings** in the UI.
5. **Clips this session** accumulates extractions until you **Clear list** or restart the server; switching URLs does not wipe the list.


## Transcript ingest

Section **Transcript ingest** on the main page:

1. Paste the **instructional title** (used as context so ASR mistakes like “de la bida” become **de la riva**).
2. Paste a raw transcript.
3. Click **Process & save ingest** — fillers/CTAs are stripped, names corrected, key concepts summarized, JSON saved under `ingest/`.

- Without an API key: offline glossary + filler cleanup (`mode: heuristic`).
- With OpenAI key (Settings → AI ingest, or `OPENAI_API_KEY`): full LLM cleanup (`mode: llm`).

| Endpoint | Purpose |
|----------|---------|
| `POST /api/ingest` | Process title + transcript; optional `save` |
| `GET /api/ingest` | List saved ingest JSON files |
| `GET /api/ingest/{id}` | Load one ingest result |

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
| `POST /api/clips/from-recording` | Import a browser-recorded segment (`multipart`: `file`, `filename`, `start`, `end`, `source_url`) |
| `POST /api/cache/from-browser` | Import player streams captured in the browser (`multipart`: `video`, optional `audio`, `source_url`, `title`) |
| `GET /api/clips` | Session clip list |
| `GET /api/clip-file/{filename}` | Serve an extracted `.mp4` |
| `GET /api/cache/status?url=` | Whether the URL is cached locally (+ size) |
| `GET /api/cache/videos` | List cached `.mp4` entries (with URL when known) |
| `GET /api/cache/preview/{cache_key}` | Serve cached source `.mp4` for the timeline scrubber (browser) |
| `DELETE /api/cache/videos/{cache_key}` | Remove one cached `.mp4` and its registry entry |
| `DELETE /api/clips` | Clear the session clip list |
| `POST /api/ingest` | Title-aware transcript cleanup + concept extract + save |
| `GET /api/ingest` | List saved ingest JSON |
| `GET /api/ingest/{id}` | Load one ingest result |

## Run tests

```bash
uv run pytest tests/ -v
```

## Files & config

- **Cache:** `./cache/<url-hash>.mp4`, `url_registry.json`, `video_titles.json`
- **Config:** `./config.json` (paths, encoding, optional proxy / Bilibili login) — copy from `config.example.json` to start fresh
- **Session:** `./session_clips.json` (clip list until you clear it)
- Run `uvicorn` from the **project root** so relative paths resolve correctly
