(function () {
  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
    const total = Math.floor(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return `${h}:${pad2(m)}:${pad2(s)}`;
    return `${m}:${pad2(s)}`;
  }

  function parseTime(text) {
    const raw = String(text || "").trim();
    if (!raw) throw new Error("Empty time");
    const parts = raw.split(":").map((p) => p.trim());
    if (parts.length === 1) return Number(parts[0]);
    if (parts.length === 2) return Number(parts[0]) * 60 + Number(parts[1]);
    if (parts.length === 3) {
      return Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2]);
    }
    throw new Error(`Invalid time: ${raw}`);
  }

  window.DrillMarkers = { formatTime, parseTime };
})();
