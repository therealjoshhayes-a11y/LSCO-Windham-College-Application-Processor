from __future__ import annotations

import argparse
import csv
import inspect
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import cv2

from lsco_tdcj_intake.form_maps.loader import load_page1_map
from lsco_tdcj_intake.imaging.field_cropper import crop_field_from_image, save_crop_result
from lsco_tdcj_intake.normalization.dates import normalize_mmddyyyy
from lsco_tdcj_intake.normalization.education import normalize_state_abbrev, is_valid_state_abbrev
from lsco_tdcj_intake.normalization.identifiers import normalize_ssn
from lsco_tdcj_intake.normalization.names import normalize_name
from lsco_tdcj_intake.ocr.tesseract_engine import ocr_image
from lsco_tdcj_intake.ocr.profiles import get_profile_for_page1_field
from lsco_tdcj_intake.imaging.blank_detection import detect_blank_bgr


DEFAULT_OUTPUT_ROOT = Path("data/working/ocr_debug/page1_ocr")

PAGE1_OCR_FIELDS = [
    "p1_year",
    "p1_degree_cert_code",
    "p1_ssn",
    "p1_tdcj_number",
    "p1_date_of_birth",
    "p1_last_name",
    "p1_first_name",
    "p1_mi",
    "p1_former_name",
    "p1_alien_reg_no",
    "p1_hs_name",
    "p1_hs_state",
    "p1_hs_year",
    "p1_ged_year",
    "p1_prev_college_row1_name",
    "p1_prev_college_row1_city_state",
    "p1_prev_college_row1_years_attended",
    "p1_prev_college_row2_name",
    "p1_prev_college_row2_city_state",
    "p1_prev_college_row2_years_attended",
    "p1_prev_college_row3_name",
    "p1_prev_college_row3_city_state",
    "p1_prev_college_row3_years_attended",
    "p1_student_signature_date",
]


