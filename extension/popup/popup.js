const DEFAULT_BASE = "http://127.0.0.1:3003";

const apiInput = document.getElementById("api-base");
const statusEl = document.getElementById("status");
const testBtn = document.getElementById("test");

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || "";
}

chrome.storage.sync.get({ apiBase: DEFAULT_BASE }, (stored) => {
  apiInput.value = stored.apiBase || DEFAULT_BASE;
});

testBtn.addEventListener("click", async () => {
  const base = apiInput.value.trim().replace(/\/$/, "") || DEFAULT_BASE;
  await chrome.storage.sync.set({ apiBase: base });
  setStatus("Checking…", "");
  testBtn.disabled = true;
  try {
    const res = await chrome.runtime.sendMessage({ type: "ping" });
    if (res?.ok) {
      const ffmpeg = res.body?.ffmpeg ? "ffmpeg OK" : "ffmpeg missing";
      setStatus(`Connected (${ffmpeg})`, "ok");
    } else {
      setStatus(res?.error || "Connection failed", "err");
    }
  } catch (err) {
    setStatus(String(err.message || err), "err");
  } finally {
    testBtn.disabled = false;
  }
});
