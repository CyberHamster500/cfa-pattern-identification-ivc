from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw

from app.core.camera_metadata import GreenMode

CfaGreenMode = Literal["GXXG", "XGGX"]
CfaGreenModeInput = Literal["AUTO", "GXXG", "XGGX"]


@dataclass(frozen=True)
class AnalysisOptions:
    ds: int = 5
    block_size: int = 32
    cfa_green_mode: CfaGreenModeInput = "AUTO"
    preferred_cfa_green_mode: GreenMode | None = None


def load_rgb_image(data: bytes, max_side: int = 768) -> np.ndarray:
    image = Image.open(BytesIO(data)).convert("RGB")
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.uint8)


def image_to_data_url(image: Image.Image) -> str:
    import base64

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def angular_error(expected: float, actual: float) -> float:
    diff = abs((expected - actual + 180.0) % 360.0 - 180.0)
    return float(diff)


def rgb_to_hue_degrees(rgb: np.ndarray) -> np.ndarray:
    arr = rgb.astype(np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros(r.shape, dtype=np.float32)

    maxc = np.maximum.reduce([r, g, b])
    minc = np.minimum.reduce([r, g, b])
    chroma = maxc - minc
    mask = chroma > 1e-6

    red = mask & (maxc == r)
    green = mask & (maxc == g)
    blue = mask & (maxc == b)

    hue[red] = (60.0 * ((g[red] - b[red]) / chroma[red])) % 360.0
    hue[green] = 60.0 * (((b[green] - r[green]) / chroma[green]) + 2.0)
    hue[blue] = 60.0 * (((r[blue] - g[blue]) / chroma[blue]) + 4.0)
    return hue


def shift_hue_hsi(rgb: np.ndarray, degrees: float) -> np.ndarray:
    src = rgb.astype(np.float32) / 255.0
    r, g, b = src[..., 0], src[..., 1], src[..., 2]
    intensity = (r + g + b) / 3.0
    min_rgb = np.minimum.reduce([r, g, b])
    saturation = np.zeros_like(intensity)
    nonzero_i = intensity > 1e-6
    saturation[nonzero_i] = 1.0 - (min_rgb[nonzero_i] / intensity[nonzero_i])
    saturation = np.clip(saturation, 0.0, 1.0)

    hue = (rgb_to_hue_degrees(rgb) + degrees) % 360.0
    out = np.zeros_like(src)

    sectors = [
        (hue < 120.0, 0),
        ((hue >= 120.0) & (hue < 240.0), 120),
        (hue >= 240.0, 240),
    ]
    for mask, offset in sectors:
        if not np.any(mask):
            continue
        h = np.deg2rad(hue[mask] - offset)
        i = intensity[mask]
        s = saturation[mask]
        cos_den = np.cos(np.deg2rad(60.0) - h)
        cos_den = np.where(np.abs(cos_den) < 1e-6, 1e-6, cos_den)
        first = i * (1.0 + (s * np.cos(h) / cos_den))
        third = i * (1.0 - s)
        second = (3.0 * i) - (first + third)

        if offset == 0:
            out[..., 0][mask], out[..., 1][mask], out[..., 2][mask] = first, second, third
        elif offset == 120:
            out[..., 0][mask], out[..., 1][mask], out[..., 2][mask] = third, first, second
        else:
            out[..., 0][mask], out[..., 1][mask], out[..., 2][mask] = second, third, first

    return np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8)


def aivc_counts(channel: np.ndarray) -> np.ndarray:
    values = channel.astype(np.float32)
    counts = np.zeros((2, 2), dtype=np.int64)
    if values.shape[0] < 3 or values.shape[1] < 3:
        return counts

    center = values[1:-1, 1:-1]
    top = values[:-2, 1:-1]
    bottom = values[2:, 1:-1]
    left = values[1:-1, :-2]
    right = values[1:-1, 2:]
    min_cross = np.minimum.reduce([top, bottom, left, right])
    max_cross = np.maximum.reduce([top, bottom, left, right])
    not_intermediate = (center < min_cross) | (center > max_cross)

    rows, cols = np.indices(center.shape)
    rows += 1
    cols += 1
    for row_parity in (0, 1):
        for col_parity in (0, 1):
            mask = not_intermediate & ((rows % 2) == row_parity) & ((cols % 2) == col_parity)
            counts[row_parity, col_parity] = int(mask.sum())
    return counts


def channel_ratios(rgb: np.ndarray) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for name, idx in (("R", 0), ("G", 1), ("B", 2)):
        counts = aivc_counts(rgb[..., idx])
        numerator = float(counts[0, 0] + counts[1, 1])
        denominator = float(counts[0, 1] + counts[1, 0])
        ratios[name] = numerator / max(denominator, 1.0)
    return ratios


