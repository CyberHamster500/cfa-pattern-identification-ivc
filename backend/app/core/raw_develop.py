from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import numpy as np

from app.core.camera_metadata import BayerPattern, GreenMode, bayer_to_green_mode


def raw_pattern_to_bayer(raw_pattern: Any, color_desc: bytes | str) -> BayerPattern | None:
    if raw_pattern is None:
        return None
    desc = color_desc.decode("ascii", errors="ignore") if isinstance(color_desc, bytes) else str(color_desc)
    try:
        pattern = np.asarray(raw_pattern)
        if pattern.shape[0] < 2 or pattern.shape[1] < 2:
            return None
        chars = []
        for row in range(2):
            for col in range(2):
                idx = int(pattern[row, col])
                chars.append(desc[idx] if 0 <= idx < len(desc) else "?")
        bayer = "".join("G" if ch == "G" else ch for ch in chars)
    except Exception:
        return None
    return bayer if bayer in {"RGGB", "BGGR", "GBRG", "GRBG"} else None  # type: ignore[return-value]


def develop_raw_with_rawpy(path: Path, max_side: int = 768) -> tuple[np.ndarray, dict[str, object]]:
    try:
        import rawpy
    except ImportError as exc:  # pragma: no cover - depends on optional wheel availability.
        raise RuntimeError("rawpy is required for RAW support. Install backend requirements first.") from exc

    with rawpy.imread(str(path)) as raw:
        bayer_pattern = raw_pattern_to_bayer(raw.raw_pattern, raw.color_desc)
        green_mode: GreenMode | None = bayer_to_green_mode(bayer_pattern)
        metadata = {
            "backend": "rawpy",
            "raw_path": str(path),
            "raw_type": str(raw.raw_type),
            "raw_size": [int(raw.raw_image_visible.shape[1]), int(raw.raw_image_visible.shape[0])],
            "rgb_size_before_resize": [int(raw.sizes.width), int(raw.sizes.height)],
            "raw_pattern": np.asarray(raw.raw_pattern).astype(int).tolist(),
            "color_desc": raw.color_desc.decode("ascii", errors="ignore"),
            "bayer_pattern": bayer_pattern,
            "green_mode": green_mode,
            "black_level_per_channel": [int(value) for value in raw.black_level_per_channel],
            "white_level": int(raw.white_level),
        }
        rgb = raw.postprocess(output_bps=8, no_auto_bright=True, use_camera_wb=True)

    if max(rgb.shape[:2]) > max_side:
        from PIL import Image

        image = Image.fromarray(rgb, "RGB")
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        rgb = np.asarray(image, dtype=np.uint8)
    metadata["rgb_size"] = [int(rgb.shape[1]), int(rgb.shape[0])]
    return rgb, metadata


def develop_raw_bytes_with_rawpy(data: bytes, suffix: str = ".raw", max_side: int = 768) -> tuple[np.ndarray, dict[str, object]]:
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        tmp_path = Path(tmp.name)
    try:
        return develop_raw_with_rawpy(tmp_path, max_side=max_side)
    finally:
        tmp_path.unlink(missing_ok=True)


def is_supported_raw_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in {".nef", ".cr2", ".cr3", ".arw", ".dng", ".orf", ".rw2", ".raf", ".pef", ".sr2"}
