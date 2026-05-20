from config import Settings
from services.download import _bilibili_download_attempts


def test_bilibili_attempts_anonymous_by_default(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.download.load_settings",
        lambda: Settings(bilibili_use_login=False),
    )
    attempts = _bilibili_download_attempts()
    assert attempts[0] == (None, None)
    assert all(a[1] is None for a in attempts)


def test_bilibili_attempts_with_login_only_configured_browser(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.download.load_settings",
        lambda: Settings(bilibili_use_login=True, bilibili_cookies_browser="firefox"),
    )
    monkeypatch.setattr("services.download.resolve_bilibili_cookie_file", lambda **_: None)
    attempts = _bilibili_download_attempts()
    assert attempts[0] == (None, None)
    assert (None, "firefox") in attempts
    assert (None, "safari") not in attempts
