from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2

from lsco_tdcj_intake.imaging.blank_detection import detect_blank_bgr


DEFAULT_INPUT_ROOT = Path("data/working/ocr_debug/page1_ocr/crops")
DEFAULT_OUTPUT_CSV = Path("data/working/ocr_debug/blank_detection/page1_blank_detection.csv")

DEFAULT_FIELDS = [
    "p1_last_name",
    "p1_first_name",
    "p1_mi",
    "p1_degree_cert_code",
    "p1_alien_reg_no",
    "p1_prev_college_row1_name",
    "p1_prev_college_row2_name",
    "p1_prev_college_row3_name",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Debug blank detection against existing Page 1 OCR field crops."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--fields", nargs="*", default=DEFAULT_FIELDS)

    args = parser.parse_args()
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for field_id in args.fields:
        crop_path = args.input_root / f"{field_id}.png"
        image = cv2.imread(str(crop_path), cv2.IMREAD_COLOR)

        if image is None:
            rows.append(
                {
                    "field_id": field_id,
                    "crop_path": str(crop_path),
                    "is_blank": "",
                    "dark_pixel_ratio": "",
                    "dark_pixels": "",
                    "measured_pixels": "",
                    "notes": "crop not found or unreadable",
                }
            )
            continue

        result = detect_blank_bgr(image)

        rows.append(
            {
                "field_id": field_id,
                "crop_path": str(crop_path),
                "is_blank": result.is_blank,
                "dark_pixel_ratio": result.dark_pixel_ratio,
                "dark_pixels": result.dark_pixels,
                "measured_pixels": result.measured_pixels,
                "notes": "",
            }
        )

    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "field_id",
                "crop_path",
                "is_blank",
                "dark_pixel_ratio",
                "dark_pixels",
                "measured_pixels",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote blank detection debug CSV: {args.output_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())