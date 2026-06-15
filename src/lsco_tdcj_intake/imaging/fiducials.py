"""Detect black corner fiducial squares on LSCO TDCJ scanned pages."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FiducialCandidate:
    """One detected square-like fiducial candidate."""

    x: int
    y: int
    width: int
    height: int
    area: float
    center_x: float
    center_y: float

    @property
    def aspect_ratio(self) -> float:
        """Return width / height."""
        return self.width / self.height if self.height else 0.0


@dataclass(frozen=True)
class OrderedFiducials:
    """Four fiducials ordered as page corners."""

    top_left: FiducialCandidate
    top_right: FiducialCandidate
    bottom_right: FiducialCandidate
    bottom_left: FiducialCandidate

    def as_points_float32(self) -> np.ndarray:
        """Return corner centers as OpenCV float32 points."""
        return np.array(
            [
                [self.top_left.center_x, self.top_left.center_y],
                [self.top_right.center_x, self.top_right.center_y],
                [self.bottom_right.center_x, self.bottom_right.center_y],
                [self.bottom_left.center_x, self.bottom_left.center_y],
            ],
            dtype=np.float32,
        )


def threshold_dark_regions(gray_image: np.ndarray) -> np.ndarray:
    """Return binary mask for dark printed regions."""
    if gray_image.ndim != 2:
        raise ValueError("threshold_dark_regions expects a grayscale image")

    blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
    _, mask = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )
    return mask


def find_square_candidates(
    gray_image: np.ndarray,
    min_area: float = 100.0,
    max_area_ratio: float = 0.02,
    min_aspect: float = 0.70,
    max_aspect: float = 1.30,
) -> list[FiducialCandidate]:
    """Find square-like dark connected components."""
    mask = threshold_dark_regions(gray_image)
    image_area = float(gray_image.shape[0] * gray_image.shape[1])
    max_area = image_area * max_area_ratio

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[FiducialCandidate] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area or area > max_area:
            continue

        x, y, width, height = cv2.boundingRect(contour)
        if height == 0:
            continue

        aspect = width / height
        if aspect < min_aspect or aspect > max_aspect:
            continue

        candidates.append(
            FiducialCandidate(
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                area=area,
                center_x=x + (width / 2.0),
                center_y=y + (height / 2.0),
            )
        )

    return sorted(candidates, key=lambda item: item.area, reverse=True)


def order_fiducials(candidates: list[FiducialCandidate]) -> OrderedFiducials:
    """Order four fiducial candidates as page corners."""
    if len(candidates) < 4:
        raise ValueError(f"Need at least 4 fiducial candidates, found {len(candidates)}")

    selected = candidates[:4]

    top_two = sorted(selected, key=lambda item: item.center_y)[:2]
    bottom_two = sorted(selected, key=lambda item: item.center_y)[-2:]

    top_left, top_right = sorted(top_two, key=lambda item: item.center_x)
    bottom_left, bottom_right = sorted(bottom_two, key=lambda item: item.center_x)

    return OrderedFiducials(
        top_left=top_left,
        top_right=top_right,
        bottom_right=bottom_right,
        bottom_left=bottom_left,
    )


def detect_ordered_fiducials(gray_image: np.ndarray) -> OrderedFiducials:
    """Detect and order page corner fiducials."""
    candidates = find_square_candidates(gray_image)
    return order_fiducials(candidates)


def draw_fiducial_debug(image_bgr: np.ndarray, ordered: OrderedFiducials) -> np.ndarray:
    """Draw detected fiducials on a copy of the image."""
    output = image_bgr.copy()

    labels = [
        ("TL", ordered.top_left),
        ("TR", ordered.top_right),
        ("BR", ordered.bottom_right),
        ("BL", ordered.bottom_left),
    ]

    for label, candidate in labels:
        cv2.rectangle(
            output,
            (candidate.x, candidate.y),
            (candidate.x + candidate.width, candidate.y + candidate.height),
            (0, 255, 0),
            3,
        )
        cv2.putText(
            output,
            label,
            (candidate.x, max(candidate.y - 10, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    return output

