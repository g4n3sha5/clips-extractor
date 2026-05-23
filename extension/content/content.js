(function () {
  const PANEL_ID = "drill-clips-panel";
  const HOST = location.hostname;
  const STORAGE_KEY = `panelMinimized:${HOST}`;
  const DEFAULT_MINIMIZED = /(^|\.)youtube\.com$|(^|\.)youtu\.be$/.test(HOST);

  function loadMinimized() {
    return new Promise((resolve) => {
      try {
        chrome.storage.sync.get(STORAGE_KEY, (stored) => {
          const val = stored ? stored[STORAGE_KEY] : undefined;
          resolve(val === undefined ? DEFAULT_MINIMIZED : !!val);
        });
      } catch {
        resolve(DEFAULT_MINIMIZED);
      }
    });
  }

  function saveMinimized(minimized) {
    try {
      chrome.storage.sync.set({ [STORAGE_KEY]: !!minimized });
    } catch {
      /* ignore — storage may be unavailable */
    }
  }

  function findVideo() {
    const candidates = Array.from(document.querySelectorAll("video"));
    if (!candidates.length) return null;
    let best = candidates[0];
    let bestArea = 0;
    for (const v of candidates) {
      const r = v.getBoundingClientRect();
      const area = r.width * r.height;
      if (area > bestArea) {
        bestArea = area;
        best = v;
      }
    }
    return best;
  }

  function defaultFilename() {
    const t = document.title || "clip";
    return t.replace(/[^\w.-]+/g, "_").slice(0, 48) || "clip";
  }

  async function buildPanel() {
    if (document.getElementById(PANEL_ID)) return;

    const panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.innerHTML = `
      <button type="button" class="launcher" title="Drill Clips — click to expand">DC</button>
      <div class="panel-inner">
        <button type="button" class="toggle" title="Minimize">−</button>
        <h2>Drill Clips</h2>
        <div class="body">
          <div class="row">
            <label>In</label>
            <input type="text" id="drill-in" placeholder="0:00" />
            <button type="button" id="drill-mark-in" title="Use current video time">Mark</button>
          </div>
          <div class="row">
            <label>Out</label>
            <input type="text" id="drill-out" placeholder="0:00" />
            <button type="button" id="drill-mark-out" title="Use current video time">Mark</button>
          </div>
          <div class="row">
            <label>Name</label>
            <input type="text" id="drill-filename" />
          </div>
          <button type="button" class="primary" id="drill-export">Export to Drill Clips</button>
          <div class="status" id="drill-status"></div>
        </div>
      </div>
    `;

    document.body.appendChild(panel);

    const launcher = panel.querySelector(".launcher");
    const toggle = panel.querySelector(".toggle");

    function applyMinimized(minimized) {
      panel.classList.toggle("minimized", !!minimized);
    }

    applyMinimized(await loadMinimized());

    toggle.addEventListener("click", () => {
      applyMinimized(true);
      saveMinimized(true);
    });
    launcher.addEventListener("click", () => {
      applyMinimized(false);
      saveMinimized(false);
    });

    const inInput = panel.querySelector("#drill-in");
    const outInput = panel.querySelector("#drill-out");
    const nameInput = panel.querySelector("#drill-filename");
    const statusEl = panel.querySelector("#drill-status");
    nameInput.value = defaultFilename();

    function setStatus(msg, kind) {
      statusEl.textContent = msg || "";
      statusEl.className = "status" + (kind ? ` ${kind}` : "");
    }

    panel.querySelector("#drill-mark-in").addEventListener("click", () => {
      const video = findVideo();
      if (!video) {
        setStatus("No video player found on this page.", "error");
        return;
      }
      inInput.value = DrillMarkers.formatTime(video.currentTime);
      setStatus("");
    });

    panel.querySelector("#drill-mark-out").addEventListener("click", () => {
      const video = findVideo();
      if (!video) {
        setStatus("No video player found on this page.", "error");
        return;
      }
      outInput.value = DrillMarkers.formatTime(video.currentTime);
      setStatus("");
    });

    const exportBtn = panel.querySelector("#drill-export");
    const EXPORT_LABEL = "Export to Drill Clips";
    exportBtn.textContent = EXPORT_LABEL;

    let confirmTimer = null;
    let pendingConfirm = false;
    let recordingAbort = null;
    let currentUploadId = null;

    function resetButton() {
      pendingConfirm = false;
      recordingAbort = null;
      currentUploadId = null;
      if (confirmTimer) {
        clearTimeout(confirmTimer);
        confirmTimer = null;
      }
      exportBtn.textContent = EXPORT_LABEL;
      exportBtn.disabled = false;
    }

    async function runExport() {
      const video = findVideo();
      if (!video) {
        setStatus("No video player found on this page.", "error");
        resetButton();
        return;
      }

      let startSec;
      let endSec;
      try {
        startSec = DrillMarkers.parseTime(inInput.value);
        endSec = DrillMarkers.parseTime(outInput.value);
      } catch (err) {
        setStatus(err.message || "Invalid in/out times", "error");
        resetButton();
        return;
      }

      recordingAbort = new AbortController();
      currentUploadId = String(Date.now()) + "-" + Math.random().toString(36).slice(2, 8);
      exportBtn.textContent = "Cancel";
      exportBtn.disabled = false;
      setStatus("Recording segment…");

      try {
        const blob = await DrillRecording.recordSegment(
          video,
          startSec,
          endSec,
          (info) => {
            const t = DrillMarkers.formatTime(info.currentTime);
            const end = DrillMarkers.formatTime(endSec);
            if (info.paused) {
              setStatus(
                `Paused at ${t} / ${end} — press play on the video to continue (or Cancel)`,
                "warn"
              );
            } else {
              setStatus(`Recording ${t} / ${end} (click Cancel to stop)`);
            }
          },
          recordingAbort.signal
        );

        setStatus("Uploading to Drill Clip Extractor…");
        const clipFilename = (nameInput.value || "clip").trim();
        const ext = blob.type.includes("mp4") ? "mp4" : "webm";

        const response = await chrome.runtime.sendMessage({
          type: "uploadRecording",
          uploadId: currentUploadId,
          blob,
          filename: `recording.${ext}`,
          clipFilename,
          start: inInput.value,
          end: outInput.value,
          sourceUrl: window.location.href,
        });

        if (!response?.ok) {
          if (response?.cancelled) {
            setStatus("Cancelled.", "");
          } else {
            throw new Error(response?.error || "Upload failed");
          }
        } else {
          const saved = response.body?.filename || clipFilename;
          setStatus(`Saved: ${saved}`, "ok");
        }
      } catch (err) {
        if (err && err.name === "AbortError") {
          setStatus("Cancelled.", "");
        } else {
          setStatus(err.message || String(err), "error");
        }
      } finally {
        resetButton();
      }
    }

    function cancelInFlight() {
      if (recordingAbort) {
        try {
          recordingAbort.abort();
        } catch {
          /* ignore */
        }
      }
      if (currentUploadId) {
        chrome.runtime
          .sendMessage({ type: "cancelUpload", uploadId: currentUploadId })
          .catch(() => {});
      }
      setStatus("Cancelling…");
    }

    exportBtn.addEventListener("click", () => {
      if (recordingAbort || currentUploadId) {
        cancelInFlight();
        return;
      }

      if (pendingConfirm) {
        runExport();
        return;
      }

      const video = findVideo();
      if (!video) {
        setStatus("No video player found on this page.", "error");
        return;
      }

      let startSec;
      let endSec;
      try {
        startSec = DrillMarkers.parseTime(inInput.value);
        endSec = DrillMarkers.parseTime(outInput.value);
      } catch (err) {
        setStatus(err.message || "Invalid in/out times", "error");
        return;
      }

      if (!(endSec > startSec)) {
        setStatus("End must be after start.", "error");
        return;
      }

      const dur = endSec - startSec;
      const inStr = DrillMarkers.formatTime(startSec);
      const outStr = DrillMarkers.formatTime(endSec);
      const durStr = DrillMarkers.formatTime(dur);

      pendingConfirm = true;
      let remaining = 5;
      exportBtn.textContent = `Confirm ${inStr} → ${outStr} (${durStr}) — ${remaining}s`;
      setStatus("Click again to start recording, or wait to cancel.");

      const tick = () => {
        remaining -= 1;
        if (remaining <= 0) {
          resetButton();
          setStatus("");
          return;
        }
        exportBtn.textContent = `Confirm ${inStr} → ${outStr} (${durStr}) — ${remaining}s`;
        confirmTimer = setTimeout(tick, 1000);
      };
      confirmTimer = setTimeout(tick, 1000);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildPanel);
  } else {
    buildPanel();
  }
})();
