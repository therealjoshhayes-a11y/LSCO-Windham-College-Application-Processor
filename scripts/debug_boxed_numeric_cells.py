from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

from lsco_tdcj_intake.imaging.drop_color import remove_drop_color_bgr


INPUT = Path("data/working/ocr_debug/page1_ocr/crops/p1_ssn.png")
OUTPUT_ROOT = Path("data/working/ocr_debug/boxed_numeric_cells/p1_ssn")


def ocr_digit(cell_img) -> str:
    config = "--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789"
    return pytesseract.image_to_string(Image.fromarray(cell_img), config=config).strip()


def find_green_vertical_lines(bgr: np.ndarray) -> list[int]:
    # Green form lines: high G, lower R/B in BGR image.
    b, g, r = cv2.split(bgr)
    green_mask = (g > 110) & (g > r * 1.25) & (g > b * 1.25)

    col_counts = green_mask.sum(axis=0)
    threshold = max(8, int(green_mask.shape[0] * 0.25))

    candidate_cols = np.where(col_counts >= threshold)[0].tolist()

    groups: list[list[int]] = []
    for col in candidate_cols:
        if not groups or col > groups[-1][-1] + 2:
            groups.append([col])
        else:
            groups[-1].append(col)

    centers = [int(sum(group) / len(group)) for group in groups if len(group) >= 2]
    return centers


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    bgr = cv2.imread(str(INPUT))
    if bgr is None:
        raise FileNotFoundError(INPUT)

    h, w = bgr.shape[:2]
    print(f"Input: {INPUT}")
    print(f"Size: {w} x {h}")

    lines = find_green_vertical_lines(bgr)
    print("green vertical lines:", lines)

    clean = remove_drop_color_bgr(bgr)
    gray = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    # Adjacent green line pairs define boxes/gaps. Add right edge so final SSN cell is included.
    boundaries = lines + [w - 1]

    cells: list[tuple[int, int]] = []
    for left, right in zip(boundaries, boundaries[1:]):
        width = right - left
        if width < 70:
            continue
        cells.append((left, right))

    print("candidate cells:", cells)

    digits: list[str] = []
    for index, (x1, x2) in enumerate(cells, start=1):
        pad_x = max(4, int((x2 - x1) * 0.08))
        pad_y = max(4, int(h * 0.08))
        cell = thresh[pad_y:h - pad_y, x1 + pad_x:x2 - pad_x]

        # Tight-crop to dark ink, then enlarge and re-pad for Tesseract.
        ink = cell < 180
        ys, xs = np.where(ink)
        if len(xs) > 0 and len(ys) > 0:
            x_min, x_max = xs.min(), xs.max()
            y_min, y_max = ys.min(), ys.max()
            cell = cell[y_min:y_max + 1, x_min:x_max + 1]

        cell = cv2.resize(cell, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        cell = cv2.copyMakeBorder(
            cell,
            30,
            30,
            30,
            30,
            cv2.BORDER_CONSTANT,
            value=255,
        )

        out_path = OUTPUT_ROOT / f"cell_{index:02d}_{x1}_{x2}.png"
        cv2.imwrite(str(out_path), cell)

        digit = ocr_digit(cell)
        digits.append(digit)
        print(f"cell {index} {x1}-{x2}: {digit!r} -> {out_path}")

    print("joined:", "".join(digits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())