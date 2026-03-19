# Pitfalls Research

**Domain:** Local Python web tool wrapping yt-dlp + ffmpeg for video clip extraction
**Researched:** 2026-03-19
**Confidence:** HIGH (critical pitfalls verified against official issue trackers and ffmpeg documentation)

---

## Critical Pitfalls

### Pitfall 1: ffmpeg -c copy Produces Clips That Start With Black Frames or Audio Leading Silence

**What goes wrong:**
`ffmpeg -c copy` can only cut at keyframe boundaries (I-frames). If the requested start time falls between keyframes, ffmpeg backs up to the nearest preceding I-frame and includes the video from there — but the audio may start at the requested time. This produces clips where audio begins immediately but video is black (or frozen) for up to several seconds, depending on the GOP size.

**Why it happens:**
Video streams use temporal compression: P-frames and B-frames depend on a preceding I-frame to decode. Without re-encoding, ffmpeg cannot start a clip mid-GOP. YouTube videos typically have a keyframe every 2–5 seconds, so the error can be 0–5 seconds. The position of `-ss` (seek flag) relative to `-i` changes behavior: placing `-ss` after `-i` is frame-accurate but slow; placing it before `-i` is fast but imprecise.

**How to avoid:**
Always place `-ss` before `-i` (input seeking) for speed, and add `-avoid_negative_ts make_zero` to prevent timestamp desync at the output. Accept that cut points will snap to the nearest preceding keyframe — this is normal for `-c copy` and is acceptable for instructional clips. Document this behavior in the UI ("cuts snap to nearest keyframe"). If precision within a second is critical, re-encoding is required, which this project explicitly avoids.

Recommended command shape:
```
ffmpeg -ss [start] -i [input] -to [end] -c copy -avoid_negative_ts make_zero [output]
```

**Warning signs:**
- Clips play back with a 1–3 second black/frozen frame at the start before video appears
- Audio and video are visibly out of sync in the output file
- Clips play fine in VLC but stutter in browser `<video>` tag

**Phase to address:**
Core clip extraction implementation phase (wherever ffmpeg command is built).

---

### Pitfall 2: yt-dlp Treats Partial Downloads as Complete (Stale Cache)

**What goes wrong:**
yt-dlp can report a download as successful even when fragments are missing due to network interruption. The resulting file plays but is shorter than the original — e.g., 2:05 instead of 3:17. If the cache-hit check only tests for file existence (not file integrity), the truncated file is served forever for that URL.

**Why it happens:**
yt-dlp defaults to resuming partial downloads via `.part` files. If a download is interrupted mid-fragmented-stream and the partial reassembly produces a valid MP4 header, yt-dlp marks it done. A naive cache check (`os.path.exists(cache_path)`) cannot distinguish a complete file from a truncated one.

**How to avoid:**
After download, verify the output file exists AND has a non-zero size above a minimum threshold (e.g., >100KB). Optionally, run `ffprobe` to confirm duration is non-zero before accepting as cached. Store the expected video ID or URL in a sidecar `.meta` file alongside the cached video so a mismatch indicates corruption. If the cache file appears invalid, delete it and re-download rather than failing silently.

**Warning signs:**
- Extracted clips end abruptly before the specified end timestamp
- `ffprobe` on the cache file returns a duration significantly shorter than expected
- `.part` files remain in the cache directory after a download completes

**Phase to address:**
Download and caching phase. Cache key design and cache-hit validation logic.

---

### Pitfall 3: yt-dlp Blocks the FastAPI Event Loop During Download

**What goes wrong:**
Calling yt-dlp via its Python API (`yt_dlp.YoutubeDL(...).download(...)`) or via `subprocess.run(...)` synchronously inside a FastAPI `async def` endpoint blocks the entire event loop for the duration of the download — typically 30–120 seconds for a 720p video. All other requests to the server hang until the download completes.

**Why it happens:**
FastAPI runs on an asyncio event loop. Synchronous blocking calls (yt-dlp Python API, `subprocess.run`) run in the event loop thread and starve it. Additionally, `YoutubeDL` objects cannot be pickled, which makes naive `asyncio.run_in_executor` with a ProcessPoolExecutor fail.

**How to avoid:**
Use `asyncio.to_thread()` (Python 3.9+) or `loop.run_in_executor(None, ...)` with a ThreadPoolExecutor to run the yt-dlp download in a background thread. Since this is a single-user local tool, a simple threading approach is sufficient — no Celery or task queue needed. Alternatively, invoke yt-dlp as a subprocess using `asyncio.create_subprocess_exec()` which is truly async and avoids the pickling issue entirely.

