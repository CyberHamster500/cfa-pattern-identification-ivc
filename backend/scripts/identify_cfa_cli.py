from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.camera_metadata import extract_exif_camera, lookup_camera_cfa
from app.core.cfa_ivc import identify_cfa_pattern_payload
from app.core.hue import load_rgb_image
from app.core.raw_develop import develop_raw_with_rawpy, is_supported_raw_filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Identify a digital camera Bayer CFA pattern using IVC.")
    parser.add_argument("image", type=Path, help="PNG, JPEG, or RAW image path.")
    parser.add_argument("--max-side", type=int, default=768, help="Resize longest side before analysis. Default: 768.")
    parser.add_argument("--json", action="store_true", help="Print full JSON output.")
    return parser.parse_args()


def _safe_camera_lookup(data: bytes) -> dict[str, object]:
    try:
        return lookup_camera_cfa(extract_exif_camera(data))
    except Exception:
        return {
            "make": "",
            "model": "",
            "software": "",
            "normalized_key": "",
            "bayer_pattern": None,
            "green_mode": None,
            "source": "EXIF camera metadata could not be read",
            "source_url": None,
            "lookup_status": "unknown",
        }


def _summary(payload: dict[str, object], image_path: Path) -> str:
    camera = payload["camera"]
    ivc = payload["ivc_prediction"]
    raw = payload.get("raw_metadata") or {}
    camera_name = " ".join(part for part in [camera.get("make"), camera.get("model")] if part) or "unknown"  # type: ignore[union-attr]
    rows = [
        ("file", str(image_path)),
        ("input_kind", str(payload["input_kind"])),
        ("camera", camera_name),
        ("exif_lookup_status", str(camera["lookup_status"])),  # type: ignore[index]
        ("exif_bayer_pattern", str(camera["bayer_pattern"] or "unknown")),  # type: ignore[index]
        ("raw_bayer_pattern", str(raw.get("bayer_pattern") or "n/a")),  # type: ignore[union-attr]
        ("ivc_bayer_pattern", str(ivc["bayer_pattern"])),  # type: ignore[index]
        ("ivc_green_mode", str(ivc["green_mode"])),  # type: ignore[index]
        ("ivc_confidence", f"{float(ivc['confidence']) * 100:.2f}%"),  # type: ignore[index]
        ("raw_ivc_conflict", str(payload["raw_ivc_conflict"])),
        ("exif_ivc_conflict", str(payload["exif_ivc_conflict"])),
        ("image_size", f"{payload['width']} x {payload['height']}"),
    ]
    width = max(len(key) for key, _ in rows)
    return "\n".join(f"{key:<{width}} : {value}" for key, value in rows)


def main() -> int:
    args = parse_args()
    if not args.image.exists():
        print(f"image not found: {args.image}", file=sys.stderr)
        return 2

    data = args.image.read_bytes()
    camera = _safe_camera_lookup(data)
    raw_metadata = None
    input_kind = "raw" if is_supported_raw_filename(args.image.name) else "rgb"
    if input_kind == "raw":
        rgb, raw_metadata = develop_raw_with_rawpy(args.image, max_side=args.max_side)
    else:
        rgb = load_rgb_image(data, max_side=args.max_side)

    ivc = identify_cfa_pattern_payload(rgb)
    payload = {
        "input_kind": input_kind,
        "width": int(rgb.shape[1]),
        "height": int(rgb.shape[0]),
        "camera": camera,
        "raw_metadata": raw_metadata,
        "ivc_prediction": ivc,
        "raw_ivc_conflict": bool(raw_metadata and raw_metadata.get("bayer_pattern") and raw_metadata.get("bayer_pattern") != ivc["bayer_pattern"]),
        "exif_ivc_conflict": bool(camera.get("bayer_pattern") and camera.get("bayer_pattern") != ivc["bayer_pattern"]),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_summary(payload, args.image))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
