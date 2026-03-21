from services.cache import (
    cached_video_path,
    delete_cached_video,
    get_video_title,
    is_valid_cache_file,
    list_cached_videos,
    load_url_registry,
    save_url_registry_entry,
    save_video_title,
    url_cache_key,
)


def test_url_cache_key_stable() -> None:
    a = url_cache_key("https://example.com/watch?v=1")
    b = url_cache_key("https://example.com/watch?v=1")
    assert a == b
    assert len(a) == 16


def test_cached_video_path_suffix(tmp_path) -> None:
    p = cached_video_path(tmp_path, "https://x.test/v")
    assert p.parent == tmp_path
    assert p.suffix == ".mp4"


def test_is_valid_cache_file(tmp_path) -> None:
    empty = tmp_path / "a.mp4"
    empty.write_text("")
    assert is_valid_cache_file(empty) is False
    nonempty = tmp_path / "b.mp4"
    nonempty.write_bytes(b"x")
    assert is_valid_cache_file(nonempty) is True


def test_save_and_load_url_registry(tmp_path) -> None:
    url = "https://example.com/watch?v=abc"
    save_url_registry_entry(tmp_path, url)
    reg = load_url_registry(tmp_path)
    key = url_cache_key(url)
    assert reg[key] == url


def test_list_cached_videos_orders_and_skips_empty(tmp_path) -> None:
    k = url_cache_key("https://x.test/v")
    good = tmp_path / f"{k}.mp4"
    good.write_bytes(b"ok")
    empty = tmp_path / "empty.mp4"
    empty.write_text("")
    save_url_registry_entry(tmp_path, "https://x.test/v")
    rows = list_cached_videos(tmp_path)
    assert len(rows) == 1
    assert rows[0]["cache_key"] == k
    assert rows[0]["url"] == "https://x.test/v"


def test_delete_cached_video_removes_file_and_registry(tmp_path) -> None:
    url = "https://example.com/watch?v=del"
    k = url_cache_key(url)
    mp4 = tmp_path / f"{k}.mp4"
    mp4.write_bytes(b"x")
    save_url_registry_entry(tmp_path, url)
    save_video_title(tmp_path, url, "My Title")
    assert get_video_title(tmp_path, url) == "My Title"
    assert load_url_registry(tmp_path).get(k) == url
    assert delete_cached_video(tmp_path, k) is True
    assert not mp4.exists()
    assert k not in load_url_registry(tmp_path)
    assert get_video_title(tmp_path, url) == ""


def test_delete_cached_video_invalid_key(tmp_path) -> None:
    assert delete_cached_video(tmp_path, "../evil") is False
    assert delete_cached_video(tmp_path, "nothexnothexnot") is False
