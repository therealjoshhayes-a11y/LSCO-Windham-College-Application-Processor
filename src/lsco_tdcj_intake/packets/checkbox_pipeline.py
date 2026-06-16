"""Reusable packet-level checkbox OMR pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
from PIL import Image

from lsco_tdcj_intake.imaging.fiducials import detect_ordered_fiducials
from lsco_tdcj_intake.imaging.alignment import (
    infer_output_size_from_scan,
    warp_page_from_fiducials,
)
from lsco_tdcj_intake.omr.checkbox import (
    CheckboxOMRConfig,
    detect_checkbox_mark,
    save_checkbox_debug_image,
)
from lsco_tdcj_intake.omr.checkbox_groups import (
    CHECKBOX_GROUPS,
    interpret_checkbox_group,
)
from lsco_tdcj_intake.packets.page_identity import require_page
from lsco_tdcj_intake.paths import get_page1_map_path, get_page2_map_path


@dataclass(frozen=True)
class PacketCheckboxPipelineConfig:
    dark_threshold: int = 140
    interior_shrink: float = 0.25
    unchecked_max_dark_ratio: float = 0.04
    checked_min_dark_ratio: float = 0.18


def extract_tiff_frames(tiff_path: Path, frames_dir: Path) -> tuple[Path, Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(tiff_path) as image:
        frame_count = getattr(image, "n_frames", 1)

        if frame_count < 2:
            raise ValueError(f"Expected at least 2 TIFF frames, got {frame_count}: {tiff_path}")

        output_paths: list[Path] = []

        for index in range(2):
            image.seek(index)
            frame = image.copy().convert("RGB")
            output_path = frames_dir / f"{tiff_path.stem}_frame_{index + 1:02d}.png"
            frame.save(output_path)
            output_paths.append(output_path)

    return output_paths[0], output_paths[1]


def warp_page_image(input_path: Path, output_path: Path) -> Path:
    image_bgr = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {input_path}")

    image_gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    ordered_fiducials = detect_ordered_fiducials(image_gray)
    output_width, output_height = infer_output_size_from_scan(image_bgr)

    warped = warp_page_from_fiducials(
        image=image_bgr,
        ordered_fiducials=ordered_fiducials,
        output_width_px=output_width,
        output_height_px=output_height,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(output_path), warped)

    if not ok:
        raise OSError(f"Could not write warped page: {output_path}")

    return output_path


def _load_page_map(page_number: int) -> dict:
    map_path = get_page1_map_path() if page_number == 1 else get_page2_map_path()

    with map_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _page_groups(page_number: int):
    return [
        group
        for (group_page, _group_id), group in sorted(CHECKBOX_GROUPS.items())
        if group_page == page_number
    ]


def run_page_checkbox_groups(
    image_path: Path,
    page_number: int,
    output_json: Path,
    debug_dir: Path,
    config: PacketCheckboxPipelineConfig | None = None,
) -> dict:
    cfg = config or PacketCheckboxPipelineConfig()

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    identity = require_page(image_path, page_number)
    page_map = _load_page_map(page_number)

    omr_config = CheckboxOMRConfig(
        dark_threshold=cfg.dark_threshold,
        interior_shrink=cfg.interior_shrink,
        unchecked_max_dark_ratio=cfg.unchecked_max_dark_ratio,
        checked_min_dark_ratio=cfg.checked_min_dark_ratio,
    )

    groups = _page_groups(page_number)
    if not groups:
        raise KeyError(f"No checkbox groups defined for page {page_number}")

    page_debug_dir = debug_dir / f"p{page_number}"
    page_debug_dir.mkdir(parents=True, exist_ok=True)

    interpreted_groups: dict[str, dict] = {}

    for group in groups:
        group_results = {}
        group_debug_dir = page_debug_dir / group.group_id
        group_debug_dir.mkdir(parents=True, exist_ok=True)

        for option in group.options:
            result = detect_checkbox_mark(
                page_image=image,
                page_map=page_map,
                field_id=option.field_id,
                config=omr_config,
            )

            group_results[option.field_id] = result

            debug_path = group_debug_dir / f"{option.field_id}.png"
            save_checkbox_debug_image(debug_path, image, result)

        interpreted = interpret_checkbox_group(group, group_results)
        interpreted["debug_dir"] = str(group_debug_dir)
        interpreted_groups[group.group_id] = interpreted

    invalid_groups = [
        group_id
        for group_id, group_result in interpreted_groups.items()
        if group_result["status"] != "valid"
    ]

    page_result = {
        "page_number": page_number,
        "image_path": str(image_path),
        "page_identity": asdict(identity),
        "overall_status": "valid" if not invalid_groups else "needs_review",
        "invalid_or_review_groups": invalid_groups,
        "groups": interpreted_groups,
        "debug_dir": str(page_debug_dir),
        "config": asdict(cfg),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(page_result, indent=2), encoding="utf-8")

    return page_result


def summarize_page(page_result: dict) -> dict:
    accepted: dict[str, list[str]] = {}
    suggested: dict[str, list[str]] = {}
    invalid_or_review: list[str] = []

    for group_id, group_result in page_result.get("groups", {}).items():
        selected = group_result.get("selected", [])
        suggested_selected = group_result.get("suggested_selected", [])

        if selected:
            accepted[group_id] = selected

        if suggested_selected:
            suggested[group_id] = suggested_selected

        if group_result.get("status") != "valid":
            invalid_or_review.append(group_id)

    return {
        "page_number": page_result.get("page_number"),
        "overall_status": page_result.get("overall_status"),
        "accepted": accepted,
        "suggested": suggested,
        "invalid_or_review_groups": invalid_or_review,
    }


def run_packet_checkbox_pipeline(
    tiff_path: Path,
    packet_id: str | None,
    working_dir: Path,
    output_json: Path,
    config: PacketCheckboxPipelineConfig | None = None,
) -> dict:
    packet_id = packet_id or tiff_path.stem
    packet_dir = working_dir / packet_id
    frames_dir = packet_dir / "frames"
    warped_dir = packet_dir / "warped"
    debug_dir = packet_dir / "checkbox_debug"
    page_json_dir = packet_dir / "page_json"

    page1_frame, page2_frame = extract_tiff_frames(tiff_path, frames_dir)

    warped_page1 = warp_page_image(page1_frame, warped_dir / "warped_page_1.png")
    warped_page2 = warp_page_image(page2_frame, warped_dir / "warped_page_2.png")

    page1_result = run_page_checkbox_groups(
        image_path=warped_page1,
        page_number=1,
        output_json=page_json_dir / "page_1_checkbox_groups.json",
        debug_dir=debug_dir,
        config=config,
    )

    page2_result = run_page_checkbox_groups(
        image_path=warped_page2,
        page_number=2,
        output_json=page_json_dir / "page_2_checkbox_groups.json",
        debug_dir=debug_dir,
        config=config,
    )

    page_summaries = {
        "page_1": summarize_page(page1_result),
        "page_2": summarize_page(page2_result),
    }

    review_pages = [
        page_key
        for page_key, summary in page_summaries.items()
        if summary["overall_status"] != "valid"
    ]

    packet_result = {
        "packet_id": packet_id,
        "source_tiff": str(tiff_path),
        "packet_status": "valid" if not review_pages else "needs_review",
        "review_pages": review_pages,
        "page_summaries": page_summaries,
        "pages": {
            "page_1": page1_result,
            "page_2": page2_result,
        },
        "artifacts": {
            "packet_dir": str(packet_dir),
            "frames_dir": str(frames_dir),
            "warped_page_1": str(warped_page1),
            "warped_page_2": str(warped_page2),
            "page_json_dir": str(page_json_dir),
            "debug_dir": str(debug_dir),
        },
        "config": asdict(config or PacketCheckboxPipelineConfig()),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(packet_result, indent=2), encoding="utf-8")

    return packet_result