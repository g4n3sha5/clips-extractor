# Drill Clip Extractor — browser extension

Marks **in/out** on a Bilibili or YouTube page, **records** that segment from the in-page player (with audio on macOS via Web Audio), and sends it to your local [Drill Clip Extractor](../README.md) app. This bypasses server-side `yt-dlp` / geo blocks for Bilibili when you can play the video in the browser.

## Requirements

- Drill Clip Extractor running locally (`uv run uvicorn main:app --reload --port 3003`)
- **ffmpeg** on `PATH` (same as the main app)
- Chrome, Edge, Brave, or Firefox (temporary add-on)

## Install (no store)

### Chrome / Edge / Brave

1. Start the app on port **3003** (see main README).
2. Open `chrome://extensions` (or `edge://extensions`).
3. Enable **Developer mode**.
4. Click **Load unpacked** and select this folder: `extension/`.
5. Click the extension icon → **Test connection** should show “Connected”.

### Firefox

The same `extension/` folder works in Firefox. The manifest already includes a Gecko `background.scripts` fallback and a `browser_specific_settings.gecko.id`, so no edits are required.

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on…** and pick **any file inside** `extension/` (e.g. `manifest.json`).
3. Confirm the extension appears in the list. Click **Inspect** to open its console if something fails.
4. The Drill Clips panel will show up on Bilibili / YouTube on next navigation. Reload an already-open tab if needed.

Notes for Firefox:

- **Temporary add-ons are removed on browser restart.** Re-load it from `about:debugging` after each restart, or sign and install a packaged `.xpi` via [addons.mozilla.org](https://addons.mozilla.org) for persistence.
- Firefox uses **`mozCaptureStream()`** under the hood — already handled by `lib/recording.js`.
- Firefox enforces strict CSP on some pages; if the panel doesn't appear, open the **Browser Console** (Ctrl/Cmd + Shift + J) and check for content-script errors.
- `chrome.*` namespace works in Firefox (no need for `browser.*` polyfill here).

## Usage

1. Open a video on **bilibili.com** or **youtube.com** (with VPN/cookies if needed).
2. Use the floating **Drill Clips** panel (bottom-right):
   - **Mark** at start and end while the video plays or is paused.
   - Set a **filename** (saved as `.mp4` in your clips folder).
   - **Export to Drill Clips** — records the segment and uploads to the app.
3. Open `http://127.0.0.1:3003` to see the clip in your session list.

## Audio on macOS

Plain `video.captureStream()` often records **video only** on Mac. This extension merges:

- Video from `captureStream()`
- Audio from **Web Audio** (`createMediaElementSource`)

**Tips if there is no sound:**

- Click the video once before exporting (unlocks `AudioContext`).
- Keep the tab unmuted; don’t use Bluetooth output that blocks capture.
- If it still fails, the page may block audio routing (rare on Bilibili/YouTube players).

## Settings

Extension popup → **App URL** (default `http://127.0.0.1:3003`). Stored in `chrome.storage.sync`.

## Permissions

- **storage** — save API base URL
- **host_permissions** — Bilibili/YouTube pages + localhost API

## Troubleshooting

**`NetworkError when attempting to fetch resource`**

- App not running on the configured port. Start it: `uv run uvicorn main:app --reload --port 3003`.
- Firefox **HTTPS-Only Mode** can block `http://127.0.0.1`. Open `about:preferences#privacy` → scroll to **HTTPS-Only Mode** → **Don't enable** OR add an exception for `http://127.0.0.1`.
- Wrong port in the popup's **App URL** field — set it to `http://127.0.0.1:3003` and click **Test connection**.
- After updating the app to add CORS, **restart `uvicorn`** so the new middleware is loaded.

**Can't type in `In` / `Out`**

- Both fields are editable text — type `M:SS` (e.g. `1:23`) or `H:MM:SS` directly, or use the **Mark** button to capture the current video time.

**`No video player found on this page`**

- The script picks the largest `<video>` on the page. Wait until the main player is visible (Bilibili sometimes shows an ad first). Reload the panel by reloading the tab.

**Recording has no audio (macOS)**

- Click the video once before exporting (Web Audio needs a user gesture).
- Unmute the tab.

## Manual test checklist

- [ ] Popup: Test connection → Connected
- [ ] Bilibili: mark in/out, export short clip, appears in web UI
- [ ] Exported file plays with audio
- [ ] App shows error if not running

## Limitations (MVP)

- Records by playing the segment in real time (not instant trim).
- Max segment length **10 minutes** (guard in extension).
- DRM-protected players are not supported.
- Does not download the full video — only the marked segment.