def estimate_cfa_green_mode(rgb: np.ndarray) -> dict[str, float | str | dict[str, list[list[int]]]]:
    channel_names = (("R", 0), ("G", 1), ("B", 2))
    candidates = []
    counts_by_channel: dict[str, list[list[int]]] = {}
    for name, idx in channel_names:
        counts = aivc_counts(rgb[..., idx])
        counts_by_channel[name] = counts.astype(int).tolist()
        diagonal = float(counts[0, 0] + counts[1, 1])
        anti_diagonal = float(counts[0, 1] + counts[1, 0])
        total = max(diagonal + anti_diagonal, 1.0)
        confidence = abs(diagonal - anti_diagonal) / total
        candidates.append(
            {
                "mode": "GXXG" if diagonal >= anti_diagonal else "XGGX",
                "confidence": confidence,
                "source_channel": name,
                "diagonal_count": diagonal,
                "anti_diagonal_count": anti_diagonal,
            }
        )
    selected = max(candidates, key=lambda item: float(item["confidence"]))
    confidence = float(selected["confidence"])
    if confidence >= 0.08:
        reliability = "high"
    elif confidence >= 0.03:
        reliability = "medium"
    else:
        reliability = "low"
    return {
        "mode": str(selected["mode"]),
        "confidence": confidence,
        "reliability": reliability,
        "source_channel": str(selected["source_channel"]),
        "diagonal_count": float(selected["diagonal_count"]),
        "anti_diagonal_count": float(selected["anti_diagonal_count"]),
        "counts_by_channel": counts_by_channel,
    }


def ratio_curves(rgb: np.ndarray, ds: int) -> list[dict[str, float]]:
    step = max(1, int(ds))
    curves: list[dict[str, float]] = []
    for shift in range(0, 360, step):
        shifted = shift_hue_hsi(rgb, shift)
        ratios = channel_ratios(shifted)
        curves.append({"shift": float(shift), **ratios})
    return curves


def estimate_from_curves(curves: list[dict[str, float]], mode: CfaGreenMode) -> dict[str, float | str]:
    if not curves:
        return {"estimated_hue": 0.0, "hm": 0.0, "criterion": "empty"}
    if mode == "GXXG":
        selected = max(curves, key=lambda item: item["G"])
        criterion = "max Gr"
    else:
        selected = min(curves, key=lambda item: item["G"])
        criterion = "min Gr"
    hm = float(selected["shift"])
    estimated = (360.0 - hm) % 360.0
    return {"estimated_hue": estimated, "hm": hm, "criterion": criterion}


def analyze_image(rgb: np.ndarray, options: AnalysisOptions) -> dict:
    cfa_prediction = estimate_cfa_green_mode(rgb)
    resolved_mode = (
        options.preferred_cfa_green_mode
        if options.cfa_green_mode == "AUTO" and options.preferred_cfa_green_mode
        else str(cfa_prediction["mode"]) if options.cfa_green_mode == "AUTO" else options.cfa_green_mode
    )
    curves = ratio_curves(rgb, options.ds)
    estimate = estimate_from_curves(curves, resolved_mode)  # type: ignore[arg-type]
    heatmap = block_heatmap(rgb, options, resolved_mode)  # type: ignore[arg-type]
    return {
        "width": int(rgb.shape[1]),
        "height": int(rgb.shape[0]),
        "options": {
            "ds": int(options.ds),
            "block_size": int(options.block_size),
            "cfa_green_mode": options.cfa_green_mode,
            "resolved_cfa_green_mode": resolved_mode,
            "cfa_resolution_source": "camera_spec" if options.cfa_green_mode == "AUTO" and options.preferred_cfa_green_mode else "image_estimate" if options.cfa_green_mode == "AUTO" else "manual",
        },
        "cfa_prediction": cfa_prediction,
        "estimate": estimate,
        "curves": curves,
        "heatmap": heatmap,
    }


def block_heatmap(rgb: np.ndarray, options: AnalysisOptions, resolved_mode: CfaGreenMode) -> list[list[dict[str, float]]]:
    size = max(16, int(options.block_size))
    h, w = rgb.shape[:2]
    rows: list[list[dict[str, float]]] = []
    for y in range(0, h - size + 1, size):
        row: list[dict[str, float]] = []
        for x in range(0, w - size + 1, size):
            block = rgb[y : y + size, x : x + size]
            curves = ratio_curves(block, options.ds)
            estimate = estimate_from_curves(curves, resolved_mode)
            g_values = np.array([item["G"] for item in curves], dtype=np.float32)
            confidence = float((g_values.max() - g_values.min()) / max(float(g_values.mean()), 1e-6))
            row.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "hue": float(estimate["estimated_hue"]),
                    "confidence": confidence,
                }
            )
        if row:
            rows.append(row)
    return rows


def generate_synthetic_sample(width: int = 384, height: int = 256, hue_shift: int = 120) -> tuple[Image.Image, Image.Image]:
    x = np.linspace(0, 1, width, dtype=np.float32)
    y = np.linspace(0, 1, height, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    base = np.zeros((height, width, 3), dtype=np.uint8)
    base[..., 0] = np.clip(80 + 110 * xx + 18 * np.sin(yy * math.tau * 5), 0, 255)
    base[..., 1] = np.clip(130 + 70 * yy + 15 * np.cos(xx * math.tau * 4), 0, 255)
    base[..., 2] = np.clip(95 + 80 * (1 - xx) + 25 * np.sin((xx + yy) * math.tau * 2), 0, 255)

    # Synthetic CFA-like trace: observed green positions receive a subtle high-frequency offset.
    rows, cols = np.indices((height, width))
    gxxg = ((rows % 2) == (cols % 2))
    base[..., 1] = np.clip(base[..., 1].astype(np.int16) + np.where(gxxg, 9, -4), 0, 255).astype(np.uint8)
    base[70:185, 145:315] = shift_hue_hsi(base[70:185, 145:315], hue_shift)

    original = Image.fromarray(base, "RGB")
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    draw.rectangle((145, 70, 315, 185), outline=(255, 255, 255), width=3)
    draw.rectangle((148, 73, 312, 182), outline=(20, 30, 40), width=2)
    return original, annotated