Recommended approach for this project: `asyncio.create_subprocess_exec("yt-dlp", ...)` — clean, async, no library import needed.

**Warning signs:**
- Browser UI freezes/spins while a download is in progress
- Other API endpoints (e.g., session clip list) do not respond until download finishes
- CPU utilization on the yt-dlp thread pegs at 100% with no response from the server

**Phase to address:**
Backend API / download endpoint phase.

---

### Pitfall 4: ffmpeg Fails to Mux Opus/WebM Audio Into MP4 With -c copy

**What goes wrong:**
YouTube increasingly serves video as VP9/WebM or H.264/MP4 with Opus audio. When yt-dlp merges the best video and audio tracks and the audio is Opus, copying it into an MP4 container fails or produces a file that cannot be played in browsers. The error is typically: `Opus in MP4 support is experimental` or the audio track is silently dropped.

**Why it happens:**
The MP4 container has limited and sometimes broken support for Opus audio in ffmpeg's muxer. yt-dlp selects the best available formats by default, which may be VP9+Opus on YouTube — a combination that remuxes cleanly into MKV/WebM but not MP4.

**How to avoid:**
Explicitly request H.264 video with AAC audio in the yt-dlp format string to guarantee MP4-compatible streams:
```
bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]
```
This preference chain first tries `mp4+m4a` (always muxes cleanly to MP4), then falls back gracefully. Always specify `--merge-output-format mp4` as an extra safeguard.

**Warning signs:**
- yt-dlp emits `WARNING: Requested formats are incompatible for merge` during download
- Downloaded file plays video but has no audio
- ffmpeg exits with non-zero code during the merge step
- Cache file is `.mkv` instead of `.mp4`

**Phase to address:**
Download configuration phase. The yt-dlp format string and merge options must be locked down before any caching logic is built on top.

---

### Pitfall 5: Using shell=True or String Interpolation When Building yt-dlp / ffmpeg Subprocess Calls

**What goes wrong:**
Building subprocess commands by concatenating user-supplied values (timestamps, filenames, URLs) into a shell string with `shell=True` exposes the local machine to command injection. A malicious filename like `clip; rm -rf ~/` passed to an unescaped shell command executes destructively.

**Why it happens:**
It is faster to write `os.system(f"ffmpeg -ss {start} -i {infile} ...")` than to build a proper argument list. Even for a local-only tool, the URL and filename fields come from the browser UI and are treated as trusted — but local tools can still be exploited via browser history, bookmarks, or shared links.

**How to avoid:**
Always use `subprocess.run([...], shell=False)` or `asyncio.create_subprocess_exec(...)` with arguments as a Python list — never as a string. Validate timestamp inputs against a strict `HH:MM:SS` or `MM:SS` regex before passing them to subprocess. Validate filenames to strip or reject characters outside `[a-zA-Z0-9_\-.]`.

**Warning signs:**
- Any subprocess call that uses `shell=True` or f-string interpolation directly into a command string
- Filename or timestamp fields with no server-side validation

**Phase to address:**
Backend API / any phase that builds subprocess calls. Validate at the point of entry (API route), not inside the subprocess helper.

---

### Pitfall 6: Browser `<video>` Tag Cannot Seek in Served MP4 Without HTTP Range Support

**What goes wrong:**
The project includes a "play button" for each extracted clip. If the FastAPI backend serves clips via `FileResponse` without HTTP range request support (206 Partial Content), browsers load the entire file before playing and seeking is disabled. A 200MB clip causes a 30-second hang before playback starts.

**Why it happens:**
The HTML5 `<video>` element requires HTTP range requests to support seek operations and efficient streaming. FastAPI's `FileResponse` does support range requests natively, but only if the response is not wrapped or buffered incorrectly. `StreamingResponse` with a simple generator does not automatically handle range headers.

**How to avoid:**
Use `fastapi.responses.FileResponse` directly — FastAPI's `FileResponse` handles `Accept-Ranges` and 206 responses automatically (via Starlette's underlying implementation). Do not wrap clip playback in a custom `StreamingResponse` generator unless it correctly parses the `Range` header and returns 206.

**Warning signs:**
- Browser `<video>` element loads but seek bar is disabled or jumps back to 0
- Large clips take a long time before any playback begins
- Server responds with HTTP 200 instead of 206 to a range request

