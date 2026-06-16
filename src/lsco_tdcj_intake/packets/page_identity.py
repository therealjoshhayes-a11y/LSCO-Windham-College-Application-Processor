"""Lightweight page identity checks for LSCO TDCJ form packets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class PageIdentityResult:
    image_path: str
    predicted_page: int | None
    decision: str
    confidence: float
    page1_score: float
    page2_score: float

    def is_page(self, page_number: int) -> bool:
        return self.predicted_page == page_number and self.decision == "matched"


def _read_gray(image_path: str | Path) -> np.ndarray:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return image


def _crop_top_band(gray: np.ndarray) -> np.ndarray:
    height, width = gray.shape[:2]
    return gray[0 : int(height * 0.22), 0:width]


def _dark_pixel_score(region: np.ndarray, threshold: int = 170) -> float:
    if region.size == 0:
        return 0.0
    return float(np.count_nonzero(region <= threshold) / region.size)


def classify_page_image(image_path: str | Path) -> PageIdentityResult:
    """Classify a warped or extracted form image as Page 1 or Page 2.

    This is intentionally simple and conservative. It uses top-band layout signals:
    Page 1 has a very large title block and enrollment bar.
    Page 2 has the FERPA heading and Section A bar higher on the page.
    """
    gray = _read_gray(image_path)
    top = _crop_top_band(gray)

    h, w = top.shape[:2]

    # Page 1: large APPLICATION title and Enrollment Information bar.
    p1_title_region = top[int(h * 0.16) : int(h * 0.40), int(w * 0.04) : int(w * 0.78)]
    p1_bar_region = top[int(h * 0.50) : int(h * 0.68), int(w * 0.04) : int(w * 0.96)]

    # Page 2: FERPA header and Section A bar near the top.
    p2_title_region = top[int(h * 0.02) : int(h * 0.28), int(w * 0.04) : int(w * 0.72)]
    p2_bar_region = top[int(h * 0.30) : int(h * 0.48), int(w * 0.04) : int(w * 0.96)]

    page1_score = (
        _dark_pixel_score(p1_title_region) * 0.45
        + _dark_pixel_score(p1_bar_region) * 0.55
    )

    page2_score = (
        _dark_pixel_score(p2_title_region) * 0.35
        + _dark_pixel_score(p2_bar_region) * 0.65
    )

    delta = abs(page1_score - page2_score)

    if delta < 0.015:
        predicted = None
        decision = "uncertain"
        confidence = 0.0
    elif page1_score > page2_score:
        predicted = 1
        decision = "matched"
        confidence = min(1.0, delta / 0.10)
    else:
        predicted = 2
        decision = "matched"
        confidence = min(1.0, delta / 0.10)

    return PageIdentityResult(
        image_path=str(image_path),
        predicted_page=predicted,
        decision=decision,
        confidence=round(confidence, 4),
        page1_score=round(page1_score, 6),
        page2_score=round(page2_score, 6),
    )


def require_page(image_path: str | Path, expected_page: int) -> PageIdentityResult:
    result = classify_page_image(image_path)

    if not result.is_page(expected_page):
        raise ValueError(
            f"Page identity mismatch for {image_path}. "
            f"Expected page {expected_page}, got {result.predicted_page} "
            f"decision={result.decision} confidence={result.confidence} "
            f"page1_score={result.page1_score} page2_score={result.page2_score}"
        )

    return result