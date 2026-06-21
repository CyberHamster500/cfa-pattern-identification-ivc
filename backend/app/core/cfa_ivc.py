from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.camera_metadata import BayerPattern, GreenMode, bayer_to_green_mode
from app.core.hue import aivc_counts


PATTERN_LAYOUTS: dict[BayerPattern, tuple[tuple[str, str], tuple[str, str]]] = {
    "RGGB": (("R", "G"), ("G", "B")),
    "BGGR": (("B", "G"), ("G", "R")),
    "GBRG": (("G", "B"), ("R", "G")),
    "GRBG": (("G", "R"), ("B", "G")),
}


@dataclass(frozen=True)
class CfaIvcResult:
    bayer_pattern: BayerPattern
    green_mode: GreenMode
    confidence: float
    scores: dict[BayerPattern, float]
    counts_by_channel: dict[str, list[list[int]]]


def _normalized_counts(counts: np.ndarray) -> np.ndarray:
    total = float(counts.sum())
    if total <= 0.0:
        return np.zeros_like(counts, dtype=np.float64)
    return counts.astype(np.float64) / total


def _pattern_score(pattern: BayerPattern, normalized: dict[str, np.ndarray]) -> float:
    layout = PATTERN_LAYOUTS[pattern]
    score = 0.0
    for row in (0, 1):
        for col in (0, 1):
            channel = layout[row][col]
            score += float(normalized[channel][row, col])
    return score


def identify_cfa_pattern_ivc(rgb: np.ndarray) -> CfaIvcResult:
    """Identify a Bayer CFA pattern using intermediate value counting.

    The method counts non-intermediate samples by 2x2 parity for each RGB channel.
    Each Bayer candidate is scored by how strongly the R, G, and B channel IVC
    peaks align with that candidate's color positions.
    """

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must be an HxWx3 array")

    channel_map = {"R": 0, "G": 1, "B": 2}
    counts = {name: aivc_counts(rgb[..., idx]) for name, idx in channel_map.items()}
    normalized = {name: _normalized_counts(channel_counts) for name, channel_counts in counts.items()}
    scores = {pattern: _pattern_score(pattern, normalized) for pattern in PATTERN_LAYOUTS}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_pattern = ranked[0][0]
    best_score = ranked[0][1]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = 0.0 if best_score <= 0.0 else max(0.0, (best_score - second_score) / best_score)
    green_mode = bayer_to_green_mode(best_pattern)
    if green_mode is None:  # Defensive; all entries in PATTERN_LAYOUTS are Bayer patterns.
        raise RuntimeError(f"unsupported Bayer pattern: {best_pattern}")
    return CfaIvcResult(
        bayer_pattern=best_pattern,
        green_mode=green_mode,
        confidence=float(confidence),
        scores=scores,
        counts_by_channel={name: value.astype(int).tolist() for name, value in counts.items()},
    )


def identify_cfa_pattern_payload(rgb: np.ndarray) -> dict[str, object]:
    result = identify_cfa_pattern_ivc(rgb)
    return {
        "bayer_pattern": result.bayer_pattern,
        "green_mode": result.green_mode,
        "confidence": result.confidence,
        "scores": result.scores,
        "counts_by_channel": result.counts_by_channel,
    }
