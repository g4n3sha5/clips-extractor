from pathlib import Path

from services.bilibili_cookies import _find_firefox_cookie_db, export_firefox_bilibili_cookies


def test_export_firefox_writes_cookie_file_when_profile_exists(tmp_path) -> None:
    if _find_firefox_cookie_db() is None:
        return
    dest = tmp_path / "bilibili_cookies.txt"
    assert export_firefox_bilibili_cookies(dest) is True
    text = dest.read_text(encoding="utf-8")
    assert "bilibili" in text.lower()