**Phase to address:**
Frontend clip playback / any phase that adds a play endpoint.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Cache key = full URL string as filename | Simple, no hashing needed | URL-derived filenames are long and contain invalid FS characters; breaks on Windows paths | Never — hash the URL (e.g., SHA-256) and store URL in a sidecar `.meta` file |
| Single global yt-dlp options dict | Fast to write | Silent breakage when options conflict across different yt-dlp versions | Acceptable in MVP if options are pinned and documented |
| Using yt-dlp Python API instead of subprocess | Avoids external process | YoutubeDL cannot be pickled; harder to run async; tightly couples to yt-dlp internals | Use subprocess instead — cleaner async support |
| Hardcoding cache dir as `~/.drillclips/cache/` | No configuration needed | Breaks for users with non-standard home directories or on Windows | Acceptable for MVP; make configurable in a later phase |
| No progress feedback during download | Simpler backend | User sees a frozen UI for 30–120 seconds with no indication of progress | MVP-acceptable if a loading indicator is shown; a later phase should add SSE or polling |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| yt-dlp (Bilibili) | Assuming 720p is always available without login | Bilibili gates 720p+ on login; test with public videos and gracefully handle "format not available" errors |
| yt-dlp (YouTube) | Using `best` format without specifying codec preference | `best` may select VP9+Opus which fails to mux into MP4; use the explicit `mp4+m4a` preference chain |
| yt-dlp (any site) | Assuming installed yt-dlp is current | yt-dlp breaks against YouTube often; check version at startup and warn if older than 30 days |
| ffmpeg | Not checking exit code after clip extraction | ffmpeg exits 0 even on some partial failures; check that the output file exists and is >0 bytes |
| ffmpeg | Passing `-to` as absolute time instead of `-t` for duration | `-to` is output end time (absolute), `-t` is duration; using `-to` after placing `-ss` before `-i` requires careful arithmetic |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous yt-dlp download in async endpoint | Browser UI locks up during any download | Run download in thread via `asyncio.to_thread` or use `asyncio.create_subprocess_exec` | Immediately on first download request |
| No cache: re-downloading on every clip extraction | Each clip from the same video triggers a full re-download (30–120s wait) | Implement URL-keyed cache before building the clip extraction endpoint | From day one if cache is skipped |
| Loading entire video into memory for ffmpeg | OOM errors on large videos | Always pass file paths to ffmpeg, never pipe video bytes through Python | At ~500MB video files |
| ffprobe validation on every cache hit | Adds 0.5–2s latency to each clip extraction | Run ffprobe only during download (write a valid flag to sidecar), not on cache lookup | At any usage frequency |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `shell=True` with user-supplied URL/filename/timestamps | Arbitrary command execution on the local machine | Always pass args as Python list; `shell=False` |
| No validation on the output filename field | Directory traversal: `../../.ssh/authorized_keys` as filename writes to arbitrary paths | Strip path separators; resolve final output path and assert it is inside the configured output dir |
| Serving the entire cache directory as a static mount | Exposes all cached full-length videos at a predictable URL | Cache dir should not be a static mount; serve clips through a controlled endpoint |
| Accepting arbitrary URLs and passing to yt-dlp | SSRF-like: yt-dlp will attempt to fetch internal network URLs | Restrict accepted URL prefixes to known domains (youtube.com, youtu.be, bilibili.com, b23.tv) |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No loading state during download | User submits clip form, nothing happens for 30–120s; they click again, triggering duplicate downloads | Disable the form and show a spinner/status message as soon as extraction starts |
| No error message when yt-dlp fails | Silent failure; user does not know whether to retry or check the URL | Capture stderr from yt-dlp subprocess; surface a human-readable error in the UI |
| Clip timestamps accepted as free-form text without validation | User types `1:30` (valid) or `1m30s` (yt-dlp style) or `90` (seconds); inconsistent behavior | Normalize timestamp input: accept `MM:SS`, `HH:MM:SS`, and plain seconds; reject anything else with an inline error |
| Output filename accepted with extension | User types `clip.mp4` thinking they need the extension; tool produces `clip.mp4.mp4` | Strip `.mp4` extension from the filename field and always append it in code |
| Session clip list not updating after extraction | User extracts a clip and has no confirmation it worked | Refresh the session list automatically on successful extraction completion |

---

## "Looks Done But Isn't" Checklist

