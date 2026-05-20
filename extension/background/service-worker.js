const DEFAULT_BASE = "http://127.0.0.1:3003";

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

const activeUploads = new Map();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "ping") {
    apiFetch("/api/health")
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
