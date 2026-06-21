from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from PIL import ExifTags, Image

BayerPattern = Literal["RGGB", "BGGR", "GBRG", "GRBG"]
GreenMode = Literal["GXXG", "XGGX"]


@dataclass(frozen=True)
class CameraCfaSpec:
    make: str
    model: str
    bayer_pattern: BayerPattern
    source: str
    source_url: str


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\x00", " ").strip()
    text = "".join(ch for ch in text if ch.isprintable())
    return re.sub(r"\s+", " ", text).strip()


def normalize_camera_key(*parts: str) -> str:
    joined = " ".join(part for part in parts if part)
    joined = joined.upper()
    joined = re.sub(r"[^A-Z0-9]+", " ", joined)
    joined = re.sub(r"\b(CORPORATION|CORP|COMPANY|CO LTD|COMPUTER|IMAGING|DIGITAL|CAMERA)\b", " ", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined


def bayer_to_green_mode(pattern: str | None) -> GreenMode | None:
    if pattern in {"RGGB", "BGGR"}:
        return "XGGX"
    if pattern in {"GBRG", "GRBG"}:
        return "GXXG"
    return None


# Curated references are intentionally conservative. Unknown cameras fall back to
# image-based CFA mode estimation and report low/medium/high confidence.
KNOWN_CAMERA_CFA: dict[str, CameraCfaSpec] = {
    normalize_camera_key("NIKON CORPORATION", "NIKON D200"): CameraCfaSpec(
        make="NIKON CORPORATION",
        model="NIKON D200",
        bayer_pattern="RGGB",
        source="Choi et al. 2013 Table 1; Siegen multi-illuminant dataset paper",
        source_url="https://doi.org/10.1016/j.forsciint.2012.12.014",
    ),
    normalize_camera_key("NIKON CORPORATION", "NIKON D70"): CameraCfaSpec(
        make="NIKON CORPORATION",
        model="NIKON D70",
        bayer_pattern="BGGR",
        source="Choi et al. 2013 Table 1; Choi et al. 2011 CFA pattern identification",
        source_url="https://dl.acm.org/doi/10.1145/2037252.2037258",
    ),
    normalize_camera_key("NIKON CORPORATION", "NIKON D70s"): CameraCfaSpec(
        make="NIKON CORPORATION",
        model="NIKON D70s",
        bayer_pattern="BGGR",
        source="Choi et al. 2013 Table 1; Choi et al. 2011 CFA pattern identification",
        source_url="https://dl.acm.org/doi/10.1145/2037252.2037258",
    ),
    normalize_camera_key("NIKON CORPORATION", "NIKON D90"): CameraCfaSpec(
        make="NIKON CORPORATION",
        model="NIKON D90",
        bayer_pattern="GBRG",
        source="Choi et al. 2013 Table 1",
        source_url="https://doi.org/10.1016/j.forsciint.2012.12.014",
    ),
    normalize_camera_key("Canon", "Canon EOS 500D"): CameraCfaSpec(
        make="Canon",
        model="Canon EOS 500D",
        bayer_pattern="RGGB",
        source="Choi et al. 2013 Table 1",
        source_url="https://doi.org/10.1016/j.forsciint.2012.12.014",
    ),
    normalize_camera_key("SONY", "DSLR-A380"): CameraCfaSpec(
        make="SONY",
        model="DSLR-A380",
        bayer_pattern="RGGB",
        source="Choi et al. 2013 Table 1",
        source_url="https://doi.org/10.1016/j.forsciint.2012.12.014",
    ),
    normalize_camera_key("OLYMPUS IMAGING CORP.", "E-420"): CameraCfaSpec(
        make="OLYMPUS IMAGING CORP.",
        model="E-420",
        bayer_pattern="RGGB",
        source="Choi et al. 2013 Table 1",
        source_url="https://doi.org/10.1016/j.forsciint.2012.12.014",
    ),
}


def extract_exif_camera(data: bytes) -> dict[str, str]:
    image = Image.open(BytesIO(data))
    exif = image.getexif()
    named = {ExifTags.TAGS.get(tag, tag): value for tag, value in exif.items()}
    make = _clean_text(named.get("Make"))
    model = _clean_text(named.get("Model"))
    software = _clean_text(named.get("Software"))
    return {
        "make": make,
        "model": model,
        "software": software,
        "normalized_key": normalize_camera_key(make, model),
    }


def lookup_camera_cfa(exif_camera: dict[str, str]) -> dict[str, object]:
    key = exif_camera.get("normalized_key", "")
    spec = KNOWN_CAMERA_CFA.get(key)
    if spec is None:
        # Some EXIF model strings already include the make, so also try model-only.
        model_key = normalize_camera_key(exif_camera.get("model", ""))
        spec = KNOWN_CAMERA_CFA.get(model_key)
    if spec is None:
        return {
            **exif_camera,
            "bayer_pattern": None,
            "green_mode": None,
            "source": "Not found in curated CFA spec table; using image-based auto estimate",
            "source_url": None,
            "lookup_status": "unknown",
        }
    return {
        **exif_camera,
        "bayer_pattern": spec.bayer_pattern,
        "green_mode": bayer_to_green_mode(spec.bayer_pattern),
        "source": spec.source,
        "source_url": spec.source_url,
        "lookup_status": "known",
    }

