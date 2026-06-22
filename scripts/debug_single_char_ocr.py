from __future__ import annotations

from pathlib import Path

import cv2
import pytesseract
from PIL import Image
from lsco_tdcj_intake.imaging.drop_color import remove_drop_color_bgr


INPUT = Path("data/working/ocr_debug/page1_ocr/crops/p1_mi.png")
OUTPUT_ROOT = Path("data/working/ocr_debug/single_char_ocr")


def tesseract_text(image, label: str) -> None:
    config = (
        "--psm 10 "
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )
    text = pytesseract.image_to_string(image, config=config).strip()
    print(f"{label}: {text!r}")


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    bgr = cv2.imread(str(INPUT))
    if bgr is None:
        raise FileNotFoundError(INPUT)

    cleaned_bgr = remove_drop_color_bgr(bgr)
    cv2.imwrite(str(OUTPUT_ROOT / "p1_mi_cleaned.png"), cleaned_bgr)

    gray = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2GRAY)

    variants = {
        "gray": gray,
        "threshold_180": cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1],
        "blur_threshold_180": cv2.threshold(
            cv2.GaussianBlur(gray, (3, 3), 0),
            180,
            255,
            cv2.THRESH_BINARY,
        )[1],
        "threshold_200": cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)[1],
        "otsu": cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        "inverted_otsu": cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
    }

    print(f"Input: {INPUT}")
    print(f"Output: {OUTPUT_ROOT}")

    for label, img in variants.items():
        out_path = OUTPUT_ROOT / f"p1_mi_{label}.png"
        cv2.imwrite(str(out_path), img)
        pil_img = Image.fromarray(img)
        tesseract_text(pil_img, label)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())