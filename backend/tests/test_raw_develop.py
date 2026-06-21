from app.core.raw_develop import raw_pattern_to_bayer


def test_raw_pattern_to_bayer_maps_rawpy_indices() -> None:
    assert raw_pattern_to_bayer([[0, 1], [3, 2]], b"RGBG") == "RGGB"
    assert raw_pattern_to_bayer([[1, 0], [2, 3]], b"RGBG") == "GRBG"
    assert raw_pattern_to_bayer([[2, 3], [1, 0]], b"RGBG") == "BGGR"
    assert raw_pattern_to_bayer([[3, 2], [0, 1]], b"RGBG") == "GBRG"


def test_raw_pattern_to_bayer_rejects_non_bayer_pattern() -> None:
    assert raw_pattern_to_bayer([[0, 0], [1, 2]], b"RGBG") is None