- [ ] **Download caching:** Does the cache check verify file integrity (size/ffprobe), not just file existence? Verify by interrupting a download mid-way and confirming the partial file is detected and re-downloaded.
- [ ] **ffmpeg clip extraction:** Do clips play in a browser `<video>` tag without black frames at the start? Verify by extracting a clip starting at a non-keyframe time (e.g., 1 second after a known I-frame).
- [ ] **Async download:** Does the FastAPI server respond to other requests while a download is in progress? Verify by opening the session list endpoint during an active download.
- [ ] **MP4 compatibility:** Do clips have working audio? Verify with a YouTube video that uses Opus audio (check with `ffprobe` first).
- [ ] **Output directory traversal:** Does a filename like `../../test` write outside the configured output folder? Verify with a path traversal attempt.
- [ ] **Play button:** Does the browser `<video>` element support seeking (not just play/pause)? Verify by loading a >10MB clip and dragging the seek bar.
- [ ] **yt-dlp version warning:** Does the tool detect and warn about an outdated yt-dlp installation? Verify by temporarily setting the version check threshold to 0 days.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stale/corrupt cache file | LOW | Delete the cache entry for that URL; next extraction triggers a fresh download automatically |
| Opus-in-MP4 mux failure | LOW | Update the yt-dlp format string to prefer `mp4+m4a`; existing broken cached files need to be deleted and re-downloaded |
| Clips with black-frame start | MEDIUM | Adjust `-ss` placement and add `-avoid_negative_ts make_zero`; existing clips need re-extraction (old clips are not automatically fixed) |
| Async blocking discovered late | MEDIUM | Migrate download call from sync endpoint to `asyncio.to_thread` or subprocess; no data migration needed, only code change |
| Directory traversal in output path | HIGH (security incident) | Immediately add path validation; audit all previously written files for unexpected locations |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| ffmpeg -c copy keyframe snapping / black frames | Core clip extraction (ffmpeg command design) | Extract a clip starting at a non-keyframe time; confirm no black frames in playback |
| Stale/corrupt cache (partial download) | Download + caching layer | Interrupt a download; confirm the partial file is detected and re-downloaded on next attempt |
| Blocking event loop during download | Backend API (download endpoint) | Run a simultaneous request during download; confirm it responds in <1s |
| Opus/WebM mux failure into MP4 | Download configuration (yt-dlp format string) | Download a YouTube video; confirm audio is present via `ffprobe` |
| Shell injection via user input | Backend API (all subprocess calls) | Pass a filename containing `;` or `&&`; confirm it is rejected or safely escaped |
| Browser video seek broken (no range support) | Frontend clip playback (play endpoint) | Load a >10MB clip in browser; confirm seek bar is functional |
| Output path directory traversal | Backend API (filename/output path validation) | Pass `../../test` as filename; confirm file is rejected or written inside output dir only |

---

## Sources

- [yt-dlp GitHub Issue #10808 — yt-dlp considers partial files successful downloads](https://github.com/yt-dlp/yt-dlp/issues/10808)
- [yt-dlp GitHub Issue #5463 — How to delete unfinished cache files when download fails](https://github.com/yt-dlp/yt-dlp/issues/5463)
- [yt-dlp GitHub Issue #9487 — yt-dlp with asyncio multiprocessing](https://github.com/yt-dlp/yt-dlp/issues/9487)
- [FastAPI Discussion #8842 — FastAPI blocking long running requests with asyncio calls](https://github.com/fastapi/fastapi/discussions/8842)
- [LosslessCut PR #13 — ffmpeg argument order and keyframe cutting](https://github.com/mifi/lossless-cut/pull/13)
- [LosslessCut Issue #1216 — How to seek to and cut from a frame in ffmpeg](https://github.com/mifi/lossless-cut/issues/1216)
- [LosslessCut Discussion #1874 — avoid_negative_ts behavior](https://github.com/mifi/lossless-cut/discussions/1874)
- [FFmpeg Wiki — Seeking](https://fftrac-bg.ffmpeg.org/wiki/Seeking)
- [Hacker News — FFmpeg awful handling of timestamps by default](https://news.ycombinator.com/item?id=26372148)
- [yt-dlp Issue #5272 — Request format not available when using best](https://github.com/yt-dlp/yt-dlp/issues/5272)
- [Bilibili "No video formats found" Issue #14805](https://github.com/yt-dlp/yt-dlp/issues/14805)
- [FastAPI — Streaming video with range requests](https://github.com/fastapi/fastapi/discussions/7718)
- [Sourcery — Python subprocess shell=True vulnerability](https://www.sourcery.ai/vulnerabilities/python-lang-security-audit-subprocess-shell-true)
- [Snyk — Command injection in Python: examples and prevention](https://snyk.io/blog/command-injection-python-prevention-examples/)

---

*Pitfalls research for: Local Python web tool wrapping yt-dlp + ffmpeg (Drill Clip Extractor)*
*Researched: 2026-03-19*
