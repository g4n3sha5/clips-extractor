from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from config import PROJECT_ROOT

DEFAULT_COOKIE_PATH = PROJECT_ROOT / "bilibili_cookies.txt"


def _firefox_profiles_dir() -> Path:
    return Path.home() / "Library/Application Support/Firefox/Profiles"


def _find_firefox_cookie_db() -> Optional[Path]:
    root = _firefox_profiles_dir()
    if not root.is_dir():
        return None
    candidates: list[Path] = []
    for name in os.listdir(root):
        db = root / name / "cookies.sqlite"
        if db.is_file():
            candidates.append(db)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def export_firefox_bilibili_cookies(dest: Path) -> bool:
    """
    Write Netscape-format cookies for all *.bilibili* hosts from Firefox.
    Works around yt-dlp's occasional failure with Firefox cookie DB v17.
    """
    db_path = _find_firefox_cookie_db()
    if not db_path:
        return False

    tmp = Path(tempfile.mkdtemp()) / "cookies.sqlite"
    try:
        shutil.copy2(db_path, tmp)
        con = sqlite3.connect(tmp)
        rows = con.execute(
            """
            SELECT host, path, isSecure, expiry, name, value
            FROM moz_cookies
            WHERE host LIKE '%bilibili%' AND value IS NOT NULL AND value != ''
            """
        ).fetchall()
        con.close()
    except (OSError, sqlite3.Error) as e:
        logger.warning("Firefox cookie export failed: %s", e)
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except OSError:
            pass

    if not rows:
        return False

    lines = ["# Netscape HTTP Cookie File", "# Exported from Firefox for Drill Clip Extractor"]
    now = int(time.time())
    for host, path, is_secure, expiry, name, value in rows:
        domain = host if host.startswith(".") else f".{host}"
        secure = "TRUE" if is_secure else "FALSE"
        exp = int(expiry) if expiry and int(expiry) > now else now + 86400 * 365
        lines.append(f"{domain}\tTRUE\t{path or '/'}\t{secure}\t{exp}\t{name}\t{value}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def resolve_bilibili_cookie_file(*, allow_auto_export: bool = True) -> Optional[Path]:
    """Cookie file for Bilibili when login is enabled (or an explicit path is configured)."""
    from config import load_settings

    settings = load_settings()
    if settings.bilibili_cookies_file and settings.bilibili_cookies_file.is_file():
        return settings.bilibili_cookies_file

    if not allow_auto_export or not settings.bilibili_use_login:
        return None

    if DEFAULT_COOKIE_PATH.is_file():
        age = time.time() - DEFAULT_COOKIE_PATH.stat().st_mtime
        if age < 3600:
            return DEFAULT_COOKIE_PATH

    if export_firefox_bilibili_cookies(DEFAULT_COOKIE_PATH):
        return DEFAULT_COOKIE_PATH

    if DEFAULT_COOKIE_PATH.is_file():
        return DEFAULT_COOKIE_PATH

    return None