def _field_map_fields(form_map: Any) -> dict[str, Any]:
    if isinstance(form_map, dict):
        fields = form_map.get("fields", {})
    else:
        fields = getattr(form_map, "fields", {})

    if not isinstance(fields, dict):
        raise TypeError("Page 1 form map fields could not be read as a dictionary.")

    return fields


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def _get_attr_or_key(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _call_crop_field_from_image(
    image: Any,
    form_map: Any,
    field_id: str,
    page_number: int = 1,
) -> Any:
    signature = inspect.signature(crop_field_from_image)
    params = signature.parameters

    kwargs: dict[str, Any] = {}

    if "page_number" in params:
        kwargs["page_number"] = page_number
    elif "page" in params:
        kwargs["page"] = page_number

    try:
        return crop_field_from_image(image, form_map, field_id, **kwargs)
    except TypeError:
        pass

    try:
        return crop_field_from_image(image=image, form_map=form_map, field_id=field_id, **kwargs)
    except TypeError:
        pass

    try:
        return crop_field_from_image(page_image=image, form_map=form_map, field_id=field_id, **kwargs)
    except TypeError:
        pass

    return crop_field_from_image(image, form_map, field_id)


def _save_crop(crop_result: Any, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        save_crop_result(crop_result, output_path)
        return
    except TypeError:
        pass

    crop_image = _get_attr_or_key(crop_result, "image")
    if crop_image is None:
        crop_image = _get_attr_or_key(crop_result, "crop")
    if crop_image is None:
        crop_image = _get_attr_or_key(crop_result, "crop_image")

    if crop_image is None:
        raise ValueError(f"Could not find crop image on crop result for {output_path}")

    cv2.imwrite(str(output_path), crop_image)


def _crop_image_from_result(crop_result: Any) -> Any:
    crop_image = _get_attr_or_key(crop_result, "image")
    if crop_image is None:
        crop_image = _get_attr_or_key(crop_result, "crop")
    if crop_image is None:
        crop_image = _get_attr_or_key(crop_result, "crop_image")
    if crop_image is None:
        raise ValueError("Could not find crop image on crop result.")
    return crop_image


def _ocr_field_image(image: Any, field_id: str) -> dict[str, Any]:
    profile = get_profile_for_page1_field(field_id)

    try:
        if profile.profile_id == "single_letter_review":
            threshold_mode = "fixed_180"
            psm = 10
            apply_blur = False
        else:
            threshold_mode = "otsu"
            psm = 7
            apply_blur = True

        result = ocr_image(
            image,
            field_id=field_id,
            allowlist=profile.allowlist,
            threshold_mode=threshold_mode,
            apply_blur=apply_blur,
            psm=psm,
        )

    except TypeError:
        result = ocr_image(image)

    if isinstance(result, str):
        return {
            "raw_text": result,
            "confidence": None,
            "profile_id": profile.profile_id,
            "engine_result": {"text": result},
        }

    raw_text = _get_attr_or_key(result, "text", "")
    if raw_text is None:
        raw_text = _get_attr_or_key(result, "raw_text", "")

    confidence = _get_attr_or_key(result, "confidence")
    if confidence is None:
        confidence = _get_attr_or_key(result, "mean_confidence")

    return {
        "raw_text": str(raw_text or ""),
        "confidence": confidence,
        "profile_id": profile.profile_id,
        "engine_result": _to_jsonable(result),
    }


def _normalize_field(field_id: str, raw_text: str) -> tuple[str, str]:
    raw_text = raw_text or ""

    if field_id in {"p1_last_name", "p1_first_name", "p1_mi", "p1_former_name"}:
        return normalize_name(raw_text), "name"

    if field_id == "p1_ssn":
        return normalize_ssn(raw_text), "ssn"

    if field_id in {"p1_date_of_birth", "p1_student_signature_date"}:
        return normalize_mmddyyyy(raw_text), "date_mmddyyyy"

    if field_id == "p1_hs_state":
        return normalize_state_abbrev(raw_text), "state_abbrev"

    if field_id in {"p1_year", "p1_hs_year", "p1_ged_year"}:
        digits = "".join(ch for ch in raw_text if ch.isdigit())
        return digits[:4], "year"

    if field_id in {"p1_tdcj_number", "p1_alien_reg_no"}:
        alnum = "".join(ch for ch in raw_text.upper() if ch.isalnum())
        return alnum, "identifier"

    if field_id == "p1_degree_cert_code":
        cleaned = "".join(ch for ch in raw_text.upper() if ch.isalnum() or ch in {"-", "_"})
        return cleaned, "degree_cert_code"

    cleaned = " ".join(raw_text.upper().strip().split())
    return cleaned, "text"


def _safe_confidence(confidence: Any) -> float:
    try:
        return float(confidence)
    except (TypeError, ValueError):
        return 0.0


def _looks_like_garbage(value: str) -> bool:
    if not value:
        return False

    if len(value) >= 20:
        unique_chars = len(set(value))
        if unique_chars <= 6:
            return True

    repeated_z = value.count("Z")
    repeated_2 = value.count("2")
    repeated_4 = value.count("4")

    if len(value) >= 20 and (repeated_z + repeated_2 + repeated_4) / len(value) >= 0.35:
        return True

    return False


def _status_for_field(field_id: str, normalized_text: str, confidence: Any) -> tuple[str, str]:
    value = normalized_text or ""
    conf = _safe_confidence(confidence)

    if not value:
        return "blank_or_needs_review", "No normalized OCR value."

    if _looks_like_garbage(value):
        return "ocr_candidate_needs_review", "Candidate looks like OCR/gridline noise."

    if field_id == "p1_ssn":
        if len(value) == 9 and value.isdigit() and conf >= 0.60:
            return "accepted", ""
        return "ocr_candidate_needs_review", "SSN must be exactly 9 digits with confidence >= 0.60."

    if field_id == "p1_date_of_birth":
        if len(value) == 10 and value.count("/") == 2 and conf >= 0.60:
            return "accepted", ""
        return "ocr_candidate_needs_review", "DOB must normalize to MM/DD/YYYY with confidence >= 0.60."

    if field_id == "p1_student_signature_date":
        if len(value) == 10 and value.count("/") == 2 and conf >= 0.50:
            return "accepted", ""
        return "ocr_candidate_needs_review", "Signature date must normalize to MM/DD/YYYY with confidence >= 0.50."

    if field_id == "p1_tdcj_number":
        if value.isdigit() and 5 <= len(value) <= 10 and conf >= 0.60:
            return "accepted", ""
        return "ocr_candidate_needs_review", "TDCJ number must be 5-10 digits with confidence >= 0.60."

    if field_id == "p1_hs_state":
        if len(value) == 2 and value.isalpha() and is_valid_state_abbrev(value) and conf >= 0.40:
            return "accepted", ""
        return "ocr_candidate_needs_review", "State must be a valid 2-letter abbreviation with confidence >= 0.40."

    if field_id in {"p1_year", "p1_hs_year", "p1_ged_year"}:
        if len(value) == 4 and value.isdigit() and conf >= 0.60:
            return "accepted", ""
        return "ocr_candidate_needs_review", "Year must be exactly 4 digits with confidence >= 0.60."

    if field_id in {"p1_last_name", "p1_first_name"}:
        if len(value) >= 2 and value.isalpha() and conf >= 0.50:
            return "accepted", ""
        if len(value) >= 2 and value.isalpha() and conf == 0.0:
            return "accepted", "Accepted by required-name grammar fallback; Tesseract confidence unavailable."
        return "ocr_candidate_needs_review", "Name must be alphabetic or pass required-name grammar fallback."

    if field_id in {"p1_mi"}:
        if len(value) == 1 and value.isalpha() and conf >= 0.50:
            return "accepted", ""
        return "ocr_candidate_needs_review", "Middle initial must be one alphabetic character with confidence >= 0.50."

    if field_id in {"p1_former_name"}:
        if len(value) >= 2 and conf >= 0.50:
            return "accepted", ""
        return "ocr_candidate_needs_review", "Former name candidate below confidence threshold."

    if field_id in {"p1_degree_cert_code", "p1_alien_reg_no"}:
        if 2 <= len(value) <= 12 and conf >= 0.60:
            return "accepted", ""
        return "ocr_candidate_needs_review", "Identifier candidate below length/confidence threshold."

    if field_id.startswith("p1_prev_college_") or field_id == "p1_hs_name":
        if 2 <= len(value) <= 60 and conf >= 0.60:
            return "accepted", ""
        return "ocr_candidate_needs_review", "Free-text candidate below confidence threshold or implausible length."

    if conf >= 0.60:
        return "accepted", ""

    return "ocr_candidate_needs_review", "Candidate below confidence threshold."


def run_page1_ocr(warped_page_path: Path, output_root: Path) -> dict[str, Any]:
    if not warped_page_path.exists():
        raise FileNotFoundError(f"Warped Page 1 image not found: {warped_page_path}")

    output_root.mkdir(parents=True, exist_ok=True)
    crops_root = output_root / "crops"
    crops_root.mkdir(parents=True, exist_ok=True)

    image = cv2.imread(str(warped_page_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {warped_page_path}")

    page1_map = load_page1_map()
    fields = _field_map_fields(page1_map)

    rows: list[dict[str, Any]] = []

    for field_id in PAGE1_OCR_FIELDS:
        if field_id not in fields:
            rows.append(
                {
                    "field_id": field_id,
                    "status": "missing_from_map",
                    "raw_text": "",
                    "normalized_text": "",
                    "normalization": "",
                    "confidence": "",
                    "crop_path": "",
                    "notes": "Field configured for OCR but not present in Page 1 map.",
                }
            )
            continue

        crop_path = crops_root / f"{field_id}.png"

        try:
            crop_result = _call_crop_field_from_image(
                image=image,
                form_map=page1_map,
                field_id=field_id,
                page_number=1,
            )
            _save_crop(crop_result, crop_path)
            crop_image = _crop_image_from_result(crop_result)
            blank_result = detect_blank_bgr(crop_image)
        except Exception as exc:
            rows.append(
                {
                    "field_id": field_id,
                    "status": "crop_failed",
                    "raw_text": "",
                    "normalized_text": "",
                    "normalization": "",
                    "confidence": "",
                    "crop_path": str(crop_path),
                    "notes": repr(exc),
                }
            )
            continue

        try:
            profile = get_profile_for_page1_field(field_id)

            if blank_result.is_blank:
                raw_text = ""
                confidence = ""
                normalized_text = ""
                normalization = "blank_detection"
                if profile.review_if_blank:
                    status = "blank_or_needs_review"
                    notes = f"Blank detected; dark_pixel_ratio={blank_result.dark_pixel_ratio}."
                else:
                    status = "blank_accepted"
                    notes = f"Optional blank accepted; dark_pixel_ratio={blank_result.dark_pixel_ratio}."
            else:
                ocr_payload = _ocr_field_image(crop_image, field_id)
                raw_text = ocr_payload["raw_text"]
                confidence = ocr_payload["confidence"]
                normalized_text, normalization = _normalize_field(field_id, raw_text)
                status, validation_note = _status_for_field(field_id, normalized_text, confidence)
                notes = validation_note
        except Exception as exc:
            raw_text = ""
            confidence = ""
            normalized_text = ""
            normalization = ""
            status = "ocr_failed"
            notes = repr(exc)

        rows.append(
            {
                "field_id": field_id,
                "status": status,
                "raw_text": raw_text,
                "normalized_text": normalized_text,
                "normalization": normalization,
                "confidence": confidence if confidence is not None else "",
                "crop_path": str(crop_path),
                "notes": notes,
            }
        )

    json_payload = {
        "source_warped_page": str(warped_page_path),
        "page_number": 1,
        "output_root": str(output_root),
        "fields": rows,
    }

    json_path = output_root / "page1_ocr.json"
    csv_path = output_root / "page1_ocr.csv"

    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "field_id",
                "status",
                "raw_text",
                "normalized_text",
                "normalization",
                "confidence",
                "crop_path",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    ocr_accepted = sum(1 for row in rows if row["status"] == "accepted")
    blank_accepted = sum(1 for row in rows if row["status"] == "blank_accepted")
    review = sum(
        1
        for row in rows
        if row["status"] not in {"accepted", "blank_accepted"}
    )
    failed = sum(1 for row in rows if row["status"].endswith("failed"))

    return {
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "crop_root": str(crops_root),
        "field_count": len(rows),
        "ocr_accepted": ocr_accepted,
        "blank_accepted": blank_accepted,
        "review_needed": review,
        "failed": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Debug Page 1 OCR from an already-warped LSCO TDCJ application page."
    )
    parser.add_argument(
        "warped_page",
        type=Path,
        help="Path to warped Page 1 PNG, usually data/processed/check.../warped/warped_page_1.png",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Output folder. Default: {DEFAULT_OUTPUT_ROOT}",
    )

    args = parser.parse_args()

    summary = run_page1_ocr(
        warped_page_path=args.warped_page,
        output_root=args.output_root,
    )

    print("Page 1 OCR debug complete")
    print(f"Fields processed: {summary['field_count']}")
    print(f"OCR accepted: {summary['ocr_accepted']}")
    print(f"Blank accepted: {summary['blank_accepted']}")
    print(f"Review needed: {summary['review_needed']}")
    print(f"Failed: {summary['failed']}")
    print(f"CSV: {summary['csv_path']}")
    print(f"JSON: {summary['json_path']}")
    print(f"Crops: {summary['crop_root']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())