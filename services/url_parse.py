from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_BV_RE = re.compile(r"/video/(BV[\w]+)", re.IGNORECASE)
_URL_IN_TEXT_RE = re.compile(
    r"https?://[^\s\u3000\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff【】「」]+",
    re.IGNORECASE,
)


def extract_url_from_text(text: str) -> str:
    """Pull the first http(s) URL from pasted share text (e.g. title + link)."""
    raw = (text or "").strip()
    if not raw:
        return ""
    match = _URL_IN_TEXT_RE.search(raw)
    if match:
        return match.group(0).rstrip(".,;)")
    return raw


def canonical_instructional_url(text: str) -> str:
    """
    Normalize instructional URLs for stable cache keys and yt-dlp.

    Bilibili multi-part videos must use ?p=N; tracking params are stripped.
    """
    url = extract_url_from_text(text)
    if not url:
        return ""

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if "bilibili.com" not in host and "b23.tv" not in host:
        return url

    if "b23.tv" in host:
        # Short links: leave resolution to yt-dlp; still strip junk from paste.
        return url

    match = _BV_RE.search(parsed.path or "")
    if not match:
        return url

    bvid = match.group(1).upper()
    query = parse_qs(parsed.query, keep_blank_values=False)
    p_vals = query.get("p") or query.get("page")
    if p_vals:
        try:
            p_num = int(p_vals[0])
        except (TypeError, ValueError):
            p_num = 1
        if p_num < 1:
            p_num = 1
        return f"https://www.bilibili.com/video/{bvid}?p={p_num}"

    # Multi-part series without ?p= — keep BV-only URL (download layer will reject playlists).
    return f"https://www.bilibili.com/video/{bvid}"


def is_bilibili_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "bilibili.com" in host or "b23.tv" in host
