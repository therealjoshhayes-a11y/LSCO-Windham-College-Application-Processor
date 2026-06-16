from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lsco_tdcj_intake.form_maps.loader import load_form_map  # noqa: E402
from lsco_tdcj_intake.imaging.field_cropper import (  # noqa: E402
    crop_field_from_file,
    save_crop_result,
)
from lsco_tdcj_intake.packets.page_identity import require_page  # noqa: E402
from lsco_tdcj_intake.paths import get_page1_map_path  # noqa: E402


PAGE1_TEXT_FIELD_TYPES = {
    "boxed_text_series",
    "free_text_region",
    "line_text",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop all Page 1 text fields from a warped LSCO TDCJ page image."
    )

    parser.add_argument("warped_page_1", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/working/ocr_debug/page1_text_crops"),
    )
    parser.add_argument(
        "--manifest-json",
        type=Path,
        default=Path("data/working/ocr_debug/page1_text_crops_manifest.json"),
    )
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=Path("data/working/ocr_debug/page1_text_crops_manifest.csv"),
    )

    return parser.parse_args()


def field_type(field: object) -> str:
    if isinstance(field, dict):
        return str(field.get("type", ""))

    return str(getattr(field, "type", ""))


def iter_page1_text_field_ids(form_map) -> list[str]:
    field_ids: list[str] = []

    for field_id, field in form_map.fields.items():
        if field_type(field) in PAGE1_TEXT_FIELD_TYPES:
            field_ids.append(field_id)

    return field_ids


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "page_number",
        "field_id",
        "field_type",
        "base_box",
        "final_box",
        "padding",
        "image_shape",
        "output_image",
        "status",
        "error",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_csv.parent.mkdir(parents=True, exist_ok=True)

    identity = require_page(args.warped_page_1, 1)
    form_map = load_form_map(get_page1_map_path())
    field_ids = iter_page1_text_field_ids(form_map)

    rows: list[dict] = []

    for field_id in field_ids:
        output_image = args.output_dir / f"{field_id}.png"
        field = form_map.fields[field_id]

        try:
            crop = crop_field_from_file(
                warped_image_path=args.warped_page_1,
                form_map=form_map,
                field_id=field_id,
            )

            save_crop_result(crop, output_image)

            rows.append(
                {
                    "page_number": crop.page_number,
                    "field_id": crop.field_id,
                    "field_type": field_type(field),
                    "base_box": crop.base_box,
                    "final_box": crop.final_box,
                    "padding": asdict(crop.padding),
                    "image_shape": crop.image_shape,
                    "output_image": str(output_image),
                    "status": "ok",
                    "error": "",
                }
            )

        except Exception as exc:
            rows.append(
                {
                    "page_number": 1,
                    "field_id": field_id,
                    "field_type": field_type(field),
                    "base_box": "",
                    "final_box": "",
                    "padding": "",
                    "image_shape": "",
                    "output_image": str(output_image),
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    manifest = {
        "warped_page_1": str(args.warped_page_1),
        "page_identity": asdict(identity),
        "field_count": len(rows),
        "ok_count": sum(1 for row in rows if row["status"] == "ok"),
        "failed_count": sum(1 for row in rows if row["status"] == "failed"),
        "output_dir": str(args.output_dir),
        "rows": rows,
    }

    args.manifest_json.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    write_csv(args.manifest_csv, rows)

    print(f"Page identity OK: expected=1 predicted={identity.predicted_page}")
    print(f"Text fields found: {manifest['field_count']}")
    print(f"Crops OK: {manifest['ok_count']}")
    print(f"Crops failed: {manifest['failed_count']}")
    print(f"Crop dir: {args.output_dir}")
    print(f"Manifest JSON: {args.manifest_json}")
    print(f"Manifest CSV: {args.manifest_csv}")

    return 0 if manifest["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
