from services.url_parse import canonical_instructional_url, extract_url_from_text


def test_extract_url_from_chinese_share_text() -> None:
    text = (
        "【ARMBAR MASTERCLASS】 "
        "https://www.bilibili.com/video/BV1Z3BEB3E6w/?p=10&share_source=copy_web"
    )
    assert extract_url_from_text(text).startswith("https://www.bilibili.com/video/BV1Z3BEB3E6w")


def test_canonical_bilibili_preserves_part() -> None:
    raw = "https://www.bilibili.com/video/BV1Z3BEB3E6w/?p=10&share_source=copy_web&vd_source=abc"
    assert canonical_instructional_url(raw) == "https://www.bilibili.com/video/BV1Z3BEB3E6W?p=10"


def test_canonical_bilibili_same_key_for_share_variants() -> None:
    from services.cache import url_cache_key

    a = url_cache_key("https://www.bilibili.com/video/BV1Z3BEB3E6w/?p=10&share_source=x")
    b = url_cache_key("https://www.bilibili.com/video/BV1Z3BEB3E6w?p=10")
    assert a == b


def test_canonical_bilibili_videopod_url_with_p10() -> None:
    raw = (
        "https://www.bilibili.com/video/BV1Z3BEB3E6w"
        "?spm_id_from=333.788.videopod.episodes"
        "&vd_source=fa99b1ed46e6991fb3c313fb0a929e50&p=10"
    )
    assert canonical_instructional_url(raw) == "https://www.bilibili.com/video/BV1Z3BEB3E6W?p=10"


def test_canonical_bilibili_without_part_strips_tracking_only() -> None:
    raw = "https://www.bilibili.com/video/BV1Z3BEB3E6w/?share_source=copy_web"
    assert canonical_instructional_url(raw) == "https://www.bilibili.com/video/BV1Z3BEB3E6W"
