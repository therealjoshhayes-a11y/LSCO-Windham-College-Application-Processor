from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import re

import cv2
import numpy as np
import pytesseract


@dataclass(frozen=True)
class OCRResult:
    text: str
    raw_text: str
    confidence: float
    engine: str = "tesseract"


def _drop_form_color_bgr(image: np.ndarray) -> np.ndarray:
    """
    Remove LSCO/drop-color form ink before OCR.

    Assumes OpenCV BGR input. Green-ish pixels are converted to white.
    Black handwriting/print should remain.
    """
    if image.ndim != 3:
        return image

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Broad green/cyan-green band. Conservative saturation/value floor avoids
    # turning dark handwriting white.
    lower_green = np.array([35, 25, 40], dtype=np.uint8)
    upper_green = np.array([100, 255, 255], dtype=np.uint8)

    mask = cv2.inRange(hsv, lower_green, upper_green)

    cleaned = image.copy()
    cleaned[mask > 0] = (255, 255, 255)

    return cleaned


def _to_gray(image: Any, *, drop_form_color: bool = True) -> np.ndarray:
    if isinstance(image, (str, Path)):
        img = cv2.imread(str(image), cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {image}")

        if drop_form_color:
            img = _drop_form_color_bgr(img)

        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if isinstance(image, np.ndarray):
        if image.ndim == 2:
            return image

        img = image
        if drop_form_color:
            img = _drop_form_color_bgr(img)

        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    raise TypeError(f"Unsupported image input type: {type(image)!r}")

def prepare_for_tesseract(
    image: Any,
    *,
    drop_form_color: bool = True,
) -> np.ndarray:
    gray = _to_gray(image, drop_form_color=drop_form_color)

    if gray.shape[0] < 80:
        scale = max(2, round(120 / max(gray.shape[0], 1)))
        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    _, thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    return thresh


def _clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x0c", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _mean_confidence(data: dict[str, list[str]]) -> float:
    values: list[float] = []

    for raw in data.get("conf", []):
        try:
            value = float(raw)
        except ValueError:
            continue

        if value >= 0:
            values.append(value)

    if not values:
        return 0.0

    return round((sum(values) / len(values)) / 100.0, 4)

def ocr_image(
    image: Any,
    *,
    psm: int = 7,
    allowlist: str | None = None,
    field_id: str | None = None,
    drop_form_color: bool = True,
) -> OCRResult:
    """
    Run local Tesseract OCR on a cropped field image.

    field_id is accepted for compatibility with debug scripts, but profile
    decisions should live outside this low-level engine.
    """
    prepared = prepare_for_tesseract(
    image,
    drop_form_color=drop_form_color,
)
    config_parts = [
        "--oem 3",
        f"--psm {psm}",
    ]

    if allowlist:
        config_parts.append(f"-c tessedit_char_whitelist={allowlist}")

    config = " ".join(config_parts)

    raw_text = pytesseract.image_to_string(prepared, config=config)

    data = pytesseract.image_to_data(
        prepared,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    return OCRResult(
        text=_clean_text(raw_text),
        raw_text=raw_text,
        confidence=_mean_confidence(data),
    )