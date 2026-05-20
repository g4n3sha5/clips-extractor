from services.download import _is_cookie_access_error


def test_cookie_permission_errors_are_detected() -> None:
    """macOS may block browser cookie reads; those failures should not abort other attempts."""
    assert _is_cookie_access_error("ERROR: [Errno 1] Operation not permitted") is True
    assert _is_cookie_access_error("could not find chrome cookies database") is True
    assert _is_cookie_access_error("Cookies.binarycookies") is True
