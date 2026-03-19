# Feature Research

**Domain:** Local video clip extraction / instructional annotation tool
**Researched:** 2026-03-19
**Confidence:** HIGH (core features), MEDIUM (differentiators), LOW (anti-features based on domain reasoning)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Paste URL → extract clip | The entire job of the tool; everything else flows from this | LOW | yt-dlp handles download, ffmpeg -c copy handles cut |
| Start/end timestamp input | No timestamp = no clip; core data primitive | LOW | HH:MM:SS or MM:SS; ffmpeg accepts both |
| Filename input | Every extracted file needs an identity | LOW | No filename = unnamed chaos in output folder |
| Download caching by URL | Users watch long instructionals (1-4 hrs); re-downloading every clip would take minutes | MEDIUM | Cache key = URL, stored in ~/.drillclips/cache/ or similar |
| Output folder configuration | Users want clips somewhere specific, not buried in an app dir | LOW | Configured once; persists across sessions |
| Session clip list | User needs to see what they've extracted during the current work session | LOW | Filename, timestamp range, play button per row |
| In-browser clip playback | Verify the clip without leaving the tool | LOW | HTML5 `<video>` element; trivial given local file path |
| Download/extraction progress feedback | Long downloads stall with no feedback; users refresh or rage-quit | MEDIUM | SSE or WebSocket from FastAPI; show % or status text |
| Error messaging | yt-dlp fails on geo-blocked, private, or unsupported URLs; ffmpeg fails on bad ranges | MEDIUM | Surface the actual error, not a silent failure |
| Keyboard-first form flow | The core value prop is "stamp out clips without friction"; mouse-heavy forms break that | LOW | Tab order, Enter to submit, no click-only interactions |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Description field with auto-suggest template | Drill clips without context decay over time; a structured freeform note (source, tags, URL, range, notes) means clips are self-documenting | LOW | Textarea pre-filled with template tokens; user overwrites freely. Aligns with hidden JSON metadata sidecar |
| Hidden JSON metadata sidecar | Clips remain portable (plain MP4 files) while machine-readable metadata lives alongside for future tooling (search, indexing, tagging) | LOW | Write `<filename>.json` next to `<filename>.mp4`; never shown in UI |
| Bilibili support out of the box | Most clip tools target YouTube only; Bilibili hosts significant grappling/martial arts instructional content (e.g. Chinese wrestling, judo, sanda) | LOW | yt-dlp already handles Bilibili; no extra work required |
| Per-session clip history with range display | Quickly verify "did I already clip this technique?" without opening a file manager | LOW | In-memory during session; shown as `00:04:12 → 00:05:30` |
| Timestamp validation before extraction | Catches "end before start" and "range outside video duration" before ffmpeg runs | LOW | Client-side validation + server-side guard |
| ffmpeg -c copy enforcement (lossless, fast) | Re-encoding a 5-minute clip at 720p takes 10-30 seconds; stream copy takes under 1 second | LOW | Already a constraint; worth surfacing in UI ("instant extract") |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Video preview / scrubbing in browser | "I want to find my start point visually" | Serving a multi-GB cached video file through FastAPI for in-browser seeking requires range request support, chunked transfer, and adds meaningful complexity with no speed benefit for someone who already watched the video | Open the cached file in VLC or system player with a single button; or accept that users already know the timestamps from watching |
| Thumbnails for clip list | "I want to see what each clip looks like" | Requires either ffmpeg thumbnail extraction pass (extra subprocess per clip) or storing frame images alongside clips; adds storage and latency | Show filename and timestamp range; that's sufficient for recall in a session |
| Batch import of timestamp CSV | "I have a spreadsheet of 50 clips" | Sounds useful but shifts the primary UX from fast incremental stamping to upfront planning; creates a validation nightmare for 50 rows | Let the existing form handle clips one by one; it's fast enough |
| Clip editing / trimming after extraction | "I cut it slightly wrong, let me adjust" | Makes the tool a video editor; scope explosion | Re-enter the form with corrected timestamps and re-extract; with -c copy it takes under a second |
| Quality selection UI | "Sometimes I want 1080p" | PROJECT.md explicitly caps at 720p for file size reasons; exposing quality selection invites scope debates and support burden | Hard-code 720p; document the rationale |
| Persistent library / database of all clips ever | "Show me everything I've ever extracted" | Requires a database, migrations, and a browse/search UI — becomes a different product | Hidden JSON sidecars enable future tooling; the session list covers current-session recall |
| Authentication / multi-user | "Share this with my training partners" | This is a local single-user tool; adding auth means session management, CORS hardening, user model — wrong problem to solve | Run one instance per person; it's a localhost tool |

---

## Feature Dependencies

```
[Output folder config]
    └──required by──> [Clip extraction]
                           └──required by──> [Session clip list]
                                                  └──required by──> [In-browser playback]

[URL input]
    └──required by──> [Download + cache]
                           └──required by──> [Clip extraction]

[Timestamp input]
    └──required by──> [Timestamp validation]
                           └──required by──> [Clip extraction]

[Clip extraction]
    └──required by──> [JSON metadata sidecar]

[Description field] ──enhances──> [JSON metadata sidecar]
    (description text is written into the sidecar)

[Download progress feedback] ──enhances──> [URL input / download step]
    (feedback is only meaningful during download)

[Bilibili support] ──no extra dep──> [URL input]
    (yt-dlp handles it transparently)
```

### Dependency Notes

