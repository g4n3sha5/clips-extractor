/* Self-contained: serialized into the page MAIN world via chrome.scripting. */

function extractMediaDescriptor() {
  function isHttpUrl(value) {
    return typeof value === "string" && /^https?:\/\//i.test(value);
  }

  function streamUrl(item) {
    if (!item || typeof item !== "object") return "";
    const candidates = [
      item.baseUrl,
      item.base_url,
      item.baseURL,
      item.url,
      item.backupUrl && item.backupUrl[0],
      item.backup_url && item.backup_url[0],
    ];
    for (const c of candidates) {
      if (isHttpUrl(c)) return c;
    }
    return "";
  }

  function pickDash(dash, title, pageUrl) {
    if (!dash || typeof dash !== "object") return null;
    const videos = Array.isArray(dash.video) ? dash.video : [];
    const audios = Array.isArray(dash.audio) ? dash.audio : [];
    const withUrl = videos.filter((v) => streamUrl(v));
    if (!withUrl.length) return null;

    const under720 = withUrl.filter((v) => !v.height || Number(v.height) <= 720);
    const pool = under720.length ? under720 : withUrl;
    pool.sort((a, b) => {
      const ac = /avc/i.test(String(a.codecs || a.codec || "")) ? 1 : 0;
      const bc = /avc/i.test(String(b.codecs || b.codec || "")) ? 1 : 0;
      if (ac !== bc) return bc - ac;
      const ah = Number(a.height || 0);
      const bh = Number(b.height || 0);
      if (ah !== bh) return bh - ah;
      return Number(b.bandwidth || b.bandWidth || 0) - Number(a.bandwidth || a.bandWidth || 0);
    });
    const audioPool = audios.filter((a) => streamUrl(a));
    audioPool.sort(
      (a, b) => Number(b.bandwidth || b.bandWidth || 0) - Number(a.bandwidth || a.bandWidth || 0)
    );
    const video = pool[0];
    const audio = audioPool[0];
    return {
      videoUrl: streamUrl(video),
      audioUrl: audio ? streamUrl(audio) : null,
      height: video.height || null,
      title: title || document.title || "",
      pageUrl: pageUrl || location.href,
      source: "dash",
    };
  }

  function pickDurl(data, title, pageUrl) {
    const durl = data && (data.durl || data.duRL);
    if (!Array.isArray(durl) || !durl[0]) return null;
    const url = durl[0].url || durl[0].baseUrl;
    if (!isHttpUrl(url)) return null;
    return {
      videoUrl: url,
      audioUrl: null,
      height: data.quality || null,
      title: title || document.title || "",
      pageUrl: pageUrl || location.href,
      source: "durl",
    };
  }

  function fromPlayinfo(playinfo, title) {
    if (!playinfo || typeof playinfo !== "object") return null;
    const data = playinfo.data || playinfo.result || playinfo;
    return pickDash(data.dash, title, location.href) || pickDurl(data, title, location.href);
  }

  function biliTitle() {
    const state = window.__INITIAL_STATE__;
    const videoData = state && state.videoData;
    if (!videoData) {
      const media = state && state.mediaInfo;
      return (media && media.title) || document.title || "";
    }
    const params = new URLSearchParams(location.search);
    const p = parseInt(params.get("p") || "1", 10);
    const pages = videoData.pages || [];
    const part = pages[p - 1] && pages[p - 1].part;
    const base = videoData.title || "";
    return part && pages.length > 1 ? `${base} - ${part}` : base || document.title || "";
  }

  async function fetchBiliPlayurl() {
    const state = window.__INITIAL_STATE__;
    if (!state) return null;
    const videoData = state.videoData || {};
    const epInfo = state.epInfo || {};
    const bvid = videoData.bvid || epInfo.bvid;
    let cid = videoData.cid || epInfo.cid;
    const params = new URLSearchParams(location.search);
    const p = parseInt(params.get("p") || "1", 10);
    const pages = videoData.pages || [];
    if (pages[p - 1] && pages[p - 1].cid) cid = pages[p - 1].cid;
    if (!cid) return null;
    const qs = new URLSearchParams({
      cid: String(cid),
      qn: "64",
      fnval: "16",
      fnver: "0",
      fourk: "1",
    });
    if (bvid) qs.set("bvid", bvid);
    const url = `https://api.bilibili.com/x/player/playurl?${qs.toString()}`;
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) return null;
    return res.json();
  }

  function fromYoutube() {
    let player = window.ytInitialPlayerResponse;
    if (!player && window.ytplayer && window.ytplayer.config && window.ytplayer.config.args) {
      const raw = window.ytplayer.config.args.player_response || window.ytplayer.config.args.raw_player_response;
      if (typeof raw === "string") {
        try {
          player = JSON.parse(raw);
        } catch {
          player = null;
        }
      } else if (raw && typeof raw === "object") {
        player = raw;
      }
    }
    if (!player || typeof player !== "object") return null;
    const sd = player.streamingData || {};
    const details = player.videoDetails || {};
    const title = details.title || document.title || "";
    const progressive = (sd.formats || []).filter((f) => isHttpUrl(f.url));
    const adaptive = (sd.adaptiveFormats || []).filter((f) => isHttpUrl(f.url));
    const videos = [...progressive, ...adaptive].filter((f) => {
      const mime = String(f.mimeType || f.mime_type || "");
      return mime.indexOf("video") >= 0 || (!mime && f.height);
    });
    const audios = adaptive.filter((f) => String(f.mimeType || f.mime_type || "").indexOf("audio") >= 0);
    const under720 = videos.filter((v) => !v.height || Number(v.height) <= 720);
    const pool = under720.length ? under720 : videos;
    pool.sort((a, b) => Number(b.height || 0) - Number(a.height || 0));
    audios.sort((a, b) => Number(b.bitrate || 0) - Number(a.bitrate || 0));
    if (!pool.length) return null;
    const video = pool[0];
    const needsAudio = String(video.mimeType || "").indexOf("video/") === 0 && !progressive.includes(video);
    return {
      videoUrl: video.url,
      audioUrl: needsAudio && audios[0] ? audios[0].url : null,
      height: video.height || null,
      title,
      pageUrl: location.href,
      source: "youtube",
    };
  }

  return (async () => {
    const title = biliTitle();
    let found = fromPlayinfo(window.__playinfo__, title);
    if (!found) {
      try {
        found = fromPlayinfo(await fetchBiliPlayurl(), title);
      } catch {
        found = null;
      }
    }
    if (!found) found = fromYoutube();
    if (!found) {
      const video = document.querySelector("video");
      const src = video && (video.currentSrc || video.src);
      if (isHttpUrl(src)) {
        found = {
          videoUrl: src,
          audioUrl: null,
          height: null,
          title: document.title || "",
          pageUrl: location.href,
          source: "video-element",
        };
      }
    }
    return found;
  })();
}

async function drillFetchMediaStream(url, requestId) {
  try {
    const res = await fetch(url, {
      credentials: "include",
      referrer: location.href,
      referrerPolicy: "no-referrer-when-downgrade",
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const total = Number(res.headers.get("content-length") || 0);
    if (!res.body) {
      const buf = await res.arrayBuffer();
      window.postMessage({ type: "DRILL_FETCH_PROGRESS", requestId, received: buf.byteLength, total: buf.byteLength }, "*");
      window.postMessage({ type: "DRILL_FETCH_OK", requestId, buf }, "*", [buf]);
      return;
    }
    const reader = res.body.getReader();
    const chunks = [];
    let received = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      received += value.byteLength;
      window.postMessage({ type: "DRILL_FETCH_PROGRESS", requestId, received, total }, "*");
    }
    const blob = new Blob(chunks);
    const buf = await blob.arrayBuffer();
    window.postMessage({ type: "DRILL_FETCH_OK", requestId, buf }, "*", [buf]);
  } catch (err) {
    window.postMessage(
      { type: "DRILL_FETCH_ERR", requestId, error: String(err && err.message ? err.message : err) },
      "*"
    );
  }
}
