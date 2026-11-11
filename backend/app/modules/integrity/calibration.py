"""
Confidence calibration: map the auditor's raw confidence to how often it is right.

The map is fitted on faculty-labelled questions (the gold set) with isotonic
regression and saved as JSON:

    {"prompt_version": "audit-v2", "fitted_on": 212, "points": [[0.33, 0.41], [0.6, 0.72], ...]}

Raw values between points are interpolated. Without a file, or when the file was
fitted for another prompt version, confidence is used as is (identity) and the
audit records that it is uncalibrated.
"""
import json
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class CalibrationMap:
    prompt_version: str
    points: tuple[tuple[float, float], ...]
    fitted_on: int | None = None

    def apply(self, raw: float) -> float:
        xs = [x for x, _ in self.points]
        if not xs:
            return raw
        if raw <= xs[0]:
            return self.points[0][1]
        if raw >= xs[-1]:
            return self.points[-1][1]
        i = bisect_left(xs, raw)
        (x0, y0), (x1, y1) = self.points[i - 1], self.points[i]
        return y0 if x1 == x0 else y0 + (y1 - y0) * (raw - x0) / (x1 - x0)


@lru_cache(maxsize=4)
def _load(path: str) -> CalibrationMap | None:
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text())
        points = tuple(sorted((float(x), float(y)) for x, y in data["points"]))
        return CalibrationMap(
            prompt_version=str(data["prompt_version"]), points=points, fitted_on=data.get("fitted_on"),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def calibrate(raw: float, prompt_version: str) -> tuple[float, str]:
    """Return (calibrated confidence, a short description of the calibration used)."""
    mapping = _load(settings.INTEGRITY_CALIBRATION_FILE)
    if mapping is None or mapping.prompt_version != prompt_version:
        return raw, "none"
    return round(min(max(mapping.apply(raw), 0.0), 1.0), 3), f"isotonic:{mapping.fitted_on or '?'}"


def fit_isotonic(samples: list[tuple[float, bool]]) -> list[tuple[float, float]]:
    """
    Pool-adjacent-violators: the non-decreasing step function of raw confidence that
    best matches observed correctness. Returns (raw, accuracy) points.
    """
    blocks: list[list[float]] = []  # [sum_correct, count, min_x, max_x]
    for x, correct in sorted(samples):
        blocks.append([1.0 if correct else 0.0, 1.0, x, x])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, n, _, hi = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += n
            blocks[-1][3] = hi
    points: list[tuple[float, float]] = []
    for s, n, lo, hi in blocks:
        value = round(s / n, 3)
        points.append((lo, value))
        if hi != lo:
            points.append((hi, value))
    return points
