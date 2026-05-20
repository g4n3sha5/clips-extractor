(function () {
  function pickMimeType() {
    const candidates = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm;codecs=vp9",
      "video/webm",
      "video/mp4",
    ];
    for (const t of candidates) {
      if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) {
        return t;
      }
    }
    return "";
  }

  function captureVideoStream(video) {
    if (typeof video.captureStream === "function") return video.captureStream();
    if (typeof video.mozCaptureStream === "function") return video.mozCaptureStream();
    throw new Error("This browser cannot capture video from the player.");
  }

  function buildCombinedStream(video) {
    const videoStream = captureVideoStream(video);
    const tracks = [...videoStream.getVideoTracks()];

    let audioCtx = null;
    try {
      audioCtx = new AudioContext();
      const source = audioCtx.createMediaElementSource(video);
      const dest = audioCtx.createMediaStreamDestination();
      source.connect(dest);
      source.connect(audioCtx.destination);
      for (const t of dest.stream.getAudioTracks()) {
        tracks.push(t);
      }
    } catch (err) {
      console.warn("Drill Clips: Web Audio capture failed, trying video stream audio", err);
      for (const t of videoStream.getAudioTracks()) {
        tracks.push(t);
      }
    }

    const combined = new MediaStream(tracks);
    return { combined, audioCtx };
  }

  function waitForEvent(target, event, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      let timer = null;
      const onOk = () => {
        cleanup();
        resolve();
      };
      const onErr = () => {
        cleanup();
        reject(new Error(`Event ${event} failed`));
      };
      const onTimeout = () => {
        cleanup();
        reject(new Error(`Timed out waiting for ${event}`));
      };
      const cleanup = () => {
        if (timer) clearTimeout(timer);
        target.removeEventListener(event, onOk);
        target.removeEventListener("error", onErr);
      };
      target.addEventListener(event, onOk, { once: true });
      target.addEventListener("error", onErr, { once: true });
      timer = setTimeout(onTimeout, timeoutMs);
    });
  }

  async function recordSegment(video, startSec, endSec, onProgress, signal) {
    if (!(endSec > startSec)) {
      throw new Error("End must be after start");
    }
    const duration = endSec - startSec;
    if (duration > 600) {
      throw new Error("Segment longer than 10 minutes — use a shorter range");
    }
    if (signal?.aborted) {
      const e = new Error("Cancelled");
      e.name = "AbortError";
      throw e;
    }

    const { combined, audioCtx } = buildCombinedStream(video);
    if (combined.getAudioTracks().length === 0) {
      throw new Error(
        "No audio track captured. Click the video once, then try again. On Mac, Web Audio capture is required for sound."
      );
    }

    if (audioCtx && audioCtx.state === "suspended") {
      await audioCtx.resume();
    }

    const mimeType = pickMimeType();
    const recorder = mimeType
      ? new MediaRecorder(combined, { mimeType })
      : new MediaRecorder(combined);

    const chunks = [];
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size) chunks.push(e.data);
    };

    const wasPaused = video.paused;
    const prevTime = video.currentTime;
    const prevRate = video.playbackRate;

    try {
      video.pause();
      video.currentTime = startSec;
      await waitForEvent(video, "seeked");

      const recordDone = new Promise((resolve, reject) => {
        recorder.onstop = () => resolve();
        recorder.onerror = () => reject(new Error("MediaRecorder error"));
      });

      recorder.start(250);
      video.playbackRate = 1;
      await video.play();

      let cancelled = false;
      await new Promise((resolve, reject) => {
        const stopAt = endSec;
        const cleanup = () => {
          video.removeEventListener("timeupdate", onTime);
          video.removeEventListener("pause", onVideoPause);
          video.removeEventListener("play", onVideoPlay);
          video.removeEventListener("ended", onEnded);
          if (signal) signal.removeEventListener("abort", onAbort);
        };
        const finishOk = () => {
          cleanup();
          video.pause();
          if (recorder.state !== "inactive") recorder.stop();
          resolve();
        };
        const onAbort = () => {
          cancelled = true;
          cleanup();
          video.pause();
          if (recorder.state !== "inactive") recorder.stop();
          resolve();
        };
        const report = (paused) => {
          if (typeof onProgress === "function") {
            onProgress({ currentTime: video.currentTime, paused });
          }
        };
        const onTime = () => {
          report(false);
          if (video.currentTime >= stopAt - 0.05) finishOk();
        };
        const onVideoPause = () => {
          if (cancelled) return;
          if (recorder.state === "recording") {
            try {
              recorder.pause();
            } catch {
              /* ignore */
            }
          }
          report(true);
        };
        const onVideoPlay = () => {
          if (cancelled) return;
          if (recorder.state === "paused") {
            try {
              recorder.resume();
            } catch {
              /* ignore */
            }
          }
          report(false);
        };
        const onEnded = () => finishOk();

        video.addEventListener("timeupdate", onTime);
        video.addEventListener("pause", onVideoPause);
        video.addEventListener("play", onVideoPlay);
        video.addEventListener("ended", onEnded);
        recorder.onerror = () => {
          cleanup();
          reject(new Error("Recording failed"));
        };
        if (signal) signal.addEventListener("abort", onAbort, { once: true });
      });

      await recordDone;

      if (cancelled) {
        const e = new Error("Cancelled");
        e.name = "AbortError";
        throw e;
      }

      const blobType = mimeType || "video/webm";
      const blob = new Blob(chunks, { type: blobType });
      if (!blob.size) throw new Error("Recording produced an empty file");
      return blob;
    } finally {
      video.playbackRate = prevRate;
      if (wasPaused) {
        video.pause();
        video.currentTime = prevTime;
      }
      if (audioCtx) {
        try {
          await audioCtx.close();
        } catch {
          /* ignore */
        }
      }
      for (const t of combined.getTracks()) {
        try {
          t.stop();
        } catch {
          /* ignore */
        }
      }
    }
  }

  window.DrillRecording = { recordSegment, pickMimeType };
})();
