import numpy as np

from app.core.cfa_ivc import identify_cfa_pattern_payload


def test_identify_cfa_pattern_payload_has_bayer_fields() -> None:
    rgb = np.zeros((20, 20, 3), dtype=np.uint8)
    rows, cols = np.indices((20, 20))
    rgb[..., 0] = np.where((rows % 2 == 0) & (cols % 2 == 0), 240, 20)
    rgb[..., 1] = np.where((rows + cols) % 2 == 1, 180, 40)
    rgb[..., 2] = np.where((rows % 2 == 1) & (cols % 2 == 1), 240, 20)

    payload = identify_cfa_pattern_payload(rgb)

    assert payload["bayer_pattern"] in {"RGGB", "BGGR", "GBRG", "GRBG"}
    assert payload["green_mode"] in {"GXXG", "XGGX"}
    assert 0.0 <= payload["confidence"] <= 1.0
    assert set(payload["scores"]) == {"RGGB", "BGGR", "GBRG", "GRBG"}
