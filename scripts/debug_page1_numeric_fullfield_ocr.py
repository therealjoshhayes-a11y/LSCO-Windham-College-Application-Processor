from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CROPS_DIR = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "crops"
)

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "numeric_fullfield"
)

TARGET_FIELDS = {
    "p1_tdcj_number": {
        "min_digits": 8,
        "max_digits": 8,
        "note": "TDCJ number full boxed-field numeric OCR; exactly 8 digits expected; review required.",
    },
    "p1_ssn": {
        "min_digits": 9,
        "max_digits": 9,
        "note": "SSN full boxed-field numeric OCR; exactly 9 digits expected; review required.",
    },
    "p1_date_of_birth": {
        "min_digits": 8,
        "max_digits": 8,
        "note": "DOB full boxed-field numeric OCR as MMDDYYYY digits; exactly 8 digits expected; review required.",
    },
}


@dataclass
class NumericFullFieldResult:
    field_id: str
    status: str
    best_digits: str
    best_raw_text: str
    best_variant: str
    min_digits: int
    max_digits: int
    shape_valid: bool
    all_candidates: str
    source_crop_path: str
    processed_image_path: str
    notes: str
    review_value: str = ""
    review_notes: str = ""


def digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def find_crop(crops_dir: Path, field_id: str) -> Path:
    matches = sorted(crops_dir.glob(f"*{field_id}*.png"))
    if not matches:
        matches = sorted(crops_dir.glob(f"*{field_id}*.*"))

    if not matches:
        raise FileNotFoundError(f"No crop found for {field_id} in {crops_dir}")

    return matches[0]


def drop_green_lines(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 25, 25])
    upper_green = np.array([95, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    cleaned = bgr.copy()
    cleaned[green_mask > 0] = (255, 255, 255)
    return cleaned


def preprocess_variants(bgr: np.ndarray) -> dict[str, np.ndarray]:
    cleaned = drop_green_lines(bgr)
    gray = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)

    variants: dict[str, np.ndarray] = {}

    variants["gray_drop_green"] = gray

    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants["otsu_drop_green"] = otsu

    _, fixed_180 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    variants["fixed_180_drop_green"] = fixed_180

    _, fixed_200 = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    variants["fixed_200_drop_green"] = fixed_200

    scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    _, scaled_otsu = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants["scaled_otsu_drop_green"] = scaled_otsu

    return variants


def run_tesseract_numeric(image: np.ndarray) -> str:
    config = (
        "--oem 3 "
        "--psm 7 "
        "-c tessedit_char_whitelist=0123456789 "
        "-c classify_bln_numeric_mode=1"
    )
    return pytesseract.image_to_string(image, config=config).strip()


def shape_valid(digits: str, min_digits: int, max_digits: int) -> bool:
    return min_digits <= len(digits) <= max_digits


def choose_best_candidate(
    candidates: list[tuple[str, str, str]],
    min_digits: int,
    max_digits: int,
) -> tuple[str, str, str]:
    valid_shape = [
        item for item in candidates
        if shape_valid(item[2], min_digits, max_digits)
    ]

    if valid_shape:
        return valid_shape[0]

    return max(candidates, key=lambda item: len(item[2]))


def process_field(crops_dir: Path, output_dir: Path, field_id: str) -> NumericFullFieldResult:
    meta = TARGET_FIELDS[field_id]
    min_digits = int(meta["min_digits"])
    max_digits = int(meta["max_digits"])

    crop_path = find_crop(crops_dir, field_id)
    bgr = cv2.imread(str(crop_path))
    if bgr is None:
        raise RuntimeError(f"Could not read crop image: {crop_path}")

    variants = preprocess_variants(bgr)

    candidate_rows: list[tuple[str, str, str]] = []
    for variant_name, image in variants.items():
        raw_text = run_tesseract_numeric(image)
        candidate_rows.append((variant_name, raw_text, digits_only(raw_text)))

    best_variant, best_raw_text, best_digits = choose_best_candidate(
        candidate_rows,
        min_digits,
        max_digits,
    )

    processed_path = output_dir / f"{field_id}__{best_variant}.png"
    cv2.imwrite(str(processed_path), variants[best_variant])

    all_candidates = " | ".join(
        f"{variant}: raw={raw!r}, digits={digits!r}"
        for variant, raw, digits in candidate_rows
    )

    return NumericFullFieldResult(
        field_id=field_id,
        status="ocr_candidate_needs_review",
        best_digits=best_digits,
        best_raw_text=best_raw_text,
        best_variant=best_variant,
        min_digits=min_digits,
        max_digits=max_digits,
        shape_valid=shape_valid(best_digits, min_digits, max_digits),
        all_candidates=all_candidates,
        source_crop_path=str(crop_path),
        processed_image_path=str(processed_path),
        notes=str(meta["note"]),
    )


def write_outputs(results: list[NumericFullFieldResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "page1_numeric_fullfield_ocr.csv"
    json_path = output_dir / "page1_numeric_fullfield_ocr.json"

    rows = [asdict(result) for result in results]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    print(f"Wrote CSV:  {csv_path}")
    print(f"Wrote JSON: {json_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run full-field numeric OCR evidence for Page 1 identity fields."
    )

    parser.add_argument(
        "--crops-dir",
        default=str(DEFAULT_CROPS_DIR),
        help="Input Page 1 OCR crop folder.",
    )

    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output folder for numeric full-field OCR evidence.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    crops_dir = Path(args.crops_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not crops_dir.exists():
        print(f"Crop folder not found: {crops_dir}")
        print("Run scripts\\debug_page1_ocr.py first so the Page 1 crop images exist.")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[NumericFullFieldResult] = []
    for field_id in TARGET_FIELDS:
        result = process_field(crops_dir, output_dir, field_id)
        results.append(result)

    write_outputs(results, output_dir)

    print()
    print("Summary:")
    for result in results:
        print(
            f"{result.field_id}: digits={result.best_digits!r} "
            f"variant={result.best_variant} "
            f"shape_valid={result.shape_valid}"
        )

    print()
    print("Policy: all results are review evidence only. Nothing is auto-accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())