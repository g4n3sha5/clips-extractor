import pytest

from services.clip import (
    encode_options_for_sidecar,
    format_clip_description,
    parse_timestamp,
    sanitize_filename_stem,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0", 0.0),
        ("30", 30.0),
        ("0:30", 30.0),
        ("1:05", 65.0),
        ("1:01:05", 3665.0),
    ],
)
def test_parse_timestamp(text: str, expected: float) -> None:
    assert parse_timestamp(text) == pytest.approx(expected)


def test_sanitize_filename_stem() -> None:
    assert sanitize_filename_stem("foo bar") == "foo_bar"
    assert sanitize_filename_stem("clip-01") == "clip-01"


def test_encode_options_for_sidecar() -> None:
    m = encode_options_for_sidecar(crf=26, preset="medium", audio_kbps=96)
    assert m["video"] == "libx264"
    assert m["crf"] == 26
    assert m["audio_kbps"] == 96


def test_format_clip_description() -> None:
    assert format_clip_description(
        video_title="Arm Bar Basics",
        start="0:30",
        end="1:05",
        fallback_url="https://example.com/v",
    ) == "Arm Bar Basics\n0:30 – 1:05"
    assert format_clip_description(
        video_title="",
        start="0",
        end="1",
        fallback_url="https://example.com/watch",
    ) == "https://example.com/watch\n0 – 1"

