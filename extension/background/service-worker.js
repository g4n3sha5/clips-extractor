const DEFAULT_BASE = "http://127.0.0.1:3003";

try {
  importScripts("../lib/extract-page-media.js");
} catch (err) {
  console.warn("Drill Clips: could not import extract-page-media.js", err);
}

async function getApiBase() {
  const stored = await chrome.storage.sync.get({ apiBase: DEFAULT_BASE });
  return (stored.apiBase || DEFAULT_BASE).replace(/\/$/, "");
}

async function apiFetch(path, options = {}) {
  const base = await getApiBase();
  const url = `${base}${path}`;
  let response;
  try {
    response = await fetch(url, options);
  } catch (err) {
    throw new Error(
      `Cannot reach ${url}: ${err.message || err}. Is the app running on that port?`
    );
  }
  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { detail: text };
    }
  }
  if (!response.ok) {
    const detail =
      (body && (body.detail || body.message)) ||
      `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function parseApiResponse(response, text) {
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { detail: text };
    }
  }
  if (!response.ok) {
    const detail =
      (body && (body.detail || body.message)) ||
      `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

const activeUploads = new Map();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "ping") {
    apiFetch("/api/health")
      .then((body) => sendResponse({ ok: true, body }))
      .catch((err) => sendResponse({ ok: false, error: String(err.message || err) }));
    return true;
  }

  if (message?.type === "openOutputDir") {
    apiFetch("/api/config/open-output-dir", { method: "POST" })
      .then((body) => sendResponse({ ok: true, body }))
      .catch((err) => sendResponse({ ok: false, error: String(err.message || err) }));
    return true;
  }

  if (message?.type === "extractPageMedia") {
    const tabId = sender.tab && sender.tab.id;
    if (!tabId || typeof chrome.scripting === "undefined") {
      sendResponse({ ok: false, error: "Reload the extension (needs scripting permission)." });
      return false;
    }
    chrome.scripting
      .executeScript({
        target: { tabId },
        world: "MAIN",
        func: extractMediaDescriptor,
      })
      .then((results) => {
        const found = results && results[0] && results[0].result;
        if (!found || !found.videoUrl) {
          sendResponse({
            ok: false,
            error:
              "Could not read stream URLs from this player. Wait until the video is playing, then try again.",
          });
          return;
        }
        sendResponse({ ok: true, body: found });
      })
      .catch((err) => sendResponse({ ok: false, error: String(err.message || err) }));
    return true;
  }

  if (message?.type === "fetchInPage") {
    const tabId = sender.tab && sender.tab.id;
    if (!tabId || typeof chrome.scripting === "undefined") {
      sendResponse({ ok: false, error: "Reload the extension (needs scripting permission)." });
      return false;
    }
    chrome.scripting
      .executeScript({
        target: { tabId },
        world: "MAIN",
        func: drillFetchMediaStream,
        args: [message.url, message.requestId],
      })
      .then(() => sendResponse({ ok: true }))
      .catch((err) => sendResponse({ ok: false, error: String(err.message || err) }));
    return true;
  }

  if (message?.type === "fetchMediaUrl") {
    (async () => {
      const headers = {};
      if (message.referrer) headers.Referer = message.referrer;
      const response = await fetch(message.url, { headers });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const buf = await response.arrayBuffer();
      return { buf, contentType: response.headers.get("content-type") || "" };
    })()
      .then((body) => sendResponse({ ok: true, body }))
      .catch((err) => sendResponse({ ok: false, error: String(err.message || err) }));
    return true;
  }

  if (message?.type === "cancelUpload") {
    const id = message.uploadId;
    const controller = id ? activeUploads.get(id) : null;
    if (controller) {
      controller.abort();
      activeUploads.delete(id);
      sendResponse({ ok: true });
    } else {
      sendResponse({ ok: false, error: "No active upload" });
    }
    return false;
  }

  if (message?.type === "uploadRecording") {
    (async () => {
      const base = await getApiBase();
      const url = `${base}/api/clips/from-recording`;
      const form = new FormData();
      form.append("file", message.blob, message.filename || "recording.webm");
      form.append("filename", message.clipFilename);
      form.append("start", message.start);
      form.append("end", message.end);
      form.append("source_url", message.sourceUrl);

      const uploadId = message.uploadId || String(Date.now());
      const controller = new AbortController();
      activeUploads.set(uploadId, controller);

      let response;
      try {
        response = await fetch(url, {
          method: "POST",
          body: form,
          signal: controller.signal,
        });
      } catch (err) {
        activeUploads.delete(uploadId);
        if (err.name === "AbortError") {
          const e = new Error("Cancelled");
          e.name = "AbortError";
          throw e;
        }
        throw new Error(
          `Cannot reach ${url}: ${err.message || err}. Is the app running on that port?`
        );
      }
      activeUploads.delete(uploadId);
      const text = await response.text();
      return parseApiResponse(response, text);
    })()
      .then((body) => sendResponse({ ok: true, body }))
      .catch((err) => {
        const cancelled = err && err.name === "AbortError";
        sendResponse({
          ok: false,
          cancelled,
          error: cancelled ? "Cancelled" : String(err.message || err),
        });
      });
    return true;
  }

  if (message?.type === "uploadBrowserCache") {
    (async () => {
      const base = await getApiBase();
      const url = `${base}/api/cache/from-browser`;
      const form = new FormData();
      form.append("video", message.videoBlob, message.videoFilename || "video.mp4");
      if (message.audioBlob) {
        form.append("audio", message.audioBlob, message.audioFilename || "audio.m4a");
      }
      form.append("source_url", message.sourceUrl);
      form.append("title", message.title || "");

      const uploadId = message.uploadId || String(Date.now());
      const controller = new AbortController();
      activeUploads.set(uploadId, controller);

      let response;
      try {
        response = await fetch(url, {
          method: "POST",
          body: form,
          signal: controller.signal,
        });
      } catch (err) {
        activeUploads.delete(uploadId);
        if (err.name === "AbortError") {
          const e = new Error("Cancelled");
          e.name = "AbortError";
          throw e;
        }
        throw new Error(
          `Cannot reach ${url}: ${err.message || err}. Is the app running on that port?`
        );
      }
      activeUploads.delete(uploadId);
      const text = await response.text();
      return parseApiResponse(response, text);
    })()
      .then((body) => sendResponse({ ok: true, body }))
      .catch((err) => {
        const cancelled = err && err.name === "AbortError";
        sendResponse({
          ok: false,
          cancelled,
          error: cancelled ? "Cancelled" : String(err.message || err),
        });
      });
    return true;
  }

  return false;
});
