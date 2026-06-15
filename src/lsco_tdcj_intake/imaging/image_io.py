"""Image input/output helpers for LSCO TDCJ scan processing."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def read_image_bgr(path: Path | str) -> np.ndarray:
    """Read an image from disk as an OpenCV BGR array."""
    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")

    return image


def read_image_gray(path: Path | str) -> np.ndarray:
    """Read an image from disk as grayscale."""
    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")

    return image


def write_image(path: Path | str, image: np.ndarray) -> Path:
    """Write an image to disk, creating the parent folder if needed."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ok = cv2.imwrite(str(output_path), image)
    if not ok:
        raise ValueError(f"OpenCV could not write image: {output_path}")

    return output_path


def image_shape_text(image: np.ndarray) -> str:
    """Return a compact human-readable image shape string."""
    if image.ndim == 2:
        height, width = image.shape
        return f"{width}x{height} grayscale"

    height, width, channels = image.shape
    return f"{width}x{height}x{channels}"