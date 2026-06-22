from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from lsco_tdcj_intake.imaging.drop_color import remove_drop_color_bgr


@dataclass(frozen=True)
class BlankDetectionResult:
    is_blank: bool
    dark_pixel_ratio: float
    dark_pixels: int
    measured_pixels: int
    threshold: int
    max_dark_pixel_ratio: float


@dataclass(frozen=True)
class BlankDetectionConfig:
    """
    Detect whether a field crop contains meaningful dark content after
    drop-color removal.

    threshold:
        grayscale value below which a pixel is considered dark.

    max_dark_pixel_ratio:
        crop is blank if dark_pixel_ratio is <= this value.
    """

    threshold: int = 170
    max_dark_pixel_ratio: float = 0.003


DEFAULT_BLANK_DETECTION_CONFIG = BlankDetectionConfig()


def detect_blank_bgr(
    image_bgr: np.ndarray,
    config: BlankDetectionConfig = DEFAULT_BLANK_DETECTION_CONFIG,
) -> BlankDetectionResult:
    """
    Detect whether a BGR field crop is effectively blank after LSCO green
    drop-color removal.

    This is intended for OCR/free-text fields, not checkbox OMR.
    """
    if image_bgr.ndim == 2:
        gray = image_bgr
    else:
        cleaned = remove_drop_color_bgr(image_bgr)
        gray = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)

    dark_mask = gray < config.threshold

    dark_pixels = int(np.count_nonzero(dark_mask))
    measured_pixels = int(gray.size)

    if measured_pixels == 0:
        ratio = 0.0
    else:
        ratio = dark_pixels / measured_pixels

    return BlankDetectionResult(
        is_blank=ratio <= config.max_dark_pixel_ratio,
        dark_pixel_ratio=round(ratio, 6),
        dark_pixels=dark_pixels,
        measured_pixels=measured_pixels,
        threshold=config.threshold,
        max_dark_pixel_ratio=config.max_dark_pixel_ratio,
    )