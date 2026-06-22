from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class DropColorConfig:
    """
    HSV threshold config for removing LSCO green/drop-color form ink.

    Hue range is OpenCV HSV hue scale: 0-179.
    """

    lower_h: int = 35
    lower_s: int = 25
    lower_v: int = 40
    upper_h: int = 100
    upper_s: int = 255
    upper_v: int = 255


DEFAULT_DROP_COLOR_CONFIG = DropColorConfig()


def build_drop_color_mask_bgr(
    image_bgr: np.ndarray,
    config: DropColorConfig = DEFAULT_DROP_COLOR_CONFIG,
) -> np.ndarray:
    """
    Return a mask where likely green/drop-color form pixels are white (255).

    Input must be an OpenCV BGR image.
    """
    if image_bgr.ndim != 3:
        raise ValueError("build_drop_color_mask_bgr expects a BGR color image.")

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    lower = np.array(
        [config.lower_h, config.lower_s, config.lower_v],
        dtype=np.uint8,
    )
    upper = np.array(
        [config.upper_h, config.upper_s, config.upper_v],
        dtype=np.uint8,
    )

    return cv2.inRange(hsv, lower, upper)


def remove_drop_color_bgr(
    image_bgr: np.ndarray,
    config: DropColorConfig = DEFAULT_DROP_COLOR_CONFIG,
    replacement_bgr: tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """
    Replace likely green/drop-color form pixels with white.

    Black/dark handwriting should remain available for OCR, OMR, and blank detection.
    """
    if image_bgr.ndim == 2:
        return image_bgr.copy()

    mask = build_drop_color_mask_bgr(image_bgr, config=config)

    cleaned = image_bgr.copy()
    cleaned[mask > 0] = replacement_bgr

    return cleaned


def remove_drop_color_gray(
    image_bgr: np.ndarray,
    config: DropColorConfig = DEFAULT_DROP_COLOR_CONFIG,
) -> np.ndarray:
    """
    Remove drop color from a BGR image and return grayscale.
    """
    cleaned_bgr = remove_drop_color_bgr(image_bgr, config=config)
    return cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2GRAY)