- **Output folder config requires Clip extraction:** Extraction cannot write anywhere without knowing the target directory. This must be configured before first use.
- **URL input requires Download + cache:** The URL is the cache key. Cache lookup happens before any download attempt.
- **Timestamp validation requires Timestamp input:** Validation is a guard layer on the inputs, not a separate feature.
- **Description field enhances JSON metadata sidecar:** The sidecar is written at extraction time; the description becomes a field inside it. If description is blank, sidecar still writes with empty notes field.
- **Session clip list requires Clip extraction:** The list is populated by successful extractions. It does not persist across server restarts by design (session = one work sitting).

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the core workflow.

- [ ] URL input (YouTube + Bilibili) — the entry point of every workflow
- [ ] Download with caching by URL — the slow step; must only happen once per instructional
- [ ] Timestamp range + filename input — the core data of every clip
- [ ] ffmpeg -c copy extraction to output folder — the deliverable
- [ ] Download/extraction progress feedback — without this, the tool feels broken during the 30-120 second download
- [ ] Session clip list with filename, range, play button — verify the clip without leaving the tool
- [ ] Output folder configuration (configured once) — clips need a home
- [ ] Error messaging for yt-dlp and ffmpeg failures — silent failures are unusable
- [ ] Keyboard-friendly form (Tab, Enter) — core value prop: low friction

### Add After Validation (v1.x)

Features to add once core workflow is confirmed working.

- [ ] Description field with auto-suggest template — add when users confirm they want clip documentation alongside extraction
- [ ] Timestamp validation (client + server) — add after v1 proves the form works; prevents a class of frustrating errors
- [ ] JSON metadata sidecar — add alongside description field; they're coupled

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Persistent clip library across sessions — requires storage design; defer until session-based model proves insufficient
- [ ] Tag-based search of sidecars — only valuable after many clips accumulate
- [ ] Bulk re-extraction (e.g., if output folder changes) — edge case; defer

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| URL input + download with cache | HIGH | MEDIUM | P1 |
| Timestamp + filename form | HIGH | LOW | P1 |
| ffmpeg -c copy extraction | HIGH | LOW | P1 |
| Download/extraction progress | HIGH | MEDIUM | P1 |
| Session clip list + playback | HIGH | LOW | P1 |
| Output folder config | HIGH | LOW | P1 |
| Error messaging | HIGH | LOW | P1 |
| Keyboard-first form flow | HIGH | LOW | P1 |
| Description field + template | MEDIUM | LOW | P2 |
| JSON metadata sidecar | MEDIUM | LOW | P2 |
| Timestamp validation | MEDIUM | LOW | P2 |
| Bilibili support | MEDIUM | LOW | P2 (yt-dlp handles it; just needs testing) |
| Persistent clip library | LOW | HIGH | P3 |
| Thumbnail extraction | LOW | MEDIUM | P3 |
| Batch CSV import | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Tools surveyed: LosslessCut (desktop, lossless video cutter), Parabolic (yt-dlp GUI), CutYT/Cutter.yt (online YouTube cutters), Kinovea (sports video annotation)

| Feature | LosslessCut | Parabolic | Online cutters (CutYT etc.) | Our approach |
|---------|-------------|-----------|----------------------------|--------------|
| Download from URL | No (local files only) | Yes | Yes | Yes — yt-dlp |
| Lossless cut (-c copy) | Yes (core feature) | No (full download, no cut) | No (re-encode) | Yes — ffmpeg -c copy |
| Caching downloaded source | N/A | No | No | Yes — cache by URL |
| Keyboard-first workflow | Yes (I/O keys, arrow nav) | No | No | Yes — form Tab/Enter flow |
| Session clip list | No | No | No | Yes |
| Clip metadata / annotations | Labels and tags on segments | No | No | Yes — description + JSON sidecar |
| Bilibili support | N/A | Yes (via yt-dlp) | No | Yes (via yt-dlp) |
| Progress feedback | Yes (built-in player) | Yes (download queue) | Yes (progress bar) | Yes — SSE/WebSocket from FastAPI |
| In-browser playback | No (system player) | No | Yes | Yes — HTML5 video |
| Complexity / setup | Medium (Electron app) | Medium (installable app) | None (web) | Low (localhost FastAPI) |

**Key gap this tool fills:** No existing tool combines (1) download-from-URL, (2) lossless stream-copy cut, (3) caching, and (4) a fast keyboard-driven form with session tracking in a single minimal local tool.

---

## Sources

- [LosslessCut README (GitHub)](https://github.com/mifi/lossless-cut/blob/master/README.md) — feature list, keyboard shortcuts
- [LosslessCut keyboard shortcuts — DefKey](https://defkey.com/losslesscut-2025-shortcuts) — I/O mark-in/out pattern
- [Parabolic: yt-dlp GUI for Linux](https://www.linuxfordevices.com/tutorials/linux/parabolic-gui-frontend-for-yt-dlp) — yt-dlp GUI feature reference
- [yt-dlp app features](https://yt-dlp.app/features) — canonical yt-dlp capability list
- [rendi.dev: Using FFmpeg with yt-dlp](https://www.rendi.dev/post/using-ffmpeg-with-yt-dlp) — ffmpeg integration patterns
- [Kinovea](https://www.kinovea.org/) — sports video annotation reference
- [AlternativeTo: LosslessCut alternatives](https://alternativeto.net/software/lossless-cut/) — competitive landscape
- [BJJ study tools landscape (Grappling AI, Digitsu, BJJFlowCharts)](https://grapplingaiapp.com/) — user workflow context for martial arts instructional use case

---
*Feature research for: local video clip extraction / instructional annotation tool (Drill Clip Extractor)*
*Researched: 2026-03-19*